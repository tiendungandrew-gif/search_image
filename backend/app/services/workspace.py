"""Read-only, bounded workspace snapshots; never infer an empty DB from a failure."""

import asyncio
import json
import math
from pathlib import Path

from sqlalchemy import func, select

from app.core.access import restricted, source_clause, visible_image_clause
from app.db.models import Image, ImageMetadata, SearchIndex
from app.db.models.indexing import ActiveSearchIndex, ImageEmbedding


def dataset_state(dependencies, images, indexed, vectors, index_status, runtime_ready):
    if any(value != "healthy" for value in dependencies.values()) or images is None:
        return "unavailable"
    if images == 0:
        return "index_not_ready" if indexed or vectors else "empty_dataset"
    if index_status in {"building", "validating"}:
        return "index_building"
    if not runtime_ready or not indexed or not vectors:
        return "index_not_ready"
    return "ready"


async def workspace_snapshot(request):
    state = request.app.state
    settings = state.settings
    services = state.services
    dependencies = await services.readiness()
    runtime = getattr(state, "search_runtime", None)
    runtime_ready = bool(runtime and runtime.available)
    images = available = indexed = vectors = None
    index_id = index_status = None
    generation = None
    try:
        async with asyncio.timeout(settings.dependency_timeout_seconds):
            async with services.database.sessions() as session:
                images = await session.scalar(
                    select(func.count())
                    .select_from(Image)
                    .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                    .where(
                        Image.status.not_in(["deleting", "deleted"]),
                        source_clause(),
                        visible_image_clause(Image.id),
                    )
                )
                available = await session.scalar(
                    select(func.count())
                    .select_from(Image)
                    .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                    .where(
                        Image.status == "available", source_clause(), visible_image_clause(Image.id)
                    )
                )
                active = await session.get(ActiveSearchIndex, "default")
                index = await session.get(SearchIndex, active.index_id) if active else None
                if index:
                    index_id, index_status = str(index.id), index.status
                    generation = active.generation
                    indexed = await session.scalar(
                        select(func.count())
                        .select_from(ImageEmbedding)
                        .join(Image, Image.id == ImageEmbedding.image_id)
                        .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                        .where(
                            ImageEmbedding.index_id == index.id,
                            ImageEmbedding.status == "ready",
                            Image.status == "available",
                            source_clause(),
                            visible_image_clause(Image.id),
                            ImageEmbedding.metadata_revision == Image.metadata_revision,
                        )
                    )
                else:
                    building = await session.scalar(
                        select(SearchIndex.id)
                        .where(SearchIndex.status.in_(["building", "validating"]))
                        .limit(1)
                    )
                    index_status = "building" if building else "absent"
                    indexed = 0
            if runtime_ready and index_id == str(runtime.registry.index.id):
                await runtime.registry.check()
                if restricted():
                    from app.schemas.filters import Filters
                    from app.services.search.vector_retriever import payload_filter

                    count = await services.qdrant.client.count(
                        runtime.registry.index.collection_name,
                        count_filter=payload_filter(Filters()),
                        exact=True,
                    )
                    vectors = count.count
                else:
                    collection = await services.qdrant.client.get_collection(
                        runtime.registry.index.collection_name
                    )
                    vectors = collection.points_count
            else:
                runtime_ready = False
    except Exception:
        # Unknown is distinct from zero. No database exception details leave the service.
        dependencies = {**dependencies, "snapshot": "unhealthy"}
        runtime_ready = False
    status = dataset_state(dependencies, images, indexed, vectors, index_status, runtime_ready)
    if restricted() and images == 0:
        status = "empty_dataset"
    searchable = status == "ready"
    generator = getattr(state, "rag_generator", None)
    rag_ready = bool(settings.rag_enabled and generator and generator.provider is not None)
    return {
        "dataset": {
            "state": status,
            "images": images,
            "available_images": available,
            "indexed_images": indexed,
            "vectors": vectors,
            "index_id": index_id,
            "index_status": index_status,
            "generation": generation,
        },
        "dependencies": dependencies,
        "capabilities": {
            "text_search": searchable,
            "image_search": searchable,
            "multimodal": searchable and settings.multimodal_enabled,
            "multi_intent": searchable and settings.multi_intent_enabled,
            "rerank": searchable and settings.reranking_enabled,
            "explanations": searchable and rag_ready,
            "agent": searchable and settings.agent_enabled,
        },
        "rag": {
            "enabled": settings.rag_enabled,
            "configured": rag_ready,
            "streaming": settings.rag_streaming_enabled,
        },
        "agent": {
            "enabled": settings.agent_enabled,
            "llm_planning": settings.agent_llm_planning_enabled and rag_ready,
        },
        "limits": {
            "top_k": settings.search_max_top_k,
            "image_bytes": settings.image_max_upload_mb * 1024**2,
        },
    }


def evaluation_summaries(root: Path):
    """Allowlisted aggregate metrics only. No samples, prompts, credentials or file paths."""
    if not root.is_dir():
        return {"state": "not_available", "experiments": [], "skipped": 0}
    root = root.resolve()
    experiments = []
    skipped = 0
    # Known tracker layout: phase/run/result.json, not arbitrary recursive file access.
    paths = sorted(root.glob("*/*/result.json"), reverse=True)[:200]
    for path in paths:
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(root) or path.stat().st_size > 16 * 1024**2:
                raise ValueError("unsafe_artifact")
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                raise ValueError("invalid_artifact")
            latency = value.get("client_success_latency", {})
            if not isinstance(latency, dict):
                latency = {}

            def number(item):
                return (
                    item
                    if type(item) in (int, float) and math.isfinite(item) and item >= 0
                    else None
                )

            def count(item):
                return item if type(item) is int and item >= 0 else None

            experiments.append(
                {
                    "id": path.parent.name[:160],
                    "phase": path.parent.parent.name[:80],
                    "kind": "agent"
                    if "agent_groups" in value
                    else ("rag" if "rag_groups" in value or "groups" in value else "retrieval"),
                    "status": str(value.get("status", "unknown"))[:80],
                    "attempted": count(value.get("attempted")),
                    "successful": count(value.get("successful")),
                    "failed": count(value.get("failed")),
                    "p90_ms": number(latency.get("p90_ms")),
                    "p95_ms": number(latency.get("p95_ms")),
                    "recall_at_10": None,
                    "quality_status": "not_published",
                }
            )
        except (OSError, ValueError, TypeError):
            skipped += 1
    return {
        "state": "available" if experiments else "empty",
        "experiments": experiments,
        "skipped": skipped,
    }
