"""Decoder riêng, giới hạn tài nguyên; stdin bytes, stdout JSON hoặc sanitized PNG."""

import io
import json
import resource
import sys
import warnings

from PIL import Image, ImageOps


def decode(data: bytes, max_pixels: int, max_side: int):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        image = Image.open(io.BytesIO(data))
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("UNSUPPORTED_MEDIA")
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("MULTIFRAME_IMAGE")
        if image.width * image.height > max_pixels or max(image.size) > max_side:
            raise ValueError("IMAGE_PIXEL_LIMIT")
        media = Image.MIME[image.format]
        image.load()
        image = ImageOps.exif_transpose(image)
        if image.mode in {"RGBA", "LA", "P"}:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            background.alpha_composite(rgba)
            image = background.convert("RGB")
        else:
            image = image.convert("RGB")
        image.info.clear()
        return image, media


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    try:
        data = sys.stdin.buffer.read(20 * 1024**2 + 1)
        if not data or len(data) > 20 * 1024**2:
            raise ValueError("PAYLOAD_TOO_LARGE")
        image, media = decode(data, int(sys.argv[1]), int(sys.argv[2]))
        if len(sys.argv) > 3 and sys.argv[3] == "pixels":
            image.save(sys.stdout.buffer, format="PNG")
        else:
            print(json.dumps({"width": image.width, "height": image.height, "media_type": media}))
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) else "CORRUPT_IMAGE"
        if code not in {
            "UNSUPPORTED_MEDIA",
            "MULTIFRAME_IMAGE",
            "IMAGE_PIXEL_LIMIT",
            "PAYLOAD_TOO_LARGE",
        }:
            code = "CORRUPT_IMAGE"
        print(json.dumps({"error": code}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
