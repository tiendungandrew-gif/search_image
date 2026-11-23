"""Activate validated index; không tự đổi model hoặc recreate collection."""

import argparse
import asyncio
import json
from uuid import UUID

from app.core.config import Settings
from app.core.container import Services
from app.db.models import SearchIndex
from app.db.models.indexing import ActiveSearchIndex
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import lock, now
from app.services.search.runtime import SearchRuntime


async def activate(index_id):
    services = Services(Settings())
    runtime = SearchRuntime(services)
    try:
        report = await verify_index(services, index_id)
        if report["status"] != "pass":
            raise ValueError("INDEX_NOT_VALIDATED")
        await runtime.initialize(index_id)
        async with services.database.sessions() as session, session.begin():
            await lock(session, "active-search:default")
            index = await session.get(SearchIndex, index_id, with_for_update=True)
            if index.status != "ready" or index.model_id != runtime.registry.model.id:
                raise ValueError("INDEX_CHANGED_DURING_ACTIVATION")
            pointer = await session.get(ActiveSearchIndex, "default", with_for_update=True)
            if pointer is None:
                pointer = ActiveSearchIndex(
                    corpus_key="default", index_id=index_id, generation=1, activated_at=now()
                )
                session.add(pointer)
            elif pointer.index_id != index_id:
                pointer.index_id = index_id
                pointer.generation += 1
                pointer.activated_at = now()
            generation = pointer.generation
        print(
            json.dumps(
                {
                    "status": "pass",
                    "index_id": str(index_id),
                    "model_id": str(runtime.registry.model.id),
                    "manifest_sha256": runtime.encoder.manifest_sha256,
                    "generation": generation,
                    "model_initialization_ms": runtime.initialization_ms,
                    "verified_images": report["verified_images"],
                }
            )
        )
    finally:
        await runtime.close()
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", type=UUID, required=True)
    asyncio.run(activate(parser.parse_args().activate))


if __name__ == "__main__":
    main()
