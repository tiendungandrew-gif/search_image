"""Dataset content and bounded index workflows for authenticated administrators."""

import json
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import UploadFile

from app.core.access import UNASSIGNED
from app.core.auth import require_admin_access
from app.core.exceptions import AppError
from app.db.models import EmbeddingModel, Image, ImageMetadata, IndexingJob, SearchIndex
from app.db.models.access import AccessDataset, ImageModeration
from app.db.models.indexing import ActiveSearchIndex, ImageTag, JobItem
from app.repositories.knowledge_import import import_knowledge
from app.schemas.access import ImageEdit, IndexAction, IndexCreate, ReindexInput
from app.schemas.ingestion import ImageMetadataInput, JobInput
from app.services.accounts import audit
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, job_response, lock, new_item, new_job, now
from app.services.indexing.submission import submit_job
from app.services.search.registry import SearchRegistry

router = APIRouter(
    prefix="/admin", tags=["Administration"], dependencies=[Depends(require_admin_access)]
)


@router.get("/images")
async def images(
    request: Request,
    dataset_id: UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    statement = (
        select(Image, ImageMetadata, ImageModeration.hidden)
        .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
        .outerjoin(ImageModeration, ImageModeration.image_id == Image.id)
        .where(Image.status.not_in(["deleted", "deleting"]))
    )
    async with request.app.state.services.database.sessions() as session:
        if dataset_id:
            dataset = await session.get(AccessDataset, dataset_id)
            if dataset is None:
                raise AppError(404, "DATASET_NOT_FOUND", "Không tìm thấy dataset")
            statement = statement.where(
                ImageMetadata.source_dataset.is_(None)
                if dataset.key == UNASSIGNED
                else ImageMetadata.source_dataset == dataset.key
            )
        total = await session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = (
            await session.execute(
                statement.order_by(Image.created_at.desc(), Image.id).offset(offset).limit(limit)
            )
        ).all()
        tags = (
            await session.execute(
                select(ImageTag.image_id, ImageTag.tag).where(
                    ImageTag.image_id.in_([i.id for i, _, _ in rows])
                )
            )
        ).all()
    return {
        "total": total,
        "images": [
            {
                "id": str(i.id),
                "title": m.title if m else None,
                "caption": m.caption if m else None,
                "source_dataset": m.source_dataset if m else None,
                "status": i.status,
                "hidden": bool(hidden),
                "width": i.width,
                "height": i.height,
                "tags": [tag for iid, tag in tags if iid == i.id],
                "thumbnail_url": f"/api/v1/images/{i.id}/content?variant=thumbnail",
            }
            for i, m, hidden in rows
        ],
    }


@router.post("/images/upload", status_code=202)
async def upload_image(request: Request):
    try:
        async with request.form(max_files=1, max_fields=2, max_part_size=65536) as form:
            if set(form.keys()) != {"image", "dataset_id", "metadata"} or any(
                len(form.getlist(k)) != 1 for k in form
            ):
                raise ValueError("fields")
            file = form["image"]
            if not isinstance(file, UploadFile):
                raise ValueError("file")
            dataset_id = UUID(str(form["dataset_id"]))
            async with request.app.state.services.database.sessions() as session:
                dataset = await session.get(AccessDataset, dataset_id)
                active = await session.get(ActiveSearchIndex, "default")
            if dataset is None or not dataset.is_active or dataset.key == UNASSIGNED:
                raise AppError(422, "DATASET_NOT_FOUND", "Chọn dataset đang hoạt động")
            if active is None:
                raise AppError(
                    409, "INDEX_NOT_READY", "Chuẩn bị model và active index trước khi nhập ảnh"
                )
            values = json.loads(form["metadata"])
            if not isinstance(values, dict) or set(values) - {
                "title",
                "caption",
                "tags",
                "license",
                "rights_ref",
            }:
                raise ValueError("metadata")
            metadata = ImageMetadataInput.model_validate({**values, "source_dataset": dataset.key})
            data = await file.read(request.app.state.settings.image_max_upload_mb * 1024**2 + 1)
        key = request.headers.get("idempotency-key")
        status, result = await ingest(
            request.app.state.services, data, metadata, key, index_id=active.index_id
        )
        async with request.app.state.services.database.sessions() as session, session.begin():
            audit(
                session,
                request.state.principal,
                "image.uploaded",
                result["image_id"],
                dataset_id=str(dataset_id),
                duplicate=result["duplicate"],
            )
        return {**result, "http_status": status}
    except (ValueError, TypeError, ValidationError):
        raise AppError(422, "INVALID_INPUT", "Ảnh hoặc metadata nhập không hợp lệ") from None


@router.patch("/images/{image_id}")
async def edit_image(image_id: UUID, body: ImageEdit, request: Request):
    services = request.app.state.services
    async with services.database.sessions() as session, session.begin():
        await lock(session, "active-search:default")
        image = await session.get(Image, image_id, with_for_update=True)
        dataset = await session.get(AccessDataset, body.dataset_id)
        active = await session.get(ActiveSearchIndex, "default")
        if image is None or image.status != "available":
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh sẵn sàng")
        if dataset is None or not dataset.is_active or dataset.key == UNASSIGNED:
            raise AppError(422, "DATASET_NOT_FOUND", "Chọn dataset đang hoạt động")
        if active is None:
            raise AppError(409, "INDEX_NOT_READY", "Chưa có active index")
        await lock(session, "task:" + str(image_id) + str(active.index_id))
        live = await session.scalar(
            select(JobItem.id)
            .where(
                JobItem.image_id == image_id,
                JobItem.status.in_(["awaiting_input", "queued", "processing", "retry_wait"]),
            )
            .limit(1)
        )
        if live:
            raise AppError(
                409, "INDEX_JOB_CONFLICT", "Ảnh đang được xử lý; thử lại khi job hoàn tất"
            )
        metadata = ImageMetadataInput(
            source_dataset=dataset.key,
            title=body.title,
            caption=body.caption,
            tags=body.tags,
            license="editorial",
            rights_ref="admin:" + request.state.principal.username,
        )
        current = await session.get(ImageMetadata, image_id)
        if current is None:
            current = ImageMetadata(image_id=image_id)
            session.add(current)
        current.title, current.caption, current.source_dataset = (
            metadata.title,
            metadata.caption,
            dataset.key,
        )
        current.caption_source = "admin:" + request.state.principal.username
        image.metadata_revision += 1
        await session.execute(delete(ImageTag).where(ImageTag.image_id == image_id))
        session.add_all(
            ImageTag(image_id=image_id, tag=tag, source="provided", verified=False)
            for tag in metadata.tags
        )
        job = new_job(session, active.index_id)
        job.created_by = request.state.principal.username
        await session.flush()
        new_item(session, job, image, active.index_id)
        audit(
            session,
            request.state.principal,
            "image.metadata_updated",
            image_id,
            dataset_id=str(dataset.id),
            job_id=str(job.id),
        )
    return {
        "status": "queued",
        "job_id": str(job.id),
        "message": "Metadata đã lưu; ảnh trở lại tìm kiếm khi worker cập nhật xong",
    }


@router.delete("/images/{image_id}")
async def hide_image(image_id: UUID, request: Request):
    return await moderate(image_id, True, request)


@router.post("/images/{image_id}/restore")
async def restore_image(image_id: UUID, request: Request):
    return await moderate(image_id, False, request)


async def moderate(image_id, hidden, request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        if await session.get(Image, image_id) is None:
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        query = insert(ImageModeration).values(image_id=image_id, hidden=hidden)
        await session.execute(
            query.on_conflict_do_update(
                index_elements=[ImageModeration.image_id], set_={"hidden": hidden}
            )
        )
        audit(
            session,
            request.state.principal,
            "image.hidden" if hidden else "image.restored",
            image_id,
        )
    return {"status": "hidden" if hidden else "restored", "original_preserved": True}


@router.get("/indexes")
async def indexes(request: Request):
    services = request.app.state.services
    async with services.database.sessions() as session:
        rows = (
            await session.execute(
                select(SearchIndex, EmbeddingModel)
                .join(EmbeddingModel, EmbeddingModel.id == SearchIndex.model_id)
                .order_by(SearchIndex.created_at.desc())
                .limit(100)
            )
        ).all()
        active = await session.get(ActiveSearchIndex, "default")
        jobs = list(
            (
                await session.scalars(
                    select(IndexingJob).order_by(IndexingJob.created_at.desc()).limit(30)
                )
            ).all()
        )
    return {
        "indexes": [
            {
                "id": str(i.id),
                "model_id": str(m.id),
                "model": m.model_name,
                "dimension": m.dimension,
                "version": i.config.get("version", ""),
                "status": i.status,
                "collection": i.collection_name,
                "active": bool(active and active.index_id == i.id),
            }
            for i, m in rows
        ],
        "jobs": [
            {
                "id": str(j.id),
                "kind": j.kind,
                "status": j.status,
                "total": j.total_items,
                "index_id": str(j.target_index_id) if j.target_index_id else None,
            }
            for j in jobs
        ],
    }


@router.post("/indexes", status_code=201)
async def create_index(body: IndexCreate, request: Request):
    services = request.app.state.services
    async with services.database.sessions() as session:
        model = await session.get(EmbeddingModel, body.model_id)
    if model is None:
        raise AppError(
            404, "MODEL_NOT_FOUND", "Model chưa được đăng ký; chuẩn bị bằng công cụ vận hành"
        )
    descriptor = SimpleNamespace(
        manifest_sha256=model.manifest_sha256, dimension=model.dimension, manifest=model.manifest
    )
    index, _ = await CollectionManager(services).register(descriptor, body.version)
    async with services.database.sessions() as session, session.begin():
        audit(session, request.state.principal, "index.created", index.id)
    return {"id": str(index.id), "status": index.status}


@router.post("/indexes/reindex", status_code=202)
async def reindex(body: ReindexInput, request: Request):
    services = request.app.state.services
    async with services.database.sessions() as session:
        query = (
            select(Image.id)
            .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
            .where(Image.status == "available")
        )
        if body.dataset_id:
            dataset = await session.get(AccessDataset, body.dataset_id)
            if not dataset:
                raise AppError(404, "DATASET_NOT_FOUND", "Không tìm thấy dataset")
            query = query.where(
                ImageMetadata.source_dataset.is_(None)
                if dataset.key == UNASSIGNED
                else ImageMetadata.source_dataset == dataset.key
            )
        ids = list((await session.scalars(query.order_by(Image.id).limit(5001))).all())
    if not ids:
        raise AppError(409, "EMPTY_DATASET", "Chưa có ảnh để lập chỉ mục")
    if len(ids) > 5000:
        raise AppError(422, "BATCH_LIMIT", "Dùng CLI cho lượt reindex trên 5000 ảnh")
    jobs = []
    for start in range(0, len(ids), 500):
        options = JobInput(
            kind="reindex", target_index_id=body.target_index_id, image_ids=ids[start : start + 500]
        )
        key = (
            "admin-reindex-"
            + str(body.target_index_id)
            + "-"
            + str(start)
            + "-"
            + (str(body.dataset_id) if body.dataset_id else "all")
        )
        jobs.append(await submit_job(services, options, key))
    async with services.database.sessions() as session, session.begin():
        audit(
            session,
            request.state.principal,
            "index.reindex_queued",
            body.target_index_id,
            images=len(ids),
        )
    return {"status": "queued", "jobs": jobs, "images": len(ids)}


@router.get("/jobs/{job_id}")
async def job(job_id: UUID, request: Request):
    return await job_response(request.app.state.services, job_id)


@router.post("/indexes/verify")
async def verify(body: IndexAction, request: Request):
    services = request.app.state.services
    report = await verify_index(services, body.index_id)
    if report["status"] == "pass":
        async with services.database.sessions() as session, session.begin():
            index = await session.get(SearchIndex, body.index_id, with_for_update=True)
            index.status, index.validated_at = "ready", now()
            index.corpus_snapshot_ref = "admin-verified:" + str(report["verified_images"])
            audit(session, request.state.principal, "index.verified", index.id)
    return report


@router.post("/indexes/activate")
async def activate(body: IndexAction, request: Request):
    services = request.app.state.services
    runtime = request.app.state.search_runtime
    if runtime is None or not runtime.available:
        raise AppError(
            409, "RUNTIME_NOT_READY", "Khởi tạo search runtime bằng công cụ vận hành trước"
        )
    candidate = SearchRegistry(services, runtime.encoder)
    await candidate.load(body.index_id)
    report = await verify_index(services, body.index_id)
    if report["status"] != "pass":
        raise AppError(409, "INDEX_NOT_VALIDATED", "Index chưa vượt kiểm tra nhất quán")
    async with services.database.sessions() as session, session.begin():
        await lock(session, "active-search:default")
        pointer = await session.get(ActiveSearchIndex, "default", with_for_update=True)
        index = await session.get(SearchIndex, body.index_id, with_for_update=True)
        if index.status != "ready" or index.model_id != candidate.model.id:
            raise AppError(409, "INDEX_CHANGED", "Index vừa thay đổi; kiểm tra lại")
        pending = await session.scalar(
            select(JobItem.id)
            .where(
                JobItem.index_id == index.id,
                JobItem.status.in_(["queued", "awaiting_input", "processing", "retry_wait"]),
            )
            .limit(1)
        )
        if pending:
            raise AppError(409, "INDEX_JOB_CONFLICT", "Index còn job chưa hoàn tất")
        if pointer is None:
            pointer = ActiveSearchIndex(
                corpus_key="default", index_id=index.id, generation=1, activated_at=now()
            )
            session.add(pointer)
        elif pointer.index_id != index.id:
            pointer.index_id, pointer.generation, pointer.activated_at = (
                index.id,
                pointer.generation + 1,
                now(),
            )
        candidate.generation = pointer.generation
        audit(
            session,
            request.state.principal,
            "index.activated",
            index.id,
            generation=pointer.generation,
        )
    runtime.registry = candidate
    return {
        "status": "active",
        "index_id": str(candidate.index.id),
        "generation": candidate.generation,
    }


@router.post("/knowledge")
async def knowledge(request: Request):
    from app.repositories.knowledge_import import KnowledgeImport

    try:
        body = await request.json()
        if set(body) != {"dataset_id", "apply", "knowledge"} or not isinstance(body["apply"], bool):
            raise ValueError("fields")
        dataset_id = UUID(body["dataset_id"])
        payload = KnowledgeImport.model_validate(body["knowledge"])
    except (ValueError, TypeError, KeyError, ValidationError):
        raise AppError(422, "INVALID_INPUT", "Gói tri thức không hợp lệ") from None
    services = request.app.state.services
    async with services.database.sessions() as session:
        dataset = await session.get(AccessDataset, dataset_id)
    if dataset is None or not dataset.is_active:
        raise AppError(404, "DATASET_NOT_FOUND", "Không tìm thấy dataset đang hoạt động")
    async with services.database.sessions() as session:
        from app.db.models.knowledge import Entity

        entity_ids = {e.id for e in payload.entities}
        referenced = (
            {r.subject_id for r in payload.relationships}
            | {r.object_id for r in payload.relationships}
            | {r.entity_id for r in payload.image_entities}
        )
        existing = set(
            (
                await session.scalars(
                    select(Entity.id).where(Entity.id.in_(referenced - entity_ids))
                )
            ).all()
        )
        if referenced - entity_ids - existing:
            raise AppError(
                422, "KNOWLEDGE_REJECTED", "Gói tri thức tham chiếu thực thể chưa tồn tại"
            )
        for link in payload.image_entities:
            metadata = await session.get(ImageMetadata, link.image_id)
            if metadata is None or (metadata.source_dataset or UNASSIGNED) != dataset.key:
                raise AppError(
                    422, "KNOWLEDGE_REJECTED", "Liên kết ảnh phải thuộc thư viện đã chọn"
                )
    try:
        result = await import_knowledge(
            services, payload.model_dump(mode="json"), apply=body["apply"], dataset_id=dataset_id
        )
    except (ValueError, ValidationError, IntegrityError):
        raise AppError(
            422, "KNOWLEDGE_REJECTED", "Kiểm tra nguồn, IDs và liên kết ảnh của gói tri thức"
        ) from None
    if body["apply"]:
        async with services.database.sessions() as session, session.begin():
            audit(
                session,
                request.state.principal,
                "knowledge.imported",
                dataset_id,
                entities=len(payload.entities),
                relationships=len(payload.relationships),
            )
    return result
