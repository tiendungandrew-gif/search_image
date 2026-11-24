"""Reuse isolated decoder processes without changing decoder results or image limits."""

import json
import os
import queue
import select
import struct
import subprocess
import sys
import time
from pathlib import Path

from app.core.exceptions import AppError


def read_exact(fd, size, deadline):
    data = bytearray()
    while len(data) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError
        chunk = os.read(fd, min(65536, size - len(data)))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)


class DecoderPool:
    def __init__(self, size=3, clip_preprocess=False):
        self.clip_preprocess = clip_preprocess
        self.available = queue.Queue()
        for _ in range(size):
            self.available.put(None)

    def __call__(self, data, settings, pixels=False):
        if not data or len(data) > settings.image_max_upload_mb * 1024**2:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "Ảnh vượt giới hạn dung lượng hoặc rỗng")
        process = self.available.get()
        try:
            if process is None or process.poll() is not None:
                process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).with_name("decoder_server.py"))],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            header = json.dumps(
                {
                    "bytes": len(data),
                    "pixels_limit": settings.image_max_pixels,
                    "side_limit": settings.image_max_side,
                    "pixels": pixels,
                    "clip_preprocess": self.clip_preprocess,
                }
            ).encode()
            deadline = time.monotonic() + settings.image_decode_timeout_seconds
            process.stdin.write(struct.pack("!I", len(header)) + header + data)
            process.stdin.flush()
            status, size = struct.unpack("!BI", read_exact(process.stdout.fileno(), 5, deadline))
            if size > 160 * 1024**2:
                raise EOFError
            body = read_exact(process.stdout.fileno(), size, deadline)
            if status:
                code = json.loads(body)["error"]
                raise AppError(
                    415 if code == "UNSUPPORTED_MEDIA" else 422,
                    code,
                    "Ảnh không hợp lệ hoặc không được hỗ trợ",
                )
            return body
        except (TimeoutError, EOFError, BrokenPipeError):
            if process:
                process.kill()
                process.wait()
                process = None
            raise AppError(422, "DECODE_TIMEOUT", "Ảnh vượt giới hạn thời gian decode") from None
        finally:
            self.available.put(process)


def install(size=3, clip_preprocess=False):
    from app.services.ingestion import validator

    validator.run_decoder = DecoderPool(size, clip_preprocess)
