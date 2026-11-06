"""Một decoder process đã preload/API process; JSON+bytes IPC, không pickle."""

import json
import os
import select
import struct
import subprocess
import sys
from time import monotonic

from PIL import Image

from app.core.exceptions import AppError


class QueryDecoder:
    def __init__(self, settings):
        self.settings = settings
        self.process = None

    def stop(self):
        process, self.process = self.process, None
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()

    def transfer(self, stream, deadline, *, data=None, size=0):
        descriptor = stream.fileno()
        output = []
        position = 0
        remaining = len(data) if data is not None else size
        while remaining:
            wait = deadline - monotonic()
            if wait <= 0:
                raise TimeoutError()
            readers, writers = ([descriptor], []) if data is None else ([], [descriptor])
            ready = select.select(readers, writers, [], wait)
            if not ready[0] and not ready[1]:
                raise TimeoutError()
            try:
                if data is None:
                    value = os.read(descriptor, min(remaining, 65536))
                    if not value:
                        raise EOFError()
                    output.append(value)
                    length = len(value)
                else:
                    length = os.write(descriptor, data[position : position + 65536])
            except BlockingIOError:
                continue
            remaining -= length
            position += length
        return b"".join(output)

    def frame(self, deadline, limit):
        size = struct.unpack("!I", self.transfer(self.process.stdout, deadline, size=4))[0]
        if size > limit:
            raise ValueError("invalid_frame")
        return self.transfer(self.process.stdout, deadline, size=size)

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.stop()
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "app.services.search.decoder_process",
                str(self.settings.image_max_pixels),
                str(self.settings.image_max_side),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        os.set_blocking(self.process.stdin.fileno(), False)
        os.set_blocking(self.process.stdout.fileno(), False)
        try:
            if json.loads(self.frame(monotonic() + 10, 1024)) != {"ready": True}:
                raise ValueError("decoder_not_ready")
        except Exception:
            self.stop()
            raise

    def decode(self, data):
        if not data or len(data) > self.settings.image_max_upload_mb * 1024**2:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "Ảnh vượt dung lượng hoặc rỗng")
        self.start()
        deadline = monotonic() + self.settings.image_decode_timeout_seconds
        try:
            self.transfer(self.process.stdin, deadline, data=struct.pack("!I", len(data)) + data)
            header = json.loads(self.frame(deadline, 1024))
            if "error" in header:
                code = header["error"]
                raise AppError(
                    415 if code == "UNSUPPORTED_MEDIA" else 422,
                    code,
                    "Ảnh không hợp lệ hoặc không được hỗ trợ",
                )
            width, height = header["width"], header["height"]
            if (
                type(width) is not int
                or type(height) is not int
                or min(width, height) < 1
                or max(width, height) > self.settings.image_max_side
                or width * height > self.settings.image_max_pixels
                or header["mode"] != "RGB"
            ):
                raise ValueError("invalid_dimensions")
            pixels = self.frame(deadline, self.settings.image_max_pixels * 3)
            if len(pixels) != width * height * 3:
                raise ValueError("invalid_pixels")
            return Image.frombytes("RGB", (width, height), pixels)
        except AppError:
            raise
        except TimeoutError:
            self.stop()
            raise AppError(422, "DECODE_TIMEOUT", "Decode ảnh hết thời gian") from None
        except Exception:
            self.stop()
            raise AppError(422, "CORRUPT_IMAGE", "Không decode được ảnh") from None
