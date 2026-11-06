"""Same corpus, separate model spaces; no activation/destructive collection operations."""

import asyncio
import hashlib
import resource
from pathlib import Path
from time import perf_counter
from uuid import UUID

import numpy as np
from qdrant_client import models as qm

from app.core.config import Settings
from app.db.models import EmbeddingModel, SearchIndex
from app.db.models.indexing import ActiveSearchIndex
from app.evaluation.dataset import query_digest, validate_labels
from app.evaluation.metrics import retrieval_metrics
from app.evaluation.quality import aggregate
from app.evaluation.statistics import describe
from app.evaluation.tracking import digest
from app.schemas.ingestion import JobInput
from app.services.embeddings.query_encoder import ClipQueryEncoder
from app.services.embeddings.siglip_encoder import SiglipEncoder
from app.services.health import Services
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.submission import submit_job
from app.services.indexing.worker import Worker
from app.services.search.fusion import fuse
from app.services.search.query_decoder import QueryDecoder
from app.services.search.vector_retriever import Candidate


async def compare_model(name, cache, snapshot, cases, labels=None):
    if labels is not None:
        validate_labels(labels, snapshot, cases)
    cfg = Settings()
    services = Services(cfg)
    decoder = QueryDecoder(cfg)
    try:
        async with services.database.sessions() as session:
            pointer = await session.get(ActiveSearchIndex, "default")
            baseline_id = pointer.index_id
            generation = pointer.generation
            if str(baseline_id) != snapshot["active"]["index_id"]:
                raise ValueError("ACTIVE_BASELINE_DRIFT")
        started = perf_counter()
        encoder = (
            await asyncio.to_thread(ClipQueryEncoder, cfg)
            if name == "clip"
            else await asyncio.to_thread(SiglipEncoder, cache, cfg.embedding_cpu_threads)
        )
        cold_ms = (perf_counter() - started) * 1000
        indexing = None
        if name == "clip":
            async with services.database.sessions() as session:
                index = await session.get(SearchIndex, baseline_id)
                model = await session.get(EmbeddingModel, index.model_id)
            if encoder.manifest_sha256 != model.manifest_sha256:
                raise ValueError("CLIP_INDEX_SPACE_MISMATCH")
        else:
            index, model = await CollectionManager(services).register(encoder, "siglip2_phase07_v1")
            job = await submit_job(
                services,
                JobInput(
                    kind="reindex",
                    target_index_id=index.id,
                    image_ids=[UUID(row["image_id"]) for row in snapshot["images"]],
                ),
                "phase07-" + digest([snapshot["sha256"], encoder.manifest_sha256]),
            )
            worker = Worker(services, encoder, index.id)
            at = perf_counter()
            await worker.run(once=True)
            indexing = {
                "job_id": str(job["job_id"]),
                "indexing_ms": (perf_counter() - at) * 1000,
                "batches": worker.batch_metrics,
            }
        verified = await verify_index(services, index.id, mark_ready=name != "clip")
        if verified["status"] != "pass" or set(verified["image_ids"]) != {
            r["image_id"] for r in snapshot["images"]
        }:
            raise ValueError("RESEARCH_INDEX_INCOMPLETE")
        info = await services.qdrant.client.get_collection(index.collection_name)
        if info.config.params.vectors.size != encoder.dimension:
            raise ValueError("COLLECTION_DIMENSION_MISMATCH")
        images = {r["image_id"]: r for r in snapshot["images"]}
        rows = []
        for case in cases:
            at = perf_counter()
            vectors = {}
            if case.request.get("text"):
                vectors["whole"] = (
                    await asyncio.to_thread(encoder.encode_text, [case.request["text"]])
                )[0]
            if case.request.get("image_id"):
                source = images[case.request["image_id"]]
                raw = await asyncio.to_thread(Path(source["cache_file"]).read_bytes)
                if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                    raise ValueError("REFERENCE_DIGEST_DRIFT")
                image = await asyncio.to_thread(decoder.decode, raw)
                try:
                    vectors["image"] = (await asyncio.to_thread(encoder.encode_images, [image]))[0]
                finally:
                    image.close()
            encoding_ms = (perf_counter() - at) * 1000
            at = perf_counter()
            branches = {}
            overlaps = {}
            for branch, vector in vectors.items():
                if vector.shape != (model.dimension,) or not np.isfinite(vector).all():
                    raise ValueError("MODEL_VECTOR_INVALID")
                result = await services.qdrant.client.query_points(
                    index.collection_name,
                    query=vector.tolist(),
                    limit=10,
                    with_payload=True,
                    search_params=qm.SearchParams(exact=False),
                )
                exact = await services.qdrant.client.query_points(
                    index.collection_name,
                    query=vector.tolist(),
                    limit=10,
                    with_payload=False,
                    search_params=qm.SearchParams(exact=True),
                )
                ids = [str(p.id) for p in result.points]
                exact_ids = [str(p.id) for p in exact.points]
                overlaps[branch] = {
                    f"ann_vs_exact_overlap@{k}": len(set(ids[:k]) & set(exact_ids[:k]))
                    / min(k, len(exact_ids))
                    for k in [1, 5, 10]
                }
                branches[branch] = [
                    Candidate(UUID(str(p.id)), float(p.score), p.payload or {})
                    for p in result.points
                ]
            candidates = fuse(branches, {branch: 1 for branch in branches}, "rrf", 60, 10)
            ids = [str(c.image_id) for c in candidates]
            quality = (
                retrieval_metrics(
                    ids,
                    {
                        identity: 2 if identity == case.request["image_id"] else 0
                        for identity in images
                    },
                    relevant_grade=2,
                    strict_labels=True,
                )
                if case.task == "exact_identity"
                else None
            )
            semantic_metrics = (
                retrieval_metrics(
                    ids,
                    labels["queries"][case.query_id]["grades"],
                    relevant_grade=labels.get("binary_relevance_min_grade", 2),
                    strict_labels=True,
                )
                if labels is not None and case.task != "exact_identity"
                else None
            )
            rows.append(
                {
                    "query_id": case.query_id,
                    "query_type": case.query_type,
                    "language": case.language,
                    "task": case.task,
                    "group_id": case.group_id,
                    "split": case.split,
                    "search_mode": "paired_rrf" if len(branches) > 1 else next(iter(branches)),
                    "status": "measured",
                    "encoding_ms": encoding_ms,
                    "vector_retrieval_and_exact_comparison_ms": (perf_counter() - at) * 1000,
                    "result_ids": ids,
                    "identity_metrics": quality,
                    "metrics": semantic_metrics or quality or {},
                    "ann_vs_exact": overlaps,
                }
            )
        async with services.database.sessions() as session:
            current = await session.get(ActiveSearchIndex, "default")
            if current.index_id != baseline_id or current.generation != generation:
                raise ValueError("ACTIVE_POINTER_CHANGED")
        return {
            "status": "measured",
            "model": name,
            "model_id": str(model.id),
            "checkpoint": model.model_name,
            "revision": model.model_revision,
            "manifest_sha256": model.manifest_sha256,
            "manifest": model.manifest,
            "index_id": str(index.id),
            "collection": index.collection_name,
            "dimension": model.dimension,
            "model_initialization_fresh_process_ms": cold_ms,
            "cold_policy": (
                "fresh model/process; filesystem cache warm/uncontrolled; "
                "includes hash verification and warmup"
            ),
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "device": "cpu",
            "gpu_results": None,
            "index_verification": verified,
            "indexing": indexing,
            "hnsw_config": info.config.hnsw_config.model_dump(mode="json"),
            "indexed_vectors_count": info.indexed_vectors_count,
            "ann_caveat": (
                "Small corpus may use plain scan; overlap@10 is trivial when K=N; "
                "not human relevance Recall"
            ),
            "encoding_latency": describe([r["encoding_ms"] for r in rows]),
            "dataset_sha256": snapshot["sha256"],
            "query_set_sha256": query_digest(cases),
            "label_sha256": digest(labels) if labels else None,
            "semantic_quality": "measured" if labels else "not_measured_no_human_labels",
            "aggregates": aggregate([r for r in rows if r["metrics"]]),
            "active_baseline_preserved": True,
            "queries": rows,
        }
    finally:
        await asyncio.to_thread(decoder.stop)
        await services.close()
