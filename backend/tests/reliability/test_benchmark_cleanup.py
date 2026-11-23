import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.evaluation.benchmark import run_benchmark
from app.evaluation.contracts import BenchmarkConfig


async def test_benchmark_failure_stops_its_resource_monitor(monkeypatch):
    original = httpx.AsyncClient

    async def respond(request):
        if request.url.path.endswith("/health"):
            await asyncio.sleep(0)
            return httpx.Response(503, json={"error": {"code": "NOT_READY"}})
        await asyncio.Event().wait()

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)),
    )
    config = BenchmarkConfig(requests=1, warmup=0, concurrency=1, sample_resources=True)
    case = SimpleNamespace(
        query_type="single_intent", query_id="fixture", request={"text": "fixture"}
    )
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await run_benchmark(config, [case], {"images": []}, "http://mock", "mock-only-token")
        await asyncio.sleep(0)
        pending = [
            task
            for task in asyncio.all_tasks()
            if not task.done()
            and task.get_coro().__qualname__.endswith("run_benchmark.<locals>.monitor")
        ]
        assert not pending
    finally:
        # Bound a failing regression test's own cleanup, without hiding its failure.
        pending = [
            task
            for task in asyncio.all_tasks()
            if not task.done()
            and task.get_coro().__qualname__.endswith("run_benchmark.<locals>.monitor")
        ]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
