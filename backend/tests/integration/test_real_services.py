import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.services.health import Services


@asynccontextmanager
async def async_client(app):
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


"Opt-in tests dùng dịch vụ thật; không mock hoặc SQLite thay PostgreSQL."
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1", reason="Cần RUN_INTEGRATION=1 và ba data services thật"
    ),
]


async def test_real_dependency_connections():
    settings = Settings()
    services = Services(settings)
    try:
        await services.initialize()
        assert await services.readiness() == {
            "postgresql": "healthy",
            "qdrant": "healthy",
            "minio": "healthy",
        }
        assert await services.qdrant.client.info()
    finally:
        await services.close()


async def test_real_backend_readiness():
    settings = Settings()
    async with async_client(create_app(settings)) as client:
        response = await client.get(
            "/api/v1/health/ready",
            headers={"Authorization": f"Bearer {settings.api_token.get_secret_value()}"},
        )
        assert response.status_code == 200, response.json()
        assert (await client.get("/api/v1/health/live")).status_code == 200


def test_real_migration_upgrade_schema_match_and_rollback(monkeypatch):
    settings = Settings()
    from sqlalchemy.engine import make_url

    app_url = make_url(settings.database_url.get_secret_value())
    database_name = "foundation_test_" + uuid4().hex
    admin_url = app_url.set(database="postgres", drivername="postgresql")
    admin = psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True)
    test_url = app_url.set(database=database_name)
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    engine = None
    try:
        monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
        from app.core.config import get_settings

        get_settings.cache_clear()
        cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        command.upgrade(cfg, "head")
        engine = create_engine(test_url, hide_parameters=True)
        with engine.connect() as conn:
            assert set(Base.metadata.tables).issubset(inspect(conn).get_table_names())
            assert (
                compare_metadata(
                    MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata
                )
                == []
            )
        command.downgrade(cfg, "base")
        with engine.connect() as conn:
            assert "images" not in inspect(conn).get_table_names()
    finally:
        if engine:
            engine.dispose()
        admin.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
        )
        admin.close()
        get_settings.cache_clear()
