#!/usr/bin/env python3
"""Sinh credentials local, không ghi đè môi trường đã có."""

import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import quote


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".env")
    parser.add_argument("--host", action="store_true", help="Dùng loopback URLs cho backend native")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    content = (root / ".env.example").read_text()
    password = secrets.token_urlsafe(32)
    host = "127.0.0.1" if args.host else "postgres"
    replacements = {
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": (
            f"postgresql+psycopg://image_search:{quote(password, safe='')}@{host}:5432/image_search"
        ),
        "API_TOKEN": secrets.token_urlsafe(36),
        "WRITE_API_TOKEN": secrets.token_urlsafe(36),
        "QDRANT_API_KEY": secrets.token_urlsafe(36),
        "MINIO_ACCESS_KEY": secrets.token_hex(10),
        "MINIO_SECRET_KEY": secrets.token_urlsafe(36),
    }
    if args.host:
        replacements.update(
            QDRANT_URL="http://127.0.0.1:6333",
            MINIO_ENDPOINT="127.0.0.1:9000",
            VITE_PROXY_TARGET="http://127.0.0.1:8000",
        )
    lines = []
    for line in content.splitlines():
        key = line.split("=", 1)[0]
        lines.append(f"{key}={replacements[key]}" if key in replacements else line)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.exit(1, f"Đã có {output.name}; giữ nguyên file, không ghi đè.\n")
    with os.fdopen(fd, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    print(f"Đã tạo {output.name} mode 0600; credentials không được in ra.")


if __name__ == "__main__":
    main()
