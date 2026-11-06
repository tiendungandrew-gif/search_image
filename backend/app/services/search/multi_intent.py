"""Candidate generation có giới hạn; share encoder/metadata/result path với Prompt05."""

import asyncio
from time import perf_counter

import numpy as np

from app.core.exceptions import AppError
from app.schemas.constraints import leaves
from app.schemas.search import FusionOptions
from app.services.embeddings.clip_encoder import normalized_vectors
from app.services.indexing.worker import vector_hash
from app.services.query.query_decomposer import retrieval_clauses
from app.services.search.evidence import UNKNOWN, VIOLATED, assessments, evaluate_required
from app.services.search.fusion import fuse
from app.services.search.ranking import rank_unique
from app.services.search.reranker import LightweightReranker


class AdvancedRetriever:
    def __init__(self, search):
        self.search = search
        self.runtime = search.runtime
        self.cfg = search.settings

    async def stored_scores(self, candidates, rows, vectors):
        points = await self.search.services.qdrant.client.retrieve(
            self.search.registry.index.collection_name,
            ids=[str(c.image_id) for c in candidates],
            with_payload=False,
            with_vectors=True,
        )
        output = {}
        for point in points:
            identity = next(
                (c.image_id for c in candidates if str(c.image_id) == str(point.id)), None
            )
            if identity not in rows:
                continue
            if vector_hash(point.vector) != rows[identity][2].vector_sha256:
                raise AppError(
                    409, "MODEL_INDEX_MISMATCH", "Candidate vector digest không khớp registry"
                )
            vector = normalized_vectors([point.vector], self.search.registry.model.dimension)[0]
            output[identity] = {
                name: float(np.dot(query, vector)) for name, query in vectors.items()
            }
        return output

    async def retrieve(self, options, query_bytes, analysis, count, stages, warnings):
        tree = analysis.constraints
        cfg = self.cfg
        signals = {}
        branch_vectors = {}
        exclude_id = None
        has_image = query_bytes is not None or options.image_id is not None
        fusion = options.fusion or FusionOptions(
            method=cfg.multimodal_fusion_strategy,
            text_weight=cfg.multimodal_text_weight,
            image_weight=cfg.multimodal_image_weight,
            rrf_k=cfg.fusion_rrf_k,
        )
        items = ([("whole", options.text)] if options.text else []) + [
            (leaf.id, leaf.text) for leaf in leaves(tree) if leaf.kind == "semantic"
        ]
        if items:
            unique = list(dict.fromkeys(text for _, text in items))
            mark = perf_counter()

            def encode():
                values = self.runtime.encoder.encode_text(unique)
                return values, dict(self.runtime.encoder.last_metrics)

            values, metrics = await self.runtime.compute(encode)
            stages.update(metrics)
            stages["text_embedding_ms"] = (perf_counter() - mark) * 1000
            lookup = dict(zip(unique, values, strict=True))
            signals = {name: lookup[text] for name, text in items}
            if options.text:
                branch_vectors["whole"] = signals["whole"]
        if has_image:
            image_options = options.model_copy(update={"text": None})
            vector, exclude_id = await self.search.encode(image_options, query_bytes, stages)
            signals["image"] = vector
            branch_vectors["image"] = vector
            if not options.text:
                signals["whole"] = vector
        available = cfg.search_max_branches - len(branch_vectors)
        if options.retrieval_strategy != "whole_query" and cfg.query_decomposition_enabled:
            for leaf in retrieval_clauses(tree, available):
                if leaf.text != options.text:
                    branch_vectors[leaf.id] = signals[leaf.id]
        text_branches = [name for name in branch_vectors if name != "image"]
        weights = {
            name: (
                fusion.image_weight if name == "image" else fusion.text_weight / len(text_branches)
            )
            if has_image and options.text
            else 1.0
            for name in branch_vectors
        }
        per_branch = min(count, 1000 // len(branch_vectors))
        mark = perf_counter()
        names = list(branch_vectors)
        batches = await asyncio.gather(
            *(
                self.search.retriever.search(
                    branch_vectors[name], per_branch, options.filters, exclude_id
                )
                for name in names
            )
        )
        stages["vector_retrieval_ms"] = (perf_counter() - mark) * 1000
        branches = dict(zip(names, batches, strict=True))
        mark = perf_counter()
        pool_limit = min(cfg.search_advanced_candidate_limit, 1000)
        candidates = fuse(branches, weights, fusion.method, fusion.rrf_k, pool_limit)
        stages["candidate_fusion_ms"] = (perf_counter() - mark) * 1000
        mark = perf_counter()
        rows, tags = await self.search.repository.candidates(
            [c.image_id for c in candidates], self.search.registry.index.id
        )
        stages["metadata_ms"] = (perf_counter() - mark) * 1000
        mark = perf_counter()
        eligible = []
        unknown = False
        for candidate in candidates:
            if candidate.image_id not in rows:
                continue
            scores = {c["branch"]: c["cosine"] for c in candidate.contributions}
            candidate.assessments = assessments(
                tree, rows[candidate.image_id], tags[candidate.image_id], scores
            )
            state = evaluate_required(
                tree, {a["clause_id"]: a["status"] for a in candidate.assessments}
            )
            if state == VIOLATED or options.require_verified and state == UNKNOWN:
                continue
            unknown |= any(a["status"] == UNKNOWN for a in candidate.assessments)
            eligible.append(candidate)
        stages["metadata_filtering_ms"] = (perf_counter() - mark) * 1000
        if unknown:
            warnings.append(
                {
                    "code": "CONSTRAINTS_NOT_VERIFIED",
                    "message": "Điều kiện chưa xác minh; similarity chỉ dùng để xếp hạng",
                }
            )
        score_type = "weighted_score" if fusion.method == "weighted_score" else "rrf"
        ranking_version = (
            "weighted-score-v1" if score_type == "weighted_score" else "weighted-rrf-v1"
        )
        reranked = False
        vector_fetch_calls = 0
        if options.retrieval_strategy in {"whole_query", "multi_query"}:
            matrix = (
                await self.stored_scores(eligible, rows, {"whole": signals["whole"]})
                if eligible
                else {}
            )
            vector_fetch_calls += bool(eligible)
            eligible = [c for c in eligible if c.image_id in matrix]
            for candidate in eligible:
                candidate.score = matrix[candidate.image_id]["whole"]
            eligible = rank_unique(eligible)
            score_type, ranking_version = "cosine", "whole-query-rescore-v1"
        if options.rerank.enabled and cfg.reranking_enabled and eligible:
            limit = options.rerank.candidate_limit or cfg.reranking_max_candidates
            if limit > cfg.reranking_max_candidates:
                raise AppError(422, "INVALID_INPUT", "Rerank candidate limit vượt cấu hình server")
            if limit < options.top_k:
                raise AppError(422, "INVALID_INPUT", "Rerank candidate limit phải ít nhất Top-K")
            mark = perf_counter()
            try:
                async with asyncio.timeout(
                    (options.rerank.timeout_ms or cfg.reranking_timeout_ms) / 1000
                ):
                    selected = eligible[:limit]
                    matrix = await self.stored_scores(selected, rows, signals)
                    vector_fetch_calls += 1
                    selected = [c for c in selected if c.image_id in matrix]
                    for candidate in selected:
                        values = matrix[candidate.image_id]
                        candidate.assessments = assessments(
                            tree, rows[candidate.image_id], tags[candidate.image_id], values
                        )
                        if has_image and options.text:
                            values["whole"] = (
                                fusion.text_weight * values["whole"]
                                + fusion.image_weight * values["image"]
                            ) / (fusion.text_weight + fusion.image_weight)
                    # Chỉ publish sau success; lỗi/timeout không để mutation làm hỏng baseline.
                    import copy

                    reranked_values = LightweightReranker(cfg).rank(
                        copy.deepcopy(selected), matrix, tree
                    )
                    await asyncio.sleep(0)
                eligible = reranked_values
                reranked = True
                score_type, ranking_version = "reranker", "constraint-linear-v1"
            except AppError:
                raise
            except Exception:
                if options.rerank.on_failure != "skip":
                    raise AppError(
                        503, "RERANK_FAILED", "Reranker lỗi hoặc quá thời gian", retryable=True
                    ) from None
                warnings.append(
                    {
                        "code": "RERANK_SKIPPED",
                        "message": "Reranker lỗi hoặc quá thời gian; giữ baseline ranking",
                    }
                )
            stages["reranking_ms"] = (perf_counter() - mark) * 1000
        return (
            eligible,
            rows,
            tags,
            {
                "candidate_count": per_branch,
                "candidate_pool_limit": pool_limit,
                "channels": len(branches),
                "vector_calls": len(branches),
                "vector_fetch_calls": vector_fetch_calls,
                "score_type": score_type,
                "ranking_version": ranking_version,
                "fusion_version": fusion.method + "-v1",
                "fusion_weights": weights,
                "rrf_k": fusion.rrf_k,
                "constraints_mode": "strict" if options.require_verified else "best_effort",
                "truncated": any(len(batch) == per_branch for batch in batches)
                or len({c.image_id for batch in batches for c in batch}) > pool_limit,
                "route": "paired_fusion" if has_image and options.text else "multi_query",
                "rerank_applied": reranked,
                "retrieval_strategy": options.retrieval_strategy,
            },
        )
