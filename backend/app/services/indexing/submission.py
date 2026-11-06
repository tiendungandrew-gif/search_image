import json

from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.models import DatasetSource, Image, IndexingJob
from app.db.models.indexing import JobItem
from app.services.embeddings.clip_encoder import fingerprint
from app.services.indexing.jobs import idempotency, lock, new_item, new_job, target


async def submit_job(services, options, key):
    if options.kind == "delete":
        raise AppError(409, "FEATURE_DISABLED", "Delete job chưa được triển khai")
    digest = fingerprint(options.model_dump(mode="json"))
    async with services.database.sessions() as session, session.begin():
        record, completed = await idempotency(session, "/index/jobs", key, digest)
        if completed:
            return record.response_ref
        index_id = options.target_index_id
        source_id = None
        old_items = []
        if options.kind == "retry":
            old = await session.get(IndexingJob, options.retry_of)
            if not old:
                raise AppError(404, "JOB_NOT_FOUND", "Không tìm thấy job")
            old_items = list(
                (
                    await session.scalars(
                        select(JobItem).where(
                            JobItem.id.in_(options.item_ids),
                            JobItem.job_id == old.id,
                            JobItem.status == "failed",
                        )
                    )
                ).all()
            )
            if len(old_items) != len(options.item_ids):
                raise AppError(422, "INVALID_INPUT", "Chỉ retry các items failed thuộc job")
            if any(
                item.last_error_code in {"INVALID_SOURCE", "INVALID_EMBEDDING", "IMAGE_DELETED"}
                for item in old_items
            ):
                raise AppError(409, "PERMANENT_FAILURE", "Cần sửa nguồn lỗi trước khi tạo job mới")
            index_id = old.target_index_id
            image_ids = [item.image_id for item in old_items]
        elif options.kind == "ingest_dataset":
            source = await session.get(DatasetSource, options.source_id)
            if not source or not source.enabled:
                raise AppError(404, "SOURCE_NOT_FOUND", "Nguồn chưa đăng ký hoặc bị tắt")

            # Manifest object đã được CLI materialize; API không nhận đường dẫn máy chủ.
            def read_manifest():
                response = services.minio.client.get_object(
                    services.minio.bucket, source.manifest_ref
                )
                try:
                    return response.read(1024 * 1024 + 1)
                finally:
                    response.close()
                    response.release_conn()

            data = await services.minio.run(read_manifest)
            import hashlib

            if hashlib.sha256(data).hexdigest() != source.manifest_sha256:
                raise AppError(409, "SOURCE_CHANGED", "Manifest checksum không khớp")
            image_ids = json.loads(data)["image_ids"]
            source_id = source.id
            if not 1 <= len(image_ids) <= 1000:
                raise AppError(422, "INVALID_INPUT", "Manifest vượt batch cap")
        else:
            image_ids = options.image_ids
        index = await target(session, index_id)
        if options.kind == "reindex" and index.status != "building":
            raise AppError(409, "INDEX_NOT_BUILDING", "Reindex cần collection building mới")
        images = []
        for image_id in sorted(image_ids, key=str):
            await lock(session, "task:" + str(image_id) + str(index.id))
            image = await session.get(Image, image_id, with_for_update=True)
            if not image or image.status != "available":
                raise AppError(404, "IMAGE_NOT_FOUND", "Ảnh chưa available")
            live = await session.scalar(
                select(JobItem.id).where(
                    JobItem.image_id == image.id,
                    JobItem.index_id == index.id,
                    JobItem.status.in_(["awaiting_input", "queued", "processing", "retry_wait"]),
                )
            )
            if live:
                raise AppError(409, "INDEX_JOB_CONFLICT", "Ảnh/index có task đang chạy")
            images.append(image)
        job = new_job(
            session,
            index.id,
            options.kind,
            **({"retry_of": options.retry_of} if old_items else {}),
            source_id=source_id,
        )
        job.total_items = len(images)
        await session.flush()
        for image in images:
            new_item(session, job, image, index.id)
        response = {
            "job_id": str(job.id),
            "status": "queued",
            "status_url": f"/api/v1/index/jobs/{job.id}",
        }
        record.status = "completed"
        record.response_status = 202
        record.response_ref = response
        return response
