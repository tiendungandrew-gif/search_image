import base64
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, text, tuple_

from app.core.exceptions import AppError
from app.db.models import Image, ImageMetadata, IndexingJob, SearchIndex
from app.db.models.indexing import (
    IdempotencyRecord,
    ImageEmbedding,
    ImageObject,
    ImageTag,
    JobAttempt,
    JobItem,
)
from app.services.embeddings.clip_encoder import fingerprint
from app.services.ingestion.storage import object_key, put_original
from app.services.ingestion.validator import validate_image


def now():
    return datetime.now(UTC)


def key_valid(key):
    if not key or not 1 <= len(key) <= 128 or any(ord(c) < 32 or ord(c) > 126 for c in key):
        raise AppError(400, "IDEMPOTENCY_KEY_REQUIRED", "Cần Idempotency-Key ASCII 1–128 ký tự")


async def lock(session, value):
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:value,0))"), {"value": str(value)}
    )


async def idempotency(session, endpoint, key, digest):
    key_valid(key)
    await lock(session, "idempotency:" + endpoint + key)
    record = await session.get(IdempotencyRecord, ("operator", endpoint, key))
    if record:
        if record.request_sha256 != digest:
            raise AppError(409, "IDEMPOTENCY_CONFLICT", "Key đã dùng với nội dung khác")
        if record.status == "completed":
            return record, True
        return record, False
    record = IdempotencyRecord(
        principal_id="operator",
        endpoint=endpoint,
        key=key,
        request_sha256=digest,
        status="processing",
        expires_at=now() + timedelta(days=1),
    )
    session.add(record)
    return record, False


def new_job(session, index_id, kind="ingest_upload", **fields):
    job = IndexingJob(
        id=uuid4(),
        kind=kind,
        status="queued",
        target_index_id=index_id,
        created_by="operator",
        request_id=uuid4(),
        total_items=1,
        **fields,
    )
    session.add(job)
    return job


def new_item(session, job, image, index_id, status="queued", source_ref=None):
    item = JobItem(
        id=uuid4(),
        job_id=job.id,
        image_id=image.id,
        index_id=index_id,
        source_identity=str(image.id),
        source_ref=source_ref or {},
        status=status,
        stage="object",
    )
    session.add(item)
    return item


async def target(session, index_id):
    if not index_id:
        raise AppError(503, "NOT_READY", "Chưa cấu hình ingestion index")
    index = await session.get(SearchIndex, UUID(str(index_id)), with_for_update=True)
    if not index or index.status not in {"building", "ready"}:
        raise AppError(409, "MODEL_INDEX_MISMATCH", "Target index không chấp nhận indexing")
    return index


async def ingest(services, data, metadata, key, index_id=None):
    key_valid(key)
    settings = services.settings
    validated = await validate_image(data, settings)
    digest = fingerprint(
        {
            "sha256": validated.sha256,
            "metadata": metadata.fingerprint_data(),
            "index": str(index_id or settings.ingestion_index_id),
        }
    )
    async with services.database.sessions() as session, session.begin():
        from app.services.catalog import ensure_dataset

        await ensure_dataset(session, metadata.source_dataset)
        index = await target(session, index_id or settings.ingestion_index_id)
        record, completed = await idempotency(session, "/images", key, digest)
        if completed:
            return record.response_status, record.response_ref
        if record.lease_expires_at and record.lease_expires_at > now():
            raise AppError(
                409, "IDEMPOTENCY_IN_PROGRESS", "Upload cùng key đang được xử lý", retryable=True
            )
        reserved_response = record.response_ref
        await lock(session, "image:" + validated.sha256)
        image = await session.scalar(
            select(Image).where(Image.sha256 == validated.sha256).with_for_update()
        )
        duplicate = image is not None
        if image and image.status in {"deleting", "deleted"}:
            raise AppError(409, "IMAGE_DELETED", "Ảnh đã được đánh dấu xóa")
        if image is None:
            image = Image(
                id=uuid4(),
                sha256=validated.sha256,
                status="pending_upload",
                media_type=validated.media_type,
                byte_size=len(data),
                width=validated.width,
                height=validated.height,
                created_by="operator",
                metadata_revision=1,
            )
            session.add(image)
            await session.flush()
            values = metadata.model_dump(exclude={"tags"})
            session.add(ImageMetadata(image_id=image.id, **values))
            for tag in metadata.tags:
                session.add(ImageTag(image_id=image.id, tag=tag, source="provided"))
        embedding = await session.get(ImageEmbedding, (image.id, index.id))
        live = await session.scalar(
            select(JobItem).where(
                JobItem.image_id == image.id,
                JobItem.index_id == index.id,
                JobItem.status.in_(["awaiting_input", "queued", "processing", "retry_wait"]),
            )
        )
        if (
            not reserved_response
            and embedding
            and embedding.status == "ready"
            and image.status == "available"
        ):
            response = {
                "image_id": str(image.id),
                "duplicate": True,
                "job_id": None,
                "status": "available",
                "status_url": None,
            }
            record.status = "completed"
            record.response_status = 200
            record.response_ref = response
            return 200, response
        if reserved_response:
            job_id = UUID(reserved_response["job_id"])
        elif live:
            job_id = live.job_id
        else:
            job = new_job(session, index.id)
            await session.flush()
            live = new_item(session, job, image, index.id, status="awaiting_input")
            job_id = job.id
        response = reserved_response or {
            "image_id": str(image.id),
            "duplicate": duplicate,
            "job_id": str(job_id),
            "status": "queued",
            "status_url": f"/api/v1/index/jobs/{job_id}",
        }
        record.response_ref = response
        record.response_status = 202
        record.lease_expires_at = now() + timedelta(seconds=settings.ingestion_timeout_seconds)
    # DB reservation trước I/O: crash sau PUT có thể recover bằng original key xác định.
    try:
        await put_original(services, image, data)
        await accept_original(services, image.id)
    except Exception:
        async with services.database.sessions() as session, session.begin():
            current = await session.get(
                IdempotencyRecord, ("operator", "/images", key), with_for_update=True
            )
            if current and current.status == "processing":
                current.lease_expires_at = now()
        raise
    async with services.database.sessions() as session, session.begin():
        record = await session.get(
            IdempotencyRecord, ("operator", "/images", key), with_for_update=True
        )
        record.status = "completed"
        record.response_status = 202
        record.response_ref = response
        record.lease_expires_at = None
    return 202, response


async def accept_original(services, image_id):
    from app.services.ingestion.storage import get_original

    async with services.database.sessions() as session:
        image = await session.get(Image, image_id)
    await get_original(services, image)
    async with services.database.sessions() as session, session.begin():
        image = await session.get(Image, image_id, with_for_update=True)
        if image.status in {"deleting", "deleted"}:
            raise ValueError("IMAGE_DELETED")
        obj = await session.scalar(
            select(ImageObject).where(
                ImageObject.image_id == image.id, ImageObject.role == "original"
            )
        )
        if obj is None:
            session.add(
                ImageObject(
                    id=uuid4(),
                    image_id=image.id,
                    role="original",
                    derivative_version="original",
                    bucket=services.minio.bucket,
                    object_key=object_key(image),
                    sha256=image.sha256,
                    media_type=image.media_type,
                    byte_size=image.byte_size,
                    verified_at=now(),
                )
            )
        image.status = "available"
        items = (
            await session.scalars(
                select(JobItem)
                .where(JobItem.image_id == image.id, JobItem.status == "awaiting_input")
                .with_for_update()
            )
        ).all()
        for item in items:
            item.status = "queued"


async def summarize(session, job_id):
    job = await session.get(IndexingJob, job_id, with_for_update=True)
    states = Counter(
        (await session.scalars(select(JobItem.status).where(JobItem.job_id == job_id))).all()
    )
    terminal = states["succeeded"] + states["failed"]
    if terminal == job.total_items:
        job.status = (
            "succeeded"
            if not states["failed"]
            else ("partial_failed" if states["succeeded"] else "failed")
        )
        job.finished_at = now()
    elif states["processing"] or terminal:
        job.status = "running"
    job.updated_at = now()


async def job_response(services, job_id, limit=50, cursor=None):
    async with services.database.sessions() as session:
        job = await session.get(IndexingJob, job_id)
        if job is None:
            raise AppError(404, "JOB_NOT_FOUND", "Không tìm thấy job")
        states = dict(
            (
                await session.execute(
                    select(JobItem.status, func.count())
                    .where(JobItem.job_id == job_id)
                    .group_by(JobItem.status)
                )
            ).all()
        )
        query = select(JobItem).where(JobItem.job_id == job_id)
        started_at = await session.scalar(
            select(func.min(JobAttempt.started_at))
            .join(JobItem, JobAttempt.item_id == JobItem.id)
            .where(JobItem.job_id == job_id)
        )
        errors = dict(
            (
                await session.execute(
                    select(JobItem.last_error_code, func.count())
                    .where(JobItem.job_id == job_id, JobItem.status == "failed")
                    .group_by(JobItem.last_error_code)
                )
            ).all()
        )
        if cursor:
            try:
                value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if value["job"] != str(job_id) or value["watermark"] != str(job.total_items):
                    raise ValueError()
                query = query.where(
                    tuple_(JobItem.created_at, JobItem.id)
                    > tuple_(datetime.fromisoformat(value["created_at"]), UUID(value["after"]))
                )
            except Exception:
                raise AppError(422, "INVALID_CURSOR", "Cursor không hợp lệ") from None
        items = (
            await session.scalars(query.order_by(JobItem.created_at, JobItem.id).limit(limit + 1))
        ).all()
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "job": str(job_id),
                        "after": str(items[limit - 1].id),
                        "created_at": items[limit - 1].created_at.isoformat(),
                        "watermark": str(job.total_items),
                    }
                ).encode()
            ).decode()
            if len(items) > limit
            else None
        )
        return {
            "job_id": job.id,
            "kind": job.kind,
            "status": job.status,
            "target_index_id": job.target_index_id,
            "counts": {
                "total": job.total_items,
                **{
                    key: states.get(key, 0)
                    for key in [
                        "awaiting_input",
                        "queued",
                        "processing",
                        "retry_wait",
                        "succeeded",
                        "failed",
                    ]
                },
            },
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "finished_at": job.finished_at,
            "started_at": started_at,
            "error_summary": {key or "UNKNOWN": value for key, value in errors.items()},
            "items": [
                {
                    key: getattr(item, key)
                    for key in [
                        "image_id",
                        "index_id",
                        "status",
                        "stage",
                        "attempt_count",
                        "last_error_code",
                        "next_attempt_at",
                    ]
                }
                | {"item_id": item.id}
                for item in items[:limit]
            ],
            "next_cursor": next_cursor,
        }
