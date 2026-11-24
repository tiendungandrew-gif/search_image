"""Bounded long-lived transport around the application's unchanged image decoder."""

import ctypes
import io
import json
import math
import resource
import struct
import sys

from app.services.ingestion.decoder import decode

resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))


def exact(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)


while True:
    try:
        size = struct.unpack("!I", exact(sys.stdin.buffer, 4))[0]
        if size > 20 * 1024**2 + 1024:
            raise SystemExit(1)
        header = json.loads(exact(sys.stdin.buffer, size))
        raw = exact(sys.stdin.buffer, header["bytes"])
    except EOFError:
        break
    usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu_limit = math.ceil(usage.ru_utime + usage.ru_stime) + 3
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, resource.RLIM_INFINITY))
    try:
        if not raw or len(raw) > 20 * 1024**2:
            raise ValueError("PAYLOAD_TOO_LARGE")
        image, media = decode(raw, header["pixels_limit"], header["side_limit"])
        try:
            if header["pixels"]:
                if header.get("clip_preprocess"):
                    from clip_pixels import prepare

                    transformed = prepare(image)
                    image.close()
                    image = transformed
                out = io.BytesIO()
                image.save(out, format="PNG", compress_level=0)
                body = out.getvalue()
            else:
                body = json.dumps(
                    {"width": image.width, "height": image.height, "media_type": media}
                ).encode()
        finally:
            image.close()
        status = 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) else "CORRUPT_IMAGE"
        if code not in {
            "UNSUPPORTED_MEDIA",
            "MULTIFRAME_IMAGE",
            "IMAGE_PIXEL_LIMIT",
            "PAYLOAD_TOO_LARGE",
        }:
            code = "CORRUPT_IMAGE"
        body = json.dumps({"error": code}).encode()
        status = 1
    sys.stdout.buffer.write(struct.pack("!BI", status, len(body)) + body)
    sys.stdout.buffer.flush()
    del raw, body
    getattr(ctypes.CDLL(None), "malloc_trim", lambda _: 0)(0)
