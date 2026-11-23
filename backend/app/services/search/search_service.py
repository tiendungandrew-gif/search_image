import asyncio
import hashlib
from time import perf_counter
from uuid import UUID, uuid4

from minio.error import S3Error
from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.models import Image
from app.repositories.image_repository import ImageRepository
from app.schemas.constraints import leaves
from app.schemas.search import ResultMetadata, SearchResponse, SearchResult
from app.services.embeddings.clip_encoder import normalized_vectors
from app.services.embeddings.vector_utils import vector_hash
from app.services.query.language import search_subject
from app.services.query.query_classifier import analyze_query
from app.services.search.ranking import matches_metadata, rank_unique
from app.services.search.text_matching import hybrid_rank, requires_food_phrase
from app.services.search.vector_retriever import Candidate, VectorRetriever


class SearchService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.services = runtime.services
        self.settings = runtime.settings
        self.registry = runtime.registry
        self.repository = ImageRepository(self.services)
        self.retriever = VectorRetriever(self.services, self.registry)

    async def encode(self, options, query_bytes, stages):
        exclude_id = None
        if options.text is not None:
            mark = perf_counter()

            def encode_text():
                value = self.runtime.encoder.encode_text([options.text])[0]
                return value, dict(self.runtime.encoder.last_metrics)

            vector, text_metrics = await self.runtime.compute(encode_text)
            stages.update(text_metrics)
            stages["text_embedding_ms"] = (perf_counter() - mark) * 1000
        elif query_bytes is not None:
            timings = {}

            def encode_image():
                mark = perf_counter()
                image = self.runtime.decoder.decode(query_bytes)
                timings["image_preprocessing_ms"] = (perf_counter() - mark) * 1000
                try:
                    mark = perf_counter()
                    result = self.runtime.encoder.encode_images([image])[0]
                    timings["image_embedding_ms"] = (perf_counter() - mark) * 1000
                    return result
                finally:
                    image.close()

            vector = await self.runtime.compute(encode_image)
            stages.update(timings)
            if options.exclude_self:
                async with self.services.database.sessions() as session:
                    exclude_id = await session.scalar(
                        select(Image.id).where(
                            Image.sha256 == hashlib.sha256(query_bytes).hexdigest()
                        )
                    )
        else:
            mark = perf_counter()
            rows, _ = await self.repository.candidates([options.image_id], self.registry.index.id)
            if options.image_id not in rows:
                raise AppError(404, "IMAGE_NOT_FOUND", "Ảnh tham chiếu chưa indexed/available")
            points = await self.services.qdrant.client.retrieve(
                self.registry.index.collection_name,
                ids=[str(options.image_id)],
                with_payload=True,
                with_vectors=True,
            )
            if (
                not points
                or vector_hash(points[0].vector) != rows[options.image_id][2].vector_sha256
            ):
                raise AppError(409, "MODEL_INDEX_MISMATCH", "Stored reference vector không hợp lệ")
            vector = normalized_vectors([points[0].vector], self.registry.model.dimension)[0]
            exclude_id = options.image_id if options.exclude_self else None
            stages["reference_vector_ms"] = (perf_counter() - mark) * 1000
        return vector, exclude_id

    async def object_available(self, image, receipt):
        try:
            stat = await self.services.minio.run(
                lambda: self.services.minio.client.stat_object(receipt.bucket, receipt.object_key)
            )
            return stat.size == image.byte_size
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise AppError(
                503, "DEPENDENCY_UNAVAILABLE", "Object service không khả dụng", retryable=True
            ) from None
        except Exception:
            raise AppError(
                503, "DEPENDENCY_UNAVAILABLE", "Object service không khả dụng", retryable=True
            ) from None

    async def metadata_candidates(self, hits):
        if not hits:
            return []
        try:
            points = await self.services.qdrant.client.retrieve(
                self.registry.index.collection_name,
                ids=[str(hit.image_id) for hit in hits],
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            raise AppError(
                503, "DEPENDENCY_UNAVAILABLE", "Không lấy được ứng viên tìm kiếm", retryable=True
            ) from None
        payloads = {str(point.id): point.payload or {} for point in points}
        return [
            Candidate(hit.image_id, hit.score, payloads[str(hit.image_id)])
            for hit in hits if str(hit.image_id) in payloads
        ]

    async def format_results(
        self,
        ranked,
        options,
        stages,
        rows=None,
        tags=None,
        score_type="cosine",
        ranking_version="cosine-v1",
    ):
        if rows is None:
            mark = perf_counter()
            rows, tags = await self.repository.candidates(
                [c.image_id for c in ranked], self.registry.index.id
            )
            stages["metadata_ms"] = (perf_counter() - mark) * 1000
        results = []
        missing = 0
        mark = perf_counter()
        eligible = []
        for candidate in ranked:
            row = rows.get(candidate.image_id)
            if row is None:
                continue
            image, metadata, embedding, receipt = row
            payload = candidate.payload
            expected = {
                "image_id": str(image.id),
                "index_id": str(self.registry.index.id),
                "manifest_sha256": self.registry.model.manifest_sha256,
                "source_sha256": image.sha256,
                "metadata_revision": image.metadata_revision,
            }
            if any(payload.get(k) != v for k, v in expected.items()):
                continue
            if not matches_metadata(options.filters, image, metadata, tags[image.id]):
                continue
            eligible.append((candidate, row))
        rank_offset = 0
        if options.page is not None:
            page_size = stages.pop("pagination_page_size")
            total = len(eligible)
            total_pages = (total + page_size - 1) // page_size
            page = min(options.page, max(1, total_pages))
            rank_offset = (page - 1) * page_size
            stages["pagination"] = {
                "page": page, "page_size": page_size, "total_results": total,
                "total_pages": total_pages, "result_limit": 500,
            }
            # Check objects only for this page; never scan hundreds of originals per click.
            eligible = eligible[rank_offset:rank_offset + page_size]
        cursor = 0
        io_ms = 0.0
        while cursor < len(eligible) and len(results) < options.top_k:
            width = min(self.settings.search_object_check_concurrency, options.top_k - len(results))
            window = eligible[cursor : cursor + width]
            cursor += len(window)
            io_started = perf_counter()
            available = await asyncio.gather(
                *(self.object_available(row[0], row[3]) for _, row in window)
            )
            io_ms += (perf_counter() - io_started) * 1000
            for (candidate, row), exists in zip(window, available, strict=True):
                if not exists:
                    missing += 1
                    continue
                image, metadata, embedding, receipt = row
                url = f"/api/v1/images/{image.id}/content"
                results.append(
                    SearchResult(
                        image_id=image.id,
                        rank=rank_offset + len(results) + 1,
                        score=candidate.score,
                        score_type=score_type,
                        ranking_version=ranking_version,
                        constraint_assessments=getattr(candidate, "assessments", []),
                        constraint_evidence=[
                            {
                                **a,
                                "status": {
                                    "satisfied": "VERIFIED_MATCH",
                                    "violated": "VERIFIED_MISMATCH",
                                    "unknown": "UNKNOWN",
                                }[a["status"]],
                            }
                            for a in getattr(candidate, "assessments", [])
                        ],
                        score_components=getattr(candidate, "score_components", {}),
                        contributing_branches=getattr(candidate, "contributions", []),
                        image_url=url + "?variant=original",
                        thumbnail_url=url + "?variant=thumbnail",
                        metadata=ResultMetadata(
                            title=metadata.title if metadata else None,
                            caption=metadata.caption if metadata else None,
                            width=image.width,
                            height=image.height,
                            media_type=image.media_type,
                            tags=tags[image.id],
                            source_dataset=metadata.source_dataset if metadata else None,
                            city=metadata.city if metadata else None,
                            license=metadata.license if metadata else None,
                        ),
                    )
                )
                if len(results) == options.top_k:
                    break
        stages["object_head_windows_ms"] = io_ms
        stages["eligibility_objects_urls_ms"] = (perf_counter() - mark) * 1000
        return results, missing

    async def execute(self, options, request_id, query_bytes=None):
        start = perf_counter()
        stages = {}
        warnings = []
        has_image = query_bytes is not None or options.image_id is not None
        if options.mode == "agent" or options.explain.enabled:
            raise AppError(409, "FEATURE_DISABLED", "Agent/RAG chưa triển khai")
        if not (options.text or has_image) or (
            query_bytes is not None and options.image_id is not None
        ):
            raise AppError(422, "INVALID_INPUT", "Cần text hoặc đúng một ảnh tham chiếu")
        paired = bool(options.text and has_image)
        if paired and options.retrieval_strategy != "fused":
            raise AppError(422, "INVALID_INPUT", "Multimodal yêu cầu fused retrieval strategy")
        if (
            options.mode == "text"
            and (not options.text or has_image)
            or options.mode == "image"
            and (options.text or not has_image)
            or options.mode == "multimodal"
            and not paired
            or options.mode == "multi_intent"
            and (not options.text or has_image)
        ):
            raise AppError(422, "INVALID_INPUT", "Mode không khớp input")
        if options.top_k > self.settings.search_max_top_k:
            raise AppError(422, "INVALID_INPUT", "Top-K vượt cấu hình server")
        if options.text and len(options.text) > self.settings.search_max_text_length:
            raise AppError(422, "INVALID_INPUT", "Truy vấn quá dài")
        if not self.settings.search_enable_basic_filters and options.filters.model_dump(
            exclude_defaults=True
        ):
            raise AppError(409, "FEATURE_DISABLED", "Metadata filters đang tắt")
        page_size = options.top_k
        if options.page is not None:
            # A fixed retrieval window keeps rankings independent of the requested page.
            options = options.model_copy(update={"top_k": 500, "candidate_count": 500})
        original_text = options.text
        if original_text and options.constraints is None and options.mode in {"auto", "text"}:
            options = options.model_copy(update={"text": search_subject(original_text)})
        text_hits = []
        name_hits = []
        phrase_hits = []
        food_phrase = False
        metadata_limit = min(
            500,
            options.candidate_count or max(options.top_k, self.settings.search_default_candidates),
        )
        if (
            options.text and not has_image and options.mode in {"auto", "text"}
            and options.constraints is None and not options.rerank.enabled
            and not options.require_verified and options.retrieval_strategy == "fused"
        ):
            mark = perf_counter()
            text_hits = await self.repository.text_candidates(
                options.text, self.registry.index.id, options.filters, metadata_limit
            )
            name_hits = [hit for hit in text_hits if hit.name_match]
            phrase_hits = [hit for hit in text_hits if hit.phrase_match]
            food_phrase = requires_food_phrase(options.text)
            stages["metadata_text_lookup_ms"] = (perf_counter() - mark) * 1000
        if (options.text and not (name_hits or phrase_hits or food_phrase)
                and hasattr(self.runtime.encoder, "normalize_texts")):
            mark = perf_counter()
            normalized = await self.runtime.compute(
                lambda: self.runtime.encoder.normalize_texts([options.text])[0]
            )
            stages["query_normalization_ms"] = (perf_counter() - mark) * 1000
            if normalized != options.text:
                options = options.model_copy(update={"text": normalized})
                warnings.append(
                    {
                        "code": "QUERY_ACCENTS_RESTORED",
                        "message": f"Đã tìm theo “{normalized}” (thêm dấu từ “{original_text}”).",
                    }
                )
        mark = perf_counter()
        parse = bool(
            options.mode in {"auto", "multi_intent", "multimodal"}
            and self.settings.query_decomposition_enabled
            and not (name_hits or phrase_hits or food_phrase)
        )
        analysis = analyze_query(
            options.text, has_image, parse=parse, explicit=options.constraints, timings=stages
        )
        analysis.original_query = original_text or ""
        if options.constraints is not None:
            analysis.constraints = options.constraints
        stages["query_analysis_ms"] = (perf_counter() - mark) * 1000 - stages.get(
            "query_decomposition_ms", 0
        )
        if analysis.requires_agent:
            raise AppError(
                409,
                "UNSUPPORTED_RELATIONAL_QUERY",
                "Truy vấn cần quan hệ/multi-hop chưa được hỗ trợ",
            )
        if analysis.uncertain:
            warnings.append(
                {
                    "code": "QUERY_ANALYSIS_UNCERTAIN",
                    "message": "Giữ nguyên query vì pattern chưa được phân rã tin cậy",
                }
            )
        tree = analysis.constraints
        if not self.settings.search_enable_basic_filters and any(
            leaf.kind == "metadata" for leaf in leaves(tree)
        ):
            raise AppError(409, "FEATURE_DISABLED", "Metadata constraints đang tắt")
        advanced = (
            paired
            or options.mode == "multi_intent"
            and not analysis.uncertain
            or analysis.query_type == "MULTI_INTENT"
            or options.constraints is not None
            or any(leaf.negated or leaf.kind == "metadata" for leaf in leaves(tree))
            or options.rerank.enabled
            or options.require_verified
        )
        if (
            advanced
            and not paired
            and not self.settings.multi_intent_enabled
            and options.mode == "auto"
            and options.constraints is None
            and not options.rerank.enabled
            and not options.require_verified
        ):
            advanced = False
            warnings.append(
                {
                    "code": "CONSTRAINTS_NOT_VERIFIED",
                    "message": "Multi-intent đang tắt; giữ nguyên query qua single-vector path",
                }
            )
        if (
            paired
            and not self.settings.multimodal_enabled
            or advanced
            and not paired
            and not self.settings.multi_intent_enabled
        ):
            raise AppError(409, "FEATURE_DISABLED", "Advanced retrieval đang tắt")
        if len(leaves(tree)) > self.settings.search_max_constraints:
            raise AppError(422, "CONSTRAINT_LIMIT", "Quá nhiều constraints theo cấu hình server")
        if options.require_verified and not tree:
            raise AppError(422, "INVALID_INPUT", "require_verified cần constraints rõ ràng")
        if options.require_verified and any(
            leaf.required and leaf.kind == "semantic" for leaf in leaves(tree)
        ):
            raise AppError(
                409,
                "VERIFIER_UNAVAILABLE",
                "Chưa có verifier cho semantic conditions; CLIP không chứng minh điều kiện",
            )
        if options.rerank.enabled and not self.settings.reranking_enabled:
            if options.rerank.on_failure != "skip":
                raise AppError(409, "FEATURE_DISABLED", "Reranker đang tắt")
            warnings.append(
                {"code": "RERANK_SKIPPED", "message": "Reranker đang tắt; giữ baseline ranking"}
            )
        mark = perf_counter()
        await self.registry.check()
        stages["compatibility_ms"] = (perf_counter() - mark) * 1000
        count = options.candidate_count or max(
            options.top_k, self.settings.search_default_candidates
        )
        mode = (
            "multimodal"
            if paired
            else "multi_intent"
            if advanced and options.text
            else "image"
            if has_image
            else "text"
        )
        if (name_hits or phrase_hits or food_phrase) and not advanced:
            mark = perf_counter()
            ranked = await self.metadata_candidates(name_hits or phrase_hits)
            stages["metadata_candidate_payload_ms"] = (perf_counter() - mark) * 1000
            rows = tags = None
            score_type = "weighted_score"
            ranking_version = "metadata-name-v1" if name_hits else "metadata-phrase-v1"
            settings = {
                "candidate_count": metadata_limit,
                "channels": 1, "vector_calls": 0, "vector_fetch_calls": 1,
                "fusion_version": None, "constraints_mode": "metadata_only",
                "truncated": len(text_hits) == metadata_limit,
                "route": "metadata_name" if name_hits else "metadata_phrase",
                "rerank_applied": False,
                "phrase_matched": bool(phrase_hits and not name_hits),
                "metadata_candidates": len(ranked),
            }
            if food_phrase:
                settings["food_phrase_required"] = True
            if food_phrase and not (name_hits or phrase_hits):
                settings["route"] = "metadata_food_phrase"
                warnings.append({
                    "code": "FOOD_PHRASE_NOT_FOUND",
                    "message": (
                        f"Chưa tìm thấy ảnh có mô tả khớp món “{options.text}”. "
                        "Hãy thử tên món cụ thể hơn hoặc một món khác."
                    ),
                })
        elif advanced:
            from app.services.search.multi_intent import AdvancedRetriever

            ranked, rows, tags, settings = await AdvancedRetriever(self).retrieve(
                options, query_bytes, analysis, count, stages, warnings
            )
            score_type = settings["score_type"]
            ranking_version = settings["ranking_version"]
        else:
            vector, exclude_id = await self.encode(options, query_bytes, stages)
            mark = perf_counter()
            candidates = await self.retriever.search(vector, count, options.filters, exclude_id)
            stages["vector_retrieval_ms"] = (perf_counter() - mark) * 1000
            mark = perf_counter()
            ranked = rank_unique(candidates)
            stages["ranking_ms"] = (perf_counter() - mark) * 1000
            rows = tags = None
            score_type = "cosine"
            ranking_version = "cosine-v1"
            settings = {
                "candidate_count": count,
                "channels": 1,
                "vector_calls": 1,
                "fusion_version": None,
                "constraints_mode": "metadata_only",
                "truncated": len(candidates) == count,
                "route": "single_vector",
                "rerank_applied": False,
            }
            if text_hits:
                metadata = await self.metadata_candidates(text_hits)
                if metadata:
                    ranked = hybrid_rank(metadata, ranked)
                    score_type, ranking_version = "rrf", "metadata-visual-rrf-v1"
                    settings.update(
                        channels=2, vector_fetch_calls=1, fusion_version="metadata-visual-rrf-v1",
                        route="metadata_visual", metadata_candidates=len(metadata),
                    )
        if options.page is not None:
            stages["pagination_page_size"] = page_size
        results, missing = await self.format_results(
            ranked[:500] if options.page is not None else ranked,
            options, stages, rows, tags, score_type, ranking_version
        )
        if missing:
            warnings.append(
                {
                    "code": "MISSING_IMAGE_OBJECT",
                    "message": "Một số originals không khả dụng đã được loại",
                }
            )
        if settings["truncated"] and len(results) < page_size:
            warnings.append(
                {
                    "code": "CANDIDATE_LIMIT",
                    "message": "Kết quả eligible bị giới hạn bởi candidate pool",
                }
            )
        pagination = stages.pop("pagination", None)
        elapsed = (perf_counter() - start) * 1000
        return SearchResponse(
            query_id=uuid4(),
            request_id=UUID(request_id),
            requested_mode=options.mode,
            search_mode=mode,
            service_class="advanced" if advanced else "fast",
            index_id=self.registry.index.id,
            model_id=self.registry.model.id,
            manifest_sha256=self.registry.model.manifest_sha256,
            results=results,
            total_results=len(results),
            pagination=pagination,
            effective_settings={
                "text_encoder_manifest_sha256": getattr(
                    self.runtime.encoder, "text_manifest_sha256", None
                )
                if options.text
                else None,
                "top_k": page_size,
                "ranking_version": ranking_version,
                "total_candidate_cap": 1000,
                "object_check_concurrency": self.settings.search_object_check_concurrency,
                **settings,
            },
            query_analysis=analysis.model_dump(mode="json"),
            latency={"processing_ms": elapsed, "server_response_ms": None, "stages": stages},
            latency_ms=elapsed,
            warnings=warnings,
        )
