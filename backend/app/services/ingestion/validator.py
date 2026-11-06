import asyncio
import hashlib
import io
import json
import subprocess
import sys
from dataclasses import dataclass

from PIL import Image

from app.core.exceptions import AppError


@dataclass(frozen=True)
class ValidatedImage:
    sha256: str
    width: int
    height: int
    media_type: str
    byte_size: int


def run_decoder(data, settings, pixels=False):
    if not data or len(data) > settings.image_max_upload_mb * 1024**2:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "Ảnh vượt giới hạn dung lượng hoặc rỗng")
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.services.ingestion.decoder",
                str(settings.image_max_pixels),
                str(settings.image_max_side),
                *(["pixels"] if pixels else []),
            ],
            input=data,
            capture_output=True,
            timeout=settings.image_decode_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise AppError(422, "DECODE_TIMEOUT", "Ảnh vượt giới hạn thời gian decode") from None
    if proc.returncode:
        try:
            code = json.loads(proc.stdout)["error"]
        except Exception:
            code = "CORRUPT_IMAGE"
        raise AppError(
            415 if code == "UNSUPPORTED_MEDIA" else 422,
            code,
            "Ảnh không hợp lệ hoặc không được hỗ trợ",
        )
    return proc.stdout


async def validate_image(data, settings):
    details = json.loads(await asyncio.to_thread(run_decoder, data, settings))
    return ValidatedImage(hashlib.sha256(data).hexdigest(), byte_size=len(data), **details)


def prepared_image(data, settings):
    image = Image.open(io.BytesIO(run_decoder(data, settings, pixels=True)))
    image.load()
    return image
