from pathlib import Path

from alembic.config import Config
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from alembic import command
from app.db.base import Base
from app.db.models import foundation  # noqa: F401


def test_foundation_schema_has_required_relations_and_no_arbitrary_dimension():
    assert set(Base.metadata.tables) == {
        "images",
        "image_metadata",
        "embedding_models",
        "indexing_jobs",
        "search_indexes",
        "dataset_sources",
        "image_tags",
        "image_objects",
        "image_embeddings",
        "indexing_job_items",
        "job_item_attempts",
        "idempotency_records",
        "active_search_index",
    }
    jobs = Base.metadata.tables["indexing_jobs"]
    assert {fk.target_fullname for fk in jobs.foreign_keys} == {
        "dataset_sources.id",
        "search_indexes.id",
        "indexing_jobs.id",
    }
    assert Base.metadata.tables["embedding_models"].c.dimension.default is None
    assert Base.metadata.tables["embedding_models"].c.dimension.server_default is None
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert all(constraint.name for constraint in table.constraints)


def test_migration_offline_upgrade_and_rollback_compile(settings, monkeypatch, tmp_path):
    from app.core.config import get_settings

    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    get_settings.cache_clear()
    cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    upgrade = tmp_path / "upgrade.sql"
    with upgrade.open("w") as output:
        cfg.output_buffer = output
        command.upgrade(cfg, "head", sql=True)
    assert "CREATE TABLE images" in upgrade.read_text()
    rollback = tmp_path / "rollback.sql"
    with rollback.open("w") as output:
        cfg.output_buffer = output
        command.downgrade(cfg, "0001_foundation:base", sql=True)
    assert "DROP TABLE images" in rollback.read_text()
