"""Disposable real empty stack for Phase10 browser acceptance. Never clears live data."""

import asyncio
import json
import tempfile
from pathlib import Path
from uuid import uuid4

import psycopg
import uvicorn
from app.core.config import Settings
from app.core.container import Services
from app.db.base import Base
from app.main import create_app
from psycopg import sql
from qdrant_client.models import Distance, VectorParams
from sqlalchemy.engine import make_url


async def run():
    original = Settings()
    identity = "phase10_empty_" + uuid4().hex
    app_url = make_url(original.database_url.get_secret_value())
    admin = await psycopg.AsyncConnection.connect(
        app_url.set(database="postgres", drivername="postgresql").render_as_string(
            hide_password=False
        ),
        autocommit=True,
    )
    await admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(identity)))
    with tempfile.TemporaryDirectory() as directory:
        settings = Settings(
            database_url=app_url.set(database=identity).render_as_string(hide_password=False),
            minio_bucket=identity.replace("_", "-"),
            search_enabled=False,
            rag_enabled=False,
            agent_enabled=False,
            agent_llm_planning_enabled=False,
            minio_auto_create_bucket=True,
            evaluation_results_dir=directory,
        )
        services = Services(settings)
        collection = identity
        try:
            async with services.database.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            await services.initialize()
            await services.qdrant.client.create_collection(
                collection, vectors_config=VectorParams(size=512, distance=Distance.COSINE)
            )
            objects = await asyncio.to_thread(
                lambda: list(services.minio.client.list_objects(settings.minio_bucket))
            )
            points = (await services.qdrant.client.get_collection(collection)).points_count
            assert not objects and points == 0
            await asyncio.to_thread(
                Path("/tmp/phase10_empty_resources.json").write_text,
                json.dumps(
                    {
                        "fixture": "isolated_real_services",
                        "database": identity,
                        "collection": collection,
                        "bucket": settings.minio_bucket,
                        "vectors": points,
                        "objects": len(objects),
                    }
                ),
            )
            server = uvicorn.Server(
                uvicorn.Config(create_app(settings), host="0.0.0.0", port=8001, log_level="warning")
            )
            await server.serve()
        finally:
            await services.qdrant.client.delete_collection(collection)
            await asyncio.to_thread(services.minio.client.remove_bucket, settings.minio_bucket)
            await services.close()
            await admin.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(identity))
            )
            await admin.close()


if __name__ == "__main__":
    asyncio.run(run())
