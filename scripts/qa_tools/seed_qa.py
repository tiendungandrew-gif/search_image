"""Seed only the isolated QA stack with generated images and real cached CLIP."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from app.core.config import Settings
from app.core.container import Services
from app.db.models import Image, ImageMetadata
from app.db.models.indexing import ActiveSearchIndex
from app.repositories.knowledge_import import import_knowledge
from app.schemas.ingestion import ImageMetadataInput
from app.services.embeddings.clip_encoder import ClipEncoder
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, now
from app.services.indexing.worker import Worker
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from tests.fixtures.synthetic import image_bytes


def assert_qa(settings):
    url = make_url(settings.database_url.get_secret_value())
    if (
        os.getenv("QA_ISOLATED") != "1"
        or settings.app_env != "test"
        or url.host != "qa-postgres"
        or not url.database.startswith("image_search_qa")
    ):
        raise RuntimeError("QA seed refuses a serving database")


async def seed(services):
    cfg = services.settings
    assert_qa(cfg)
    async with services.database.sessions() as session:
        before = await session.scalar(select(func.count()).select_from(Image))
    encoder = await asyncio.to_thread(ClipEncoder, cfg)
    namespace = hashlib.sha256(
        make_url(cfg.database_url.get_secret_value()).database.encode()
    ).hexdigest()[:12]
    index, model = await CollectionManager(services).register(encoder, "qa_clip_" + namespace)
    cfg.ingestion_index_id = str(index.id)
    ids = []
    for number in range(6):
        media = ["PNG", "JPEG", "WEBP"][number % 3]
        _, receipt = await ingest(
            services,
            image_bytes(number, media),
            ImageMetadataInput(
                title=f"QA synthetic fixture {number + 1}",
                caption="Generated software fixture with colored geometric shapes.",
                source_dataset="qa_synthetic_v1",
                tags=["qa", "synthetic", "shape"],
                license="generated-test-fixture",
                rights_ref="fixture://phase11/generated",
            ),
            f"qa-seed-v1-{number}",
            index.id,
        )
        ids.append(receipt["image_id"])
    async with services.database.sessions() as session, session.begin():
        for identity in ids:
            metadata = await session.get(ImageMetadata, UUID(identity))
            metadata.city = "Fixture City Beta"
    await Worker(services, encoder, index.id).run(once=True)
    report = await verify_index(services, index.id, mark_ready=True)
    assert report["status"] == "pass" and report["exact_vector_count"] == 6
    async with services.database.sessions() as session, session.begin():
        pointer = await session.get(ActiveSearchIndex, "default", with_for_update=True)
        if pointer is None:
            session.add(
                ActiveSearchIndex(
                    corpus_key="default", index_id=index.id, generation=1, activated_at=now()
                )
            )
        elif pointer.index_id != index.id:
            raise RuntimeError("QA seed refuses to replace an unrelated active index")
    payload = json.loads(
        await asyncio.to_thread(
            Path("evaluation/agent/fixtures/fictional_knowledge.json").read_text
        )
    )
    payload["image_entities"] = [
        {
            "image_id": ids[0],
            "entity_id": payload["entities"][2]["id"],
            "relation": "depicts",
            "source_ref": "fixture://phase11/association",
            "verified": True,
        }
    ]
    await import_knowledge(services, payload, apply=True)
    return {
        "classification": "REAL_CLIP_SYNTHETIC_IMAGES_FICTIONAL_KNOWLEDGE",
        "images_before": before,
        "image_ids": ids,
        "index_id": str(index.id),
        "model_id": str(model.id),
        "manifest_sha256": model.manifest_sha256,
        "dimension": model.dimension,
        "real_world_relevance": None,
    }


async def main():
    services = Services(Settings())
    try:
        await services.initialize()
        result = await seed(services)
        folder = Path("/qa-fixtures")
        await asyncio.to_thread((folder / "query.png").write_bytes, image_bytes())
        await asyncio.to_thread(
            (folder / "manifest.json").write_text, json.dumps(result, indent=2) + "\n"
        )
        print(json.dumps(result))
    finally:
        await services.close()


if __name__ == "__main__":
    asyncio.run(main())
