import asyncio
import math
import threading
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.evaluation.metrics import latency_summary, nearest_rank, retrieval_metrics
from app.schemas.search import Filters, SearchRequest, normalize_text
from app.services.search.ranking import matches_metadata, rank_unique
from app.services.search.runtime import SearchRuntime
from app.services.search.vector_retriever import Candidate, payload_filter


@pytest.mark.parametrize("value", ["", "   ", "\x00hello"])
def test_invalid_text(value):
    with pytest.raises(ValueError):
        normalize_text(value)


def test_unicode_whitespace_and_aliases():
    assert normalize_text(" cafe\u0301\n  street ") == "café street"
    assert SearchRequest(query="  coffee ", search_mode="semantic").text == "coffee"
    with pytest.raises(ValidationError):
        SearchRequest(query="a", text="b")


@pytest.mark.parametrize("value", [0, 101, True, "10"])
def test_topk_bounds_and_type(value):
    with pytest.raises(ValidationError):
        SearchRequest(text="coffee", top_k=value)


def test_filters_and_invalid_options():
    with pytest.raises(ValidationError):
        Filters(min_width=500, max_width=20)
    with pytest.raises(ValidationError):
        SearchRequest(text="coffee", collection="arbitrary")
    with pytest.raises(ValidationError):
        SearchRequest(text="a" * 2001)
    with pytest.raises(ValidationError):
        SearchRequest(text="a", top_k=10, candidate_count=5)
    assert Filters(tags_any=[" CAT ", "cat"]).tags_any == ["cat"]
    assert payload_filter(Filters(tags_all=["cat"]), UUID(int=1)).must_not


def test_rank_dedup_ties_and_authoritative_filter():
    first, second = UUID(int=1), UUID(int=2)
    # Isolated retrieval fixture; không là production vectors/results.
    values = [Candidate(second, 0.8, {}), Candidate(first, 0.8, {}), Candidate(first, 0.7, {})]
    assert [c.image_id for c in rank_unique(values)] == [first, second]
    image = SimpleNamespace(width=600, height=400, media_type="image/png")
    meta = SimpleNamespace(source_dataset="sample", city=None, captured_at=None)
    assert matches_metadata(Filters(min_width=500), image, meta, [])
    assert not matches_metadata(Filters(tags_all=["cat"]), image, meta, [])
    assert rank_unique([]) == []


def test_metric_formulas_explicit_numeric_fixtures():
    metrics = retrieval_metrics(["b", "a", "a", "c"], {"a": 3, "c": 1, "z": 1})
    assert metrics["recall@1"] == 0 and metrics["recall@5"] == 2 / 3
    assert metrics["recall@10"] == 2 / 3 and metrics["precision@10"] == 0.2
    assert metrics["mrr@10"] == 0.5
    dcg = 7 / math.log2(3) + 1 / math.log2(5)
    ideal = 7 + 1 / math.log2(3) + 1 / math.log2(4)
    assert metrics["ndcg@10"] == pytest.approx(dcg / ideal)
    assert all(value is None for value in retrieval_metrics([], {}).values())
    assert nearest_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == 9
    assert latency_summary([10, 20]) == {"p50_ms": 10, "p90_ms": 20, "p95_ms": 20}


async def test_cancelled_inference_keeps_capacity_until_thread_finishes(settings):
    runtime = SearchRuntime(SimpleNamespace(settings=settings))
    started = threading.Event()
    release = threading.Event()

    def blocking():
        started.set()
        release.wait(2)
        return 1

    task = asyncio.create_task(runtime.compute(blocking))
    await asyncio.to_thread(started.wait, 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runtime.slot.locked()
    with pytest.raises(AppError) as error:
        await runtime.compute(lambda: 2)
    assert error.value.code == "INFERENCE_BUSY"
    release.set()
    await runtime.close()


@pytest.mark.parametrize(
    "body",
    [
        {"text": ""},
        {"text": "coffee", "top_k": 0},
        {"text": "coffee", "collection": "bad"},
        {"text": "coffee", "query": "cat"},
    ],
)
async def test_api_validation_is_safe(app, auth_headers, body):
    from httpx import ASGITransport, AsyncClient

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/search", headers=auth_headers, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["request_id"]


async def test_query_decoder_preserves_pixels_and_restarts(settings):
    from io import BytesIO

    from PIL import Image

    from app.services.ingestion.validator import prepared_image
    from app.services.search.query_decoder import QueryDecoder

    decoder = QueryDecoder(settings)
    try:
        for mode, format in [("RGBA", "PNG"), ("RGB", "JPEG"), ("RGB", "WEBP")]:
            output = BytesIO()
            Image.new(mode, (12, 8)).save(output, format=format)
            raw = output.getvalue()
            original = await asyncio.to_thread(prepared_image, raw, settings)
            actual = await asyncio.to_thread(decoder.decode, raw)
            assert (
                actual.mode == original.mode
                and actual.size == original.size
                and actual.tobytes() == original.tobytes()
            )
            actual.close()
            original.close()
        pid = decoder.process.pid
        with pytest.raises(AppError):
            await asyncio.to_thread(decoder.decode, b"corrupt")
        assert decoder.process.pid == pid
        decoder.process.kill()
        decoder.process.wait()
        actual = await asyncio.to_thread(decoder.decode, raw)
        assert decoder.process.pid != pid
        actual.close()
    finally:
        await asyncio.to_thread(decoder.stop)
