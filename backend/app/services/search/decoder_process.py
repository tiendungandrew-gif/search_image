"""Private framed decoder process; reuse đúng decode function của Prompt04."""

import json
import math
import resource
import struct
import sys

from app.services.ingestion.decoder import decode


def read_exact(stream, size):
    chunks = []
    while size:
        chunk = stream.read(size)
        if not chunk:
            raise EOFError()
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


def write_frame(data):
    sys.stdout.buffer.write(struct.pack("!I", len(data)) + data)
    sys.stdout.buffer.flush()


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    max_pixels, max_side = int(sys.argv[1]), int(sys.argv[2])
    write_frame(b'{"ready":true}')
    while True:
        try:
            size = struct.unpack("!I", read_exact(sys.stdin.buffer, 4))[0]
            if not 1 <= size <= 20 * 1024**2:
                return 1
            raw = read_exact(sys.stdin.buffer, size)
        except EOFError:
            return 0
        # CPU limit là cumulative theo process; reset soft deadline cho từng ảnh.
        usage = resource.getrusage(resource.RUSAGE_SELF)
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (math.ceil(usage.ru_utime + usage.ru_stime) + 3, resource.RLIM_INFINITY),
        )
        try:
            image, _ = decode(raw, max_pixels, max_side)
            try:
                metadata = json.dumps(
                    {"width": image.width, "height": image.height, "mode": "RGB"}
                ).encode()
                pixels = image.tobytes()
            finally:
                image.close()
            write_frame(metadata)
            write_frame(pixels)
        except Exception as exc:
            allowed = {"UNSUPPORTED_MEDIA", "MULTIFRAME_IMAGE", "IMAGE_PIXEL_LIMIT"}
            code = (
                str(exc) if isinstance(exc, ValueError) and str(exc) in allowed else "CORRUPT_IMAGE"
            )
            write_frame(json.dumps({"error": code}).encode())


if __name__ == "__main__":
    raise SystemExit(main())
