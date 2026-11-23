import io
import json
import stat
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import indexing
from app.cli.operations import validate_pending_migrations
from app.cli.worker import health
from tests.fixtures.synthetic import image_bytes

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture
def deployment_modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    from deployment import backup, common

    return common, backup


def configuration(tmp_path, common):
    path = tmp_path / ".env.deploy"
    common.initialize(path, "image-search-fixture", 8080, tmp_path / "models", tmp_path / "dataset")
    return path


def test_deploy_environment_is_private_distinct_and_never_overwritten(tmp_path, deployment_modules):
    common, _ = deployment_modules
    path = configuration(tmp_path, common)
    original = path.read_bytes()
    cfg = common.read_env(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cfg["APP_ENV"] == "production"
    assert cfg["API_TOKEN"] != cfg["WRITE_API_TOKEN"]
    assert cfg["SEARCH_ENABLED"] == cfg["RAG_ENABLED"] == cfg["AGENT_ENABLED"] == "false"
    with pytest.raises(ValueError, match="ENV_ALREADY_EXISTS"):
        configuration(tmp_path, common)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "changes",
    [
        {"DEPLOY_PROJECT_NAME": "ai-image-search"},
        {"QDRANT_URL": "http://serving-qdrant:6333"},
        {"DATABASE_URL": "postgresql+psycopg://private:private@serving:5432/image_search"},
        {"AGENT_ALLOW_FIXTURE_KNOWLEDGE": "true"},
        {"DEPLOY_BIND_ADDRESS": "0.0.0.0"},
    ],
)
def test_deploy_configuration_rejects_unsafe_targets(tmp_path, deployment_modules, changes):
    common, _ = deployment_modules
    cfg = common.read_env(configuration(tmp_path, common))
    with pytest.raises(ValueError):
        common.validate(cfg | changes)


def test_deploy_child_environment_and_redaction(tmp_path, deployment_modules, monkeypatch):
    common, _ = deployment_modules
    path = configuration(tmp_path, common)
    monkeypatch.setenv("GEMINI_API_KEY", "INHERITED_PRIVATE_PROVIDER_KEY")
    deployment = common.Deployment(path, tmp_path / "logs")
    assert "GEMINI_API_KEY" not in deployment.env
    token = deployment.cfg["API_TOKEN"]
    assert token not in deployment.scrub("Bearer " + token)
    with pytest.raises(ValueError, match="SERVING_OR_QA_ENV"):
        common.Deployment(tmp_path / ".env")


async def test_dataset_dry_run_validates_real_bytes_without_storage_or_model(
    settings, monkeypatch, tmp_path, capsys
):
    settings.dataset_root = str(tmp_path)
    (tmp_path / "image.png").write_bytes(image_bytes())
    monkeypatch.setattr(indexing, "Settings", lambda: settings)

    def forbidden(*args):
        raise AssertionError("Dry run must never initialize data services")

    monkeypatch.setattr(indexing, "Services", forbidden)
    args = SimpleNamespace(
        command="dataset",
        dry_run=True,
        input=str(tmp_path),
        name="fixture",
        version="v1",
        license="test-generated",
        rights_ref="fixture://phase12",
        index=None,
    )
    assert await indexing.execute(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["validated"] == 1 and result["accepted"] == 0
    assert result["results"][0]["sha256"] and result["dry_run"]
    (tmp_path / "broken.png").write_bytes(b"corrupt")
    assert await indexing.execute(args) == 1
    assert json.loads(capsys.readouterr().out)["failed"] == 1


async def test_dataset_manifest_duplicate_identifier_is_not_silently_overwritten(
    settings, monkeypatch, tmp_path
):
    settings.dataset_root = str(tmp_path)
    (tmp_path / "image.png").write_bytes(image_bytes())
    (tmp_path / "metadata.jsonl").write_text('{"filename":"image.png"}\n' * 2)
    monkeypatch.setattr(indexing, "Settings", lambda: settings)
    args = SimpleNamespace(command="dataset", dry_run=True, input=str(tmp_path))
    with pytest.raises(ValueError, match="DUPLICATE_MANIFEST"):
        await indexing.execute(args)


def test_bootstrap_guards_destructive_upgrade_but_allows_downgrade_definition(tmp_path):
    migration = tmp_path / "migration.py"
    migration.write_text(
        'def upgrade():\n    pass\ndef downgrade():\n    op.drop_table("images")\n'
    )
    validate_pending_migrations([migration])
    migration.write_text('def upgrade():\n    op.drop_table("images")\n')
    with pytest.raises(ValueError, match="MANUAL_REVIEW"):
        validate_pending_migrations([migration])


@pytest.mark.parametrize("unsafe", [False, True])
def test_backup_checksum_and_archive_path_guard(tmp_path, deployment_modules, unsafe):
    _, backup = deployment_modules
    for name in ["qdrant.tgz", "minio.tgz"]:
        with tarfile.open(tmp_path / name, "w:gz") as archive:
            item = tarfile.TarInfo("../escape" if unsafe else "data.json")
            item.size = 2
            archive.addfile(item, io.BytesIO(b"{}"))
    (tmp_path / "postgres.dump").write_bytes(b"fixture-only")
    manifest = {
        "format": "image-search-cold-backup-v1",
        "files": {name: {"sha256": backup.checksum(tmp_path / name)} for name in backup.FILES},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    if unsafe:
        with pytest.raises(ValueError, match="UNSAFE_BACKUP_ARCHIVE"):
            backup.validate_backup(tmp_path)
    else:
        assert backup.validate_backup(tmp_path) == manifest
        (tmp_path / "postgres.dump").write_bytes(b"tampered")
        with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
            backup.validate_backup(tmp_path)


def test_worker_health_distinguishes_idle_stale_and_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr("app.cli.worker.time.time", lambda: 100)
    path = tmp_path / "worker.json"
    for state, beat, expected in [
        ("idle", 99, True),
        ("running", 50, False),
        ("blocked", 99, False),
    ]:
        path.write_text(json.dumps({"state": state, "heartbeat_unix": beat}))
        assert health(path) is expected


def test_worker_health_command_does_not_import_data_services(monkeypatch):
    import builtins
    import runpy
    import sys

    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith(("sqlalchemy", "numpy", "qdrant_client", "minio", "torch")):
            raise AssertionError("A heartbeat check must not import the data or ML stack")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.delitem(sys.modules, "app.cli.worker", raising=False)
    monkeypatch.setattr(sys, "argv", ["worker", "--health"])
    with pytest.raises(SystemExit) as result:
        runpy.run_module("app.cli.worker", run_name="__main__")
    assert result.value.code in {0, 1}
