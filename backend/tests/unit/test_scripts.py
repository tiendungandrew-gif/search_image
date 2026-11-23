import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

PROJECT = Path(__file__).resolve().parents[3]


def test_environment_aliases_preserve_explicit_files_and_external_targets(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    from environment_paths import resolve_env_file

    canonical = tmp_path / "config/environments/deployment.env"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("VALUE=private\n")
    legacy = tmp_path / ".env.phase12"
    assert resolve_env_file(legacy, root=tmp_path) == canonical
    # An explicit file takes precedence, and an external missing file never picks local credentials.
    legacy.write_text("VALUE=explicit\n")
    assert resolve_env_file(legacy, root=tmp_path) == legacy
    external = tmp_path / "external/.env.phase12"
    assert resolve_env_file(external, root=tmp_path) == external


@pytest.mark.parametrize("name", [".env.native", "config/environments/archive/native.env"])
def test_archived_native_environment_remains_protected_from_deployment(tmp_path, monkeypatch, name):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    from environment_paths import is_protected_environment

    assert is_protected_environment(tmp_path / name, root=tmp_path)


def test_generated_secrets_are_private_and_existing_env_is_never_overwritten(tmp_path):
    output = tmp_path / ".env"
    command = [sys.executable, str(PROJECT / "scripts/init_env.py"), "--output", str(output)]
    first = subprocess.run(command, capture_output=True, text=True, check=True)
    original = output.read_bytes()
    values = dotenv_values(output)
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    for key in (
        "POSTGRES_PASSWORD",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "API_TOKEN",
        "QDRANT_API_KEY",
    ):
        assert values[key] and values[key] not in first.stdout + first.stderr
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert output.read_bytes() == original


def test_local_env_helper_overrides_only_child_without_shell_evaluation(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('DEBUG=false\nFOUNDATION_TEST_VALUE="literal $(not-a-command)"\n')
    previous = os.environ.get("DEBUG")
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/run_local.py"),
            "--env-file",
            str(env_file),
            "--",
            sys.executable,
            "-c",
            "import os; assert os.environ['DEBUG']=='false'; "
            "assert os.environ['FOUNDATION_TEST_VALUE']=='literal $(not-a-command)'",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.environ.get("DEBUG") == previous
