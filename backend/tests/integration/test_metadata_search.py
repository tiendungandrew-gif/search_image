"""Actual PG full-text index, Qdrant payloads, MinIO and access scopes."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.db.models import Image, ImageMetadata
from app.repositories.image_repository import ImageRepository
from app.schemas.filters import Filters
from app.schemas.ingestion import ImageMetadataInput
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest
from app.services.indexing.worker import Worker
from tests.fixtures.synthetic import image_bytes
from tests.integration.test_access_control import accounts as accounts
from tests.integration.test_access_control import seed_search

pytestmark = pytest.mark.integration


async def test_accented_concepts_keep_meaning_and_prioritize_image_descriptions(
    accounts, qa_resources
):
    app, admin, _, _, _ = accounts
    runtime, ids = await seed_search(
        qa_resources, app,
        titles=["Quán ăn Hà Nội", "Phở " * 30 + "trên phố"],
        captions=["Bát phở bò với sợi phở và rau thơm", "Một biệt thự trên phố cổ"],
    )
    try:
        repo = ImageRepository(qa_resources.services)
        for query, expected in [("phở", ids[0]), ("phố", ids[1])]:
            hits = await repo.text_candidates(query, runtime.registry.index.id, Filters(), 10)
            assert [h.image_id for h in hits] == [expected]
        assert await repo.text_candidates("phổ", runtime.registry.index.id, Filters()) == []
        hits = await repo.text_candidates("pho", runtime.registry.index.id, Filters())
        assert {h.image_id for h in hits} == set(ids)
        # Many venue-name repetitions must not beat an actual depiction in the caption.
        hits = await repo.text_candidates("phở", runtime.registry.index.id, Filters(), 1)
        assert hits[0].image_id == ids[0]
    finally:
        await runtime.close()


async def test_names_original_accents_aliases_filters_and_hidden_scope(accounts, qa_resources):
    app, admin, _, _, _ = accounts
    name = "Phở 10 Lý Quốc Sư Hà Nội"
    runtime, ids = await seed_search(
        qa_resources,
        app,
        titles=[name, name],
        captions=["Bát phở nóng với thịt bò và rau thơm", "Một bát phở nóng"],
    )
    app.state.settings.guest_search_enabled = True
    initial_hits = await ImageRepository(qa_resources.services).text_candidates(
        "pho 10 ly quoc su", runtime.registry.index.id, Filters()
    )
    assert len(initial_hits) == 2 and all(hit.name_match for hit in initial_hits), initial_hits
    datasets = (await admin.get("/api/v1/admin/datasets")).json()["datasets"]
    public = next(d for d in datasets if d["key"] == "private_a")
    made_public = await admin.patch(
        f"/api/v1/admin/datasets/{public['id']}",
        json={"name": public["name"], "is_public": True},
    )
    assert made_public.status_code == 200, made_public.text
    origin = app.state.settings.cors_origins[0]
    try:
        async with AsyncClient(
            transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
        ) as guest:
            encode = runtime.encoder.encode_text

            def must_not_rewrite_or_encode(_):
                raise AssertionError("A known catalog name must not be accent-guessed or encoded")

            runtime.encoder.normalize_texts = must_not_rewrite_or_encode
            runtime.encoder.encode_text = must_not_rewrite_or_encode
            for query in ["pho 10 ly quoc su", "Phở 10 Lý Quốc Sư", "pho ly quoc su"]:
                response = await guest.post("/api/v1/search", json={"text": query})
                assert response.status_code == 200, response.text
                body = response.json()
                assert [r["image_id"] for r in body["results"]] == [str(ids[0])]
                assert body["effective_settings"]["route"] == "metadata_name"
                assert body["effective_settings"]["vector_calls"] == 0
                assert not any(w["code"] == "QUERY_ACCENTS_RESTORED" for w in body["warnings"])
            runtime.encoder.encode_text = encode
            del runtime.encoder.normalize_texts
            caption = await guest.post("/api/v1/search", json={"text": "bát phở nóng"})
            assert caption.status_code == 200, caption.text
            assert caption.json()["effective_settings"]["route"] == "metadata_phrase"
            assert caption.json()["effective_settings"]["vector_calls"] == 0
            for filters in [{"source_dataset": "private_b"}, {"tags_all": ["not-present"]}]:
                response = await guest.post(
                    "/api/v1/search", json={"text": name, "filters": filters}
                )
                assert response.status_code == 200, response.text
                assert response.json()["results"] == []
            async with qa_resources.services.database.sessions() as session, session.begin():
                await session.execute(
                    update(ImageMetadata)
                    .where(ImageMetadata.image_id == ids[0])
                    .values(
                        extra={
                            "approved_csv_rows": [{"entity_name": "Quán phở gia truyền Lý Quốc Sư"}]
                        }
                    )
                )
            alias = await guest.post(
                "/api/v1/search", json={"text": "quan pho gia truyen ly quoc su"}
            )
            assert alias.status_code == 200, alias.text
            assert [r["image_id"] for r in alias.json()["results"]] == [str(ids[0])]

            # Same public dataset/name in another ready index must never leak into this one.
            other, _ = await CollectionManager(qa_resources.services).register(
                runtime.encoder, "qa_" + qa_resources.token[:12] + "_other"
            )
            qa_resources.collections.add(other.collection_name)
            _, item = await ingest(
                qa_resources.services,
                image_bytes(9),
                ImageMetadataInput(
                    title=name,
                    source_dataset="private_a",
                    license="generated",
                    rights_ref="fixture://text",
                ),
                "other-index-name",
                other.id,
            )
            await Worker(qa_resources.services, runtime.encoder, other.id).run(once=True)
            assert (await verify_index(qa_resources.services, other.id, mark_ready=True))[
                "status"
            ] == "pass"
            response = await guest.post("/api/v1/search", json={"text": name})
            assert [r["image_id"] for r in response.json()["results"]] == [str(ids[0])]
            assert item["image_id"] not in str(response.json())

            hide = await admin.delete(f"/api/v1/admin/images/{ids[0]}")
            assert hide.status_code == 200, hide.text
            hidden = await guest.post("/api/v1/search", json={"text": name})
            assert hidden.status_code == 200, hidden.text
            assert hidden.json()["results"] == []
            restore = await admin.post(f"/api/v1/admin/images/{ids[0]}/restore")
            assert restore.status_code == 200, restore.text
            async with qa_resources.services.database.sessions() as session, session.begin():
                await session.execute(
                    update(Image).where(Image.id == ids[0]).values(metadata_revision=2)
                )
            stale = await guest.post("/api/v1/search", json={"text": name})
            assert stale.status_code == 200, stale.text
            assert stale.json()["results"] == []
    finally:
        await runtime.close()


async def test_pagination_stable_ranks_limits_and_access_scope(accounts, qa_resources):
    app, admin, user, _, uid = accounts
    name = "Phở 10 Lý Quốc Sư"
    runtime, ids = await seed_search(qa_resources, app, titles=[name, name])
    try:
        pages = []
        for page in [1, 2, 500]:
            response = await admin.post(
                "/api/v1/search", json={"text": name, "top_k": 1, "page": page}
            )
            assert response.status_code == 200, response.text
            pages.append(response.json())
        assert pages[0]["pagination"] == {
            "page": 1, "page_size": 1, "total_results": 2,
            "total_pages": 2, "result_limit": 500,
        }
        assert pages[1]["results"][0]["rank"] == 2
        returned = {pages[0]["results"][0]["image_id"], pages[1]["results"][0]["image_id"]}
        assert returned == set(map(str, ids))
        assert pages[2]["pagination"]["page"] == 2
        assert pages[2]["results"] == pages[1]["results"]
        # Paging does not reveal inaccessible records, even in counts.
        hidden = await user.post("/api/v1/search", json={"text": name, "page": 1})
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["pagination"]["total_results"] == 0
        assert hidden.json()["results"] == []
        for page in [0, 501, -1]:
            invalid = await admin.post("/api/v1/search", json={"text": name, "page": page})
            assert invalid.status_code == 422
        too_large = await admin.post(
            "/api/v1/search", json={"text": name, "top_k": 51, "page": 1}
        )
        assert too_large.status_code == 422
        missing = await admin.post(
            "/api/v1/search", json={"text": name, "page": 1, "filters": {"tags_all": ["absent"]}}
        )
        assert missing.status_code == 200
        assert missing.json()["pagination"]["total_pages"] == 0
        assert missing.json()["results"] == []
    finally:
        await runtime.close()


async def test_catalog_suggestions_follow_permissions_filters_and_visibility(
    accounts, qa_resources
):
    app, admin, reader, _, _ = accounts
    runtime, ids = await seed_search(
        qa_resources, app,
        titles=["Khách sạn Hà Nội", "Khách sạn Đà Nẵng"],
        captions=["Phòng ngủ có ban công", "Hồ bơi ngoài trời"],
    )
    try:
        async def suggest(client, **params):
            response = await client.get("/api/v1/search/suggestions", params=params)
            assert response.status_code == 200, response.text
            assert "no-store" in response.headers["cache-control"]
            return [item["text"] for item in response.json()["suggestions"]]

        assert await suggest(admin, q="khach san") == ["Khách sạn Hà Nội", "Khách sạn Đà Nẵng"]
        assert await suggest(reader, q="khach san") == []
        assert await suggest(admin, q="khach san", source_dataset="private_a") == [
            "Khách sạn Hà Nội"
        ]
        assert await suggest(admin, q="nonexistent catalog name") == []
        async with qa_resources.services.database.sessions() as session, session.begin():
            await session.execute(
                update(ImageMetadata).where(ImageMetadata.image_id == ids[0]).values(
                    extra={"approved_csv_rows": [{"entity_name": "Khách sạn Hoàn Kiếm"}]}
                )
            )
        assert await suggest(admin, q="khach san hoan") == ["Khách sạn Hoàn Kiếm"]
        assert (await admin.delete(f"/api/v1/admin/images/{ids[0]}")).status_code == 200
        assert await suggest(admin, q="khach san ha") == []
        assert (await admin.get("/api/v1/search/suggestions", params={"q": "x"})).status_code == 422
    finally:
        await runtime.close()


@pytest.mark.parametrize("query", [
    "phở gà", "pho ga", "PHỞ GÀ", "phở ga",
    "tìm ảnh phở gà", "tim anh pho ga", "tìm kiếm hình ảnh phở gà",
    "show me pictures of phở gà",
])
async def test_compound_dish_does_not_expand_into_scattered_terms_or_visual_neighbors(
    accounts, qa_resources, query
):
    app, admin, _, _, _ = accounts
    runtime, ids = await seed_search(
        qa_resources, app,
        titles=["Quán phở Hà Nội", "Quán phở bò"],
        captions=["Tô phở gà với nước dùng trong và rau thơm", "Bát phở bò ăn với trứng gà"],
    )
    try:
        def must_not_encode(_):
            raise AssertionError("An exact phrase must not be padded with visual neighbors")

        encode = runtime.encoder.encode_text
        runtime.encoder.encode_text = must_not_encode
        runtime.encoder.normalize_texts = must_not_encode
        result = await admin.post("/api/v1/search", json={"text": query, "top_k": 10})
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["query_analysis"]["original_query"] == query
        assert [item["image_id"] for item in body["results"]] == [str(ids[0])]
        assert body["effective_settings"]["route"] == "metadata_phrase"
        assert body["effective_settings"]["vector_calls"] == 0
        runtime.encoder.encode_text = encode
        del runtime.encoder.normalize_texts
        filtered = await admin.post("/api/v1/search", json={
            "text": query, "filters": {"source_dataset": "private_b"}
        })
        # No eligible phrase in this scope: semantic fallback must still respect image ACLs.
        assert str(ids[0]) not in filtered.text
    finally:
        await runtime.close()


@pytest.mark.parametrize("query", ["bun ga", "tìm ảnh bún gà"])
async def test_missing_food_phrase_never_falls_back_to_live_chicken_or_other_dishes(
    accounts, qa_resources, query
):
    app, admin, _, _, _ = accounts
    runtime, _ = await seed_search(
        qa_resources, app,
        titles=["Quán bún gà Hà Nội", "Bún thang"],
        captions=["Một con gà đứng trước quán bún", "Bát bún thang có thịt gà và trứng"],
    )
    try:
        def must_not_encode(_):
            raise AssertionError("No exact dish must not trigger semantic animal fallback")

        runtime.encoder.encode_text = must_not_encode
        runtime.encoder.normalize_texts = must_not_encode
        response = await admin.post("/api/v1/search", json={
            "text": query, "top_k": 10, "page": 1,
        })
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["results"] == []
        assert body["pagination"]["total_results"] == 0
        assert body["effective_settings"]["route"] == "metadata_food_phrase"
        assert body["effective_settings"]["vector_calls"] == 0
        assert body["query_analysis"]["original_query"] == query
        assert any(w["code"] == "FOOD_PHRASE_NOT_FOUND" for w in body["warnings"])
    finally:
        await runtime.close()


async def test_bun_ga_exact_matches_exclude_live_animals_and_respect_scope(accounts, qa_resources):
    app, admin, reader, _, _ = accounts
    runtime, ids = await seed_search(
        qa_resources, app,
        titles=["Món ăn", "Quán bún gà"],
        captions=["Tô bún gà nóng với rau thơm", "Đàn gà đứng trước cửa quán bún"],
    )
    try:
        def must_not_encode(_):
            raise AssertionError("Dish search must not add semantic neighbors")

        runtime.encoder.encode_text = must_not_encode
        runtime.encoder.normalize_texts = must_not_encode
        for query in ["bun ga", "bún gà", "BÚN GÀ?", "tim anh bun ga"]:
            result = await admin.post("/api/v1/search", json={"text": query})
            assert result.status_code == 200, result.text
            body = result.json()
            assert [r["image_id"] for r in body["results"]] == [str(ids[0])]
            assert body["effective_settings"]["food_phrase_required"] is True
        for client, filters in [(reader, {}), (admin, {"source_dataset": "private_b"})]:
            result = await client.post(
                "/api/v1/search", json={"text": "bun ga", "filters": filters}
            )
            assert result.status_code == 200, result.text
            assert result.json()["results"] == []
    finally:
        await runtime.close()
