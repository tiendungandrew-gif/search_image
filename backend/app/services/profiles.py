import io

from PIL import Image, ImageOps
from sqlalchemy import select

from app.core.access import source_clause, visible_image_clause
from app.db.models import Image as CatalogImage
from app.db.models import ImageMetadata
from app.services.chat import prepare_chat_image


def avatar_url(user):
    if not user.avatar_key:
        return None
    version = user.avatar_key.rsplit("/", 1)[-1].removesuffix(".jpg")
    return f"/api/v1/profiles/{user.id}/avatar?v={version}"


def prepare_avatar(data):
    encoded = prepare_chat_image(data)
    with Image.open(io.BytesIO(encoded)) as image:
        cropped = ImageOps.fit(image, (256, 256), method=Image.Resampling.LANCZOS)
        output = io.BytesIO()
        cropped.save(output, format="JPEG", quality=90)
        return output.getvalue()


def eligible_images():
    return (
        select(CatalogImage, ImageMetadata)
        .outerjoin(ImageMetadata, ImageMetadata.image_id == CatalogImage.id)
        .where(
            CatalogImage.status == "available",
            CatalogImage.deleted_at.is_(None),
            visible_image_clause(CatalogImage.id),
            source_clause(),
        )
    )
