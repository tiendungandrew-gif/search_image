import io

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.schemas.ingestion import ImageMetadataInput, JobInput
from app.services.embeddings.clip_encoder import normalized_vectors
from app.services.indexing.worker import retry_delay
from app.services.ingestion.validator import prepared_image, validate_image


def picture(format="PNG", mode="RGB", size=(20, 10), **kwargs):
    buf = io.BytesIO()
    Image.new(mode, size).save(buf, format=format, **kwargs)
    return buf.getvalue()


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
async def test_real_decode_and_hash(settings, format):
    import hashlib

    data = picture(format)
    validated = await validate_image(data, settings)
    assert validated.sha256 == hashlib.sha256(data).hexdigest()
    assert (validated.width, validated.height) == (20, 10)


@pytest.mark.parametrize("data", [b"garbage", b"\x89PNG\r\n\x1a\n", b"<svg>not an image</svg>"])
async def test_corrupt_content_rejected(settings, data):
    with pytest.raises(AppError):
        await validate_image(data, settings)


async def test_unsupported_format_and_limits(settings):
    with pytest.raises(AppError) as error:
        await validate_image(picture("GIF"), settings)
    assert error.value.code == "UNSUPPORTED_MEDIA"
    settings.image_max_pixels = 10
    with pytest.raises(AppError) as error:
        await validate_image(picture(), settings)
    assert error.value.code == "IMAGE_PIXEL_LIMIT"
    with pytest.raises(AppError) as error:
        await validate_image(b"x" * (21 * 1024**2), settings)
    assert error.value.status == 413


def test_exif_orientation_rgb_and_alpha(settings):
    exif = Image.Exif()
    exif[274] = 6
    data = picture("JPEG", size=(20, 10), exif=exif)
    image = prepared_image(data, settings)
    assert image.size == (10, 20) and image.mode == "RGB"
    transparent = prepared_image(picture(mode="RGBA"), settings)
    assert transparent.mode == "RGB" and transparent.getpixel((0, 0)) == (255, 255, 255)


@pytest.mark.parametrize(
    "values", [[[0, 0]], [[float("nan"), 1]], [[float("inf"), 1]], [[1, 2, 3]], [1, 2]]
)
def test_invalid_vectors(values):
    with pytest.raises(ValueError):
        normalized_vectors(values, 2)


def test_real_normalization_and_retry_bounds():
    # Isolated numeric unit fixture, không dùng cho production inference.
    vectors = normalized_vectors([[3, 4]], 2)
    np.testing.assert_allclose(vectors, [[0.6, 0.8]])
    assert 4 <= retry_delay(2) <= 5
    assert 60 <= retry_delay(10) <= 61


def test_metadata_and_model_config_validation(settings):
    metadata = ImageMetadataInput(
        source_dataset="fixture", license="CC0", rights_ref="test", tags=[" CAT ", "cat"]
    )
    assert metadata.tags == ["cat"]
    with pytest.raises(ValidationError):
        ImageMetadataInput(source_dataset="fixture", license="CC0", rights_ref="")
    with pytest.raises(ValidationError):
        JobInput(kind="reindex", image_ids=[])
    with pytest.raises(ValidationError):
        type(settings)(**(settings.model_dump() | {"embedding_model_revision": "main"}))
