import pytest
from pydantic import SecretStr

from app.repositories.knowledge_import import fixture_database_allowed


@pytest.mark.parametrize(
    "host,database,flag,allowed",
    [
        ("qa-postgres", "image_search_qa", "1", True),
        ("qa-postgres", "image_search_qa_abc", "1", True),
        ("qa-postgres", "image_search", "1", False),
        ("localhost", "image_search_qa", "1", False),
        ("qa-postgres", "image_search_qa", "0", False),
        ("localhost", "agent_test_owned", "0", True),
    ],
)
def test_fixture_import_requires_owned_database_namespace(
    settings, monkeypatch, host, database, flag, allowed
):
    monkeypatch.setenv("QA_ISOLATED", flag)
    cfg = settings.model_copy(
        update={
            "agent_allow_fixture_knowledge": True,
            "database_url": SecretStr(
                f"postgresql+psycopg://fixture:unused@{host}:5432/{database}"
            ),
        }
    )
    assert fixture_database_allowed(cfg) is allowed
    assert not fixture_database_allowed(cfg.model_copy(update={"app_env": "production"}))
    assert not fixture_database_allowed(
        cfg.model_copy(update={"agent_allow_fixture_knowledge": False})
    )
