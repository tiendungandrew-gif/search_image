from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql import dialect

from app.core.access import Principal, current_principal
from app.services.search.suggestions import catalog_suggestions, prefix_query, search_suggestions


def row(title=None, caption=None, names=()):
    return SimpleNamespace(title=title, caption=caption, extra={
        "approved_csv_rows": [{"entity_name": name} for name in names]
    })


def test_prefix_query_normalizes_accents_and_discards_query_operators():
    assert prefix_query("ĐÀ NẴNG") == "da & nang:*"
    assert prefix_query("phở | ! <->") == "pho:*"
    assert prefix_query("! *") is None
    assert prefix_query("a") is None


def test_catalog_names_are_deduplicated_ranked_and_complete_all_words():
    rows = [row("Ảnh khách sạn", names=["Khách sạn Hà Nội"]),
            row("Khách sạn Hà Nội"), row("Khách sạn Hội An"), row("Nhà hàng Hà Nội")]
    results = catalog_suggestions(rows, "khach san ha")
    assert [item["text"] for item in results] == ["Khách sạn Hà Nội"]
    assert catalog_suggestions(rows, "resort") == []
    assert len(catalog_suggestions(rows, "khach", limit=1)) == 1


def test_untitled_images_use_real_captions_and_ignore_malformed_metadata():
    rows = [row(caption="Biển Đà Nẵng"), SimpleNamespace(title=None, caption=None, extra={
        "approved_csv_rows": [None, {"entity_name": 123}]
    })]
    assert catalog_suggestions(rows, "bien da")[0]["text"] == "Biển Đà Nẵng"


async def test_database_query_applies_acl_visibility_status_and_bound():
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.execute.return_value.all.return_value = []
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    services = SimpleNamespace(database=SimpleNamespace(sessions=lambda: context))
    scope = current_principal.set(Principal(uuid4(), "reader", "user", (), ("allowed",)))
    try:
        assert await search_suggestions(services, "khach san", source_dataset="other") == []
        statement = session.execute.call_args.args[0]
        sql = str(statement.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
        assert "'allowed'" in sql and "'other'" in sql
        assert "image_moderation.hidden IS true" in sql
        assert "images.status = 'available'" in sql and "images.deleted_at IS NULL" in sql
        assert "@@" in sql and "LIMIT 100" in sql
    finally:
        current_principal.reset(scope)
