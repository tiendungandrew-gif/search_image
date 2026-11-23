import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

import psycopg
import pytest
from alembic.config import Config
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import make_url

from alembic import command
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.db.models import SearchIndex
from app.services.indexing.collection_manager import CollectionManager


@dataclass
class QAResources:
    settings: Settings
    services: Services
    token: str
    collections: set[str] = field(default_factory=set)

    async def index(self, encoder):
        index, model = await CollectionManager(self.services).register(
            encoder, "qa_" + self.token[:12]
        )
        self.collections.add(index.collection_name)
        self.settings.ingestion_index_id = str(index.id)
        return index, model


@pytest.fixture
async def qa_resources(monkeypatch):
    original = Settings()
    token = uuid4().hex
    name = "image_search_qa_" + token
    url = make_url(original.database_url.get_secret_value())
    admin = await psycopg.AsyncConnection.connect(
        url.set(database="postgres", drivername="postgresql").render_as_string(hide_password=False),
        autocommit=True,
    )
    await admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    test_url = url.set(database=name).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", test_url)
    get_settings.cache_clear()
    cfg = original.model_copy(
        update={
            "database_url": SecretStr(test_url),
            "minio_bucket": "qa-suite-" + token,
            "minio_auto_create_bucket": True,
            "search_enabled": False,
            "rag_enabled": False,
            "agent_enabled": False,
            "dependency_timeout_seconds": 5,
        }
    )
    services = Services(cfg)
    resources = QAResources(cfg, services, token)
    try:
        await asyncio.to_thread(command.upgrade, Config("backend/alembic.ini"), "head")
        await services.initialize()
        yield resources
    finally:
        try:
            async with services.database.sessions() as session:
                resources.collections.update(
                    (await session.scalars(select(SearchIndex.collection_name))).all()
                )
            for collection in resources.collections:
                if not collection.startswith("images_qa_"):
                    raise RuntimeError("Test cleanup refuses a non-QA collection")
                await services.qdrant.client.delete_collection(collection)

            def remove_objects():
                bucket = cfg.minio_bucket
                for obj in services.minio.client.list_objects(bucket, recursive=True):
                    services.minio.client.remove_object(bucket, obj.object_name)
                if services.minio.client.bucket_exists(bucket):
                    services.minio.client.remove_bucket(bucket)

            await asyncio.to_thread(remove_objects)
        finally:
            await services.close()
            await admin.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
            await admin.close()
            get_settings.cache_clear()
