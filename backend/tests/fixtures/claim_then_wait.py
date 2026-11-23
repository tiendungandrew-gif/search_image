"""Disposable worker process used only by the interruption integration test."""

import asyncio
import json
import os
from uuid import UUID

from app.core.config import Settings
from app.core.container import Services
from app.services.indexing.worker import Worker
from tests.fixtures.synthetic import SyntheticEncoder


async def main():
    services = Services(Settings())
    try:
        worker = Worker(services, SyntheticEncoder(), UUID(os.environ["QA_TEST_INDEX_ID"]))
        await worker.configuration()
        claimed = await worker.claim()
        print(json.dumps({"claimed": len(claimed)}), flush=True)
        await asyncio.Event().wait()
    finally:
        await services.close()


if __name__ == "__main__":
    asyncio.run(main())
