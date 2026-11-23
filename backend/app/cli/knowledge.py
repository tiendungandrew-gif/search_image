"""Nhập tri thức có nguồn: dry-run mặc định, --apply để ghi transaction; không là Agent tool."""

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import Settings
from app.core.container import Services
from app.repositories.knowledge_import import import_knowledge


async def execute(args):
    raw = await asyncio.to_thread(Path(args.input).read_bytes)
    if len(raw) > 1024 * 1024:
        raise ValueError("KNOWLEDGE_FILE_LIMIT")
    services = Services(Settings())
    try:
        result = await import_knowledge(services, json.loads(raw), args.apply)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
