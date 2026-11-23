import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from starlette.datastructures import UploadFile

from app.core.access import source_allowed, visible_image_clause
from app.core.auth import charge_usage, require_write_access
from app.core.exceptions import AppError
from app.core.guest import charge_guest_search, require_search_access
from app.db.models import Image, ImageMetadata
from app.db.models.indexing import ImageEmbedding, ImageTag
from app.schemas.ingestion import ImageMetadataInput, UploadResponse
from app.schemas.search import SearchRequest, SearchResponse
from app.services.indexing.jobs import ingest, key_valid
from app.services.ingestion.storage import get_original

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "",
    dependencies=[Depends(require_write_access)],
    status_code=202,
    response_model=UploadResponse,
    responses={200: {"model": UploadResponse}},
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["image", "metadata"],
                        "additionalProperties": False,
                        "properties": {
                            "image": {"type": "string", "format": "binary"},
                            "metadata": {
                                "type": "string",
                                "description": (
                                    "JSON ImageMetadataInput; source_dataset/license/rights_ref "
                                    "bắt buộc"
                                ),
                            },
                        },
                    }
                }
            },
        }
    },
)
async def upload(request: Request, idempotency_key: Annotated[str | None, Header()] = None):
    key_valid(idempotency_key)
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise AppError(415, "UNSUPPORTED_MEDIA", "Cần multipart/form-data")
    try:
        async with request.form(max_files=1, max_fields=1, max_part_size=65536) as form:
            if (
                set(form.keys()) != {"image", "metadata"}
                or len(form.getlist("image")) != 1
                or len(form.getlist("metadata")) != 1
            ):
                raise AppError(422, "INVALID_INPUT", "Cần đúng một image và metadata")
            file = form["image"]
            if not isinstance(file, UploadFile):
                raise AppError(422, "INVALID_INPUT", "Thiếu file ảnh")
            metadata = ImageMetadataInput.model_validate_json(form["metadata"])
            data = await file.read(request.app.state.settings.image_max_upload_mb * 1024**2 + 1)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
        raise AppError(422, "INVALID_INPUT", "Metadata/multipart không hợp lệ") from None
    try:
        status, body = await ingest(request.app.state.services, data, metadata, idempotency_key)
    except AppError:
        raise
    except Exception:
        raise AppError(
            503,
            "DEPENDENCY_UNAVAILABLE",
            "Không thể nhận ảnh bền vững; thử lại cùng key",
            retryable=True,
        ) from None
    return JSONResponse(body, status_code=status)


@router.get("/{image_id}", dependencies=[Depends(require_search_access)])
async def detail(image_id: UUID, request: Request):
    services = request.app.state.services
    async with services.database.sessions() as session:
        image = await session.get(Image, image_id)
        if (
            not image
            or image.status in {"deleting", "deleted"}
            or (request.state.principal.role == "guest" and image.status != "available")
        ):
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        meta = await session.get(ImageMetadata, image_id)
        visible = await session.scalar(
            select(Image.id).where(Image.id == image_id, visible_image_clause(Image.id))
        )
        if not visible or not source_allowed(meta.source_dataset if meta else None):
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        tags = list(
            (await session.scalars(select(ImageTag.tag).where(ImageTag.image_id == image_id))).all()
        )
        embeddings = (
            await session.scalars(select(ImageEmbedding).where(ImageEmbedding.image_id == image_id))
        ).all()
        url = f"/api/v1/images/{image.id}/content" if image.status == "available" else None
        return {
            "image_id": image.id,
            "status": image.status,
            "metadata": {
                "title": meta.title if meta else None,
                "caption": meta.caption if meta else None,
                "width": image.width,
                "height": image.height,
                "media_type": image.media_type,
                "tags": tags,
                "source_dataset": meta.source_dataset if meta else None,
                "city": meta.city if meta else None,
                "license": meta.license if meta else None,
            },
            "created_at": image.created_at,
            "indexing": []
            if request.state.principal.role == "guest"
            else [{"index_id": e.index_id, "status": e.status} for e in embeddings],
            "image_url": url + "?variant=original" if url else None,
            "thumbnail_url": url + "?variant=thumbnail" if url else None,
        }


@router.get("/{image_id}/content", dependencies=[Depends(require_search_access)])
async def content(
    image_id: UUID,
    request: Request,
    variant: Annotated[Literal["original", "thumbnail"], Query()] = "thumbnail",
):
    services = request.app.state.services
    async with services.database.sessions() as session:
        image = await session.get(Image, image_id)
        if not image or image.status != "available":
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        meta = await session.get(ImageMetadata, image_id)
        visible = await session.scalar(
            select(Image.id).where(Image.id == image_id, visible_image_clause(Image.id))
        )
        if not visible or not source_allowed(meta.source_dataset if meta else None):
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
    try:
        data = await get_original(services, image)
    except Exception:
        raise AppError(
            503, "DEPENDENCY_UNAVAILABLE", "Object không khả dụng", retryable=True
        ) from None
    # Thumbnail optional: contract cho phép fallback original với đúng MIME.
    return Response(
        data,
        media_type=image.media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.get("/{image_id}/related", dependencies=[Depends(require_search_access)],
            response_model=SearchResponse)
async def related_images(
    image_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=50)] = 24,
):
    from app.services.search.search_service import SearchService

    runtime = getattr(request.app.state, "search_runtime", None)
    settings = request.app.state.settings
    if not settings.search_enabled:
        raise AppError(409, "FEATURE_DISABLED", "Gợi ý ảnh liên quan chưa được bật")
    if runtime is None or not runtime.available:
        raise AppError(503, "NOT_READY", "Chưa sẵn sàng tải ảnh liên quan", retryable=True)
    limit = min(limit, settings.search_max_top_k)
    if request.state.principal.role == "guest":
        limit = min(limit, settings.guest_max_top_k)
        await charge_guest_search(request)
    else:
        await charge_usage(request, "search")
    # The existing retriever validates the reference's ACL/index and scopes every result.
    options = SearchRequest(mode="image", image_id=image_id, top_k=limit, exclude_self=True)
    try:
        return await SearchService(runtime).execute(options, request.state.request_id)
    except AppError:
        raise
    except Exception:
        raise AppError(
            503, "DEPENDENCY_UNAVAILABLE", "Chưa tải được ảnh liên quan", retryable=True
        ) from None
