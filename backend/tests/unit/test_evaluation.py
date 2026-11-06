"""Numeric/contract fixtures only; human_verified fixtures never become real qrels."""

import asyncio
import math
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from app.evaluation.analysis import analyze_optimization
from app.evaluation.benchmark import run_benchmark
from app.evaluation.contracts import BenchmarkConfig, QueryCase
from app.evaluation.dataset import query_digest, read_queries, validate_labels
from app.evaluation.metrics import retrieval_metrics
from app.evaluation.quality import aggregate
from app.evaluation.statistics import describe, latency_bootstrap, paired_bootstrap
from app.evaluation.tracking import Experiment, digest


def test_metrics_numeric_threshold_discount_and_duplicate_positions():
    result = retrieval_metrics(
        ["b", "a", "a", "c"], {"a": 2, "b": 0, "c": 1, "z": 2}, relevant_grade=2, strict_labels=True
    )
    assert result["recall@1"] == 0 and result["recall@5"] == 0.5
    assert result["precision@5"] == 0.2 and result["precision@10"] == 0.1
    assert result["hit@1"] == 0 and result["hit@5"] == 1 and result["mrr@10"] == 0.5
    assert result["dcg@10"] == pytest.approx(3 / math.log2(3) + 1 / math.log2(5))
    assert result["idcg@10"] == pytest.approx(3 + 3 / math.log2(3) + 1 / math.log2(4))
    partial = retrieval_metrics(["a"], {"a": 1}, relevant_grade=2)
    assert partial["recall@10"] is None and partial["ndcg@10"] == 1
    assert all(v is None for v in retrieval_metrics([], {}).values())


@pytest.mark.parametrize("grades", [{"a": -1}, {"a": True}, {"a": 1.0}, {"a": float("nan")}])
def test_invalid_grades(grades):
    with pytest.raises(ValueError):
        retrieval_metrics(["a"], grades)


def test_unjudged_results_not_silently_negative():
    with pytest.raises(ValueError):
        retrieval_metrics(["unknown"], {"a": 2}, strict_labels=True)


def test_latency_and_seeded_paired_uncertainty():
    values = describe([1, 2, 3, 4])
    assert values["mean_ms"] == 2.5 and values["p50_ms"] == 2 and values["p90_ms"] == 4
    assert values["stddev_ms"] == pytest.approx(math.sqrt(1.25))
    result = paired_bootstrap({"a": 1, "b": 2}, {"a": 2, "b": 3}, repetitions=100)
    assert result["mean_paired_delta"] == 1 and result["ci95_low"] == 1 and result["ci95_high"] == 1
    assert result == paired_bootstrap({"a": 1, "b": 2}, {"a": 2, "b": 3}, repetitions=100)
    assert paired_bootstrap({"a": 1}, {"a": 2})["status"] == "insufficient_independent_groups"
    with pytest.raises(ValueError):
        paired_bootstrap({"a": 1}, {"b": 2})
    assert latency_bootstrap([10] * 100)["p90_ci95_low_ms"] == 10
    assert latency_bootstrap([10])["status"] == "insufficient_samples"


@pytest.mark.parametrize(
    "config",
    [
        {"concurrency": 0},
        {"requests": True},
        {"rate": 0},
        {"rate": float("nan")},
        {"top_k": 10, "candidate_count": 5},
        {"profile": "agent"},
    ],
)
def test_experiment_config_bounds(config):
    with pytest.raises(ValidationError):
        BenchmarkConfig(**config)


def case(identity="q", kind="single_intent", language="en", group="g", split="dev"):
    return QueryCase(
        query_id=identity,
        query_type=kind,
        language=language,
        group_id=group,
        split=split,
        request={"text": "fixture coffee", "mode": "text"},
    )


def test_grouped_metrics_keep_task_language_and_denominators():
    rows = [
        {
            "task": "semantic_relevance",
            "query_type": "single_intent",
            "language": "en",
            "search_mode": "text",
            "metrics": {"recall@10": 0.5},
        },
        {
            "task": "semantic_relevance",
            "query_type": "single_intent",
            "language": "vi",
            "search_mode": "text",
            "metrics": {"recall@10": None},
        },
    ]
    groups = aggregate(rows)
    assert len(groups) == 2
    assert groups[0]["metrics"]["recall@10"] == {"mean": 0.5, "evaluated_queries": 1}
    assert groups[1]["metrics"]["recall@10"]["evaluated_queries"] == 0


def test_snapshot_bound_human_review_and_split_leakage(tmp_path):
    cases = [case()]
    snapshot = {"sha256": "fixture", "images": [{"image_id": "a"}]}
    labels = {
        "human_verified": True,
        "exhaustive_judgments": True,
        "annotator": "unit fixture, not actual human data",
        "dataset_sha256": "fixture",
        "query_set_sha256": query_digest(cases),
        "queries": {"q": {"grades": {"a": 2}}},
    }
    assert validate_labels(labels, snapshot, cases)["status"] == "valid"
    labels["human_verified"] = False
    with pytest.raises(ValueError):
        validate_labels(labels, snapshot, cases)
    labels["human_verified"] = True
    labels["queries"]["q"]["grades"] = {}
    with pytest.raises(ValueError):
        validate_labels(labels, snapshot, cases)
    file = tmp_path / "queries.jsonl"
    file.write_text(case().model_dump_json() + "\n" + case("q2", split="test").model_dump_json())
    with pytest.raises(ValueError):
        read_queries(file)


def test_immutable_experiment_artifacts_and_finite_serialization(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = Experiment(tmp_path / "runs", "unit", {"seed": 42})
    second = Experiment(tmp_path / "runs", "unit", {"seed": 42})
    assert first.identifier != second.identifier
    first.complete({"status": "measured"})
    with pytest.raises(FileExistsError):
        first.complete({"status": "replaced"})
    with pytest.raises(ValueError):
        second.write("invalid.json", {"x": float("nan")})
    assert not (second.directory / "invalid.json").exists()
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_abba_pools_samples_and_checks_rank_parity(tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    for number, width in enumerate([1, 2, 2, 1]):
        folder = tmp_path / "runs" / f"run{number}"
        folder.mkdir(parents=True)
        samples = [
            {
                "success": True,
                "effective_settings": {"object_check_concurrency": width},
                "query_id": key,
                "group_id": key,
                "result_ids": ["same", "rank"],
                "server_response_ms": value - (10 if width == 2 else 0),
                "stages": {"object_head_windows_ms": 5},
            }
            for key, value in [("a", 100), ("b", 200)]
        ]
        (folder / "result.json").write_text(
            json.dumps(
                {
                    "config": {"name": f"opt_head{width}_rep{number}"},
                    "failed": 0,
                    "samples": samples,
                }
            )
        )
    outcome = analyze_optimization(tmp_path / "runs")
    result = json.loads((tmp_path / "runs" / outcome["experiment_id"] / "result.json").read_text())
    assert result["pooled"]["1"]["server_latency"]["count"] == 4
    assert result["pooled"]["1"]["server_latency"]["mean_ms"] == 150
    assert result["pooled"]["2"]["server_latency"]["p90_ms"] == 190
    assert result["latency_mean_delta_cluster_bootstrap"]["mean_paired_delta"] == -10
    assert result["all_ranks_identical"]


def test_quality_ablation_keeps_query_scope_and_human_label_denominators(monkeypatch):
    import json

    from app.evaluation import quality
    from app.evaluation.dataset import case_tree, leaves

    cases = [
        case("single"),
        case("multi", kind="multi_intent").model_copy(
            update={"request": {"text": "coffee and cat", "mode": "multi_intent"}}
        ),
    ]
    snapshot = {
        "sha256": "fixture",
        "images": [{"image_id": "a"}],
        "active": {"model_id": "m", "index_id": "i", "manifest_sha256": "s"},
    }
    labels = {
        "human_verified": True,
        "exhaustive_judgments": True,
        "annotator": "unit fixture, not actual human judgments",
        "dataset_sha256": "fixture",
        "query_set_sha256": query_digest(cases),
        "queries": {
            "single": {"grades": {"a": 2}},
            "multi": {
                "grades": {"a": 2},
                "constraint_judgments": {
                    "a": {leaf.id: True for leaf in leaves(case_tree(cases[1]))}
                },
                "overall_satisfied": {"a": True},
            },
        },
    }
    received = []

    def respond(request):
        received.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                **snapshot["active"],
                "search_mode": "text",
                "results": [{"image_id": "a", "constraint_assessments": []}],
            },
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        quality.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw),
    )
    result = quality.evaluate(
        cases,
        snapshot,
        labels,
        "http://fixture",
        "unit",
        benchmark_config=BenchmarkConfig(
            profile="advanced", query_types=["multi_intent"], strategy="whole_query"
        ),
    )
    assert len(received) == 1 and received[0]["mode"] == "text"
    assert received[0]["rerank"]["enabled"] is False
    assert result["queries"][0]["query_id"] == "multi"
    assert result["queries"][0]["metrics"]["recall@10"] == 1
    assert result["queries"][0]["metrics"]["ndcg@10"] == 1


async def test_benchmark_warmup_failures_timeout_and_server_join(tmp_path, monkeypatch):
    file = tmp_path / "image"
    file.write_bytes(b"unit fixture")
    snapshot = {
        "images": [{"image_id": "a", "cache_file": str(file)}],
        "active": {"index_id": "i", "model_id": "m", "manifest_sha256": "s"},
    }
    server = []
    counter = 0

    def respond(request):
        nonlocal counter
        if request.url.path == "/api/v1/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/v1/system/search-metrics":
            return httpx.Response(200, json={"samples": server})
        counter += 1
        if counter == 3:
            raise httpx.ReadTimeout("unit timeout fixture")
        status = 503 if counter == 4 else 200
        rid = request.headers["x-request-id"]
        server.append({"request_id": rid, "server_response_ms": 2, "complete": True, "stages": {}})
        return httpx.Response(
            status,
            json={
                "index_id": "i",
                "model_id": "m",
                "manifest_sha256": "s",
                "results": [],
                "latency": {"processing_ms": 1},
                "effective_settings": {},
                "search_mode": "text",
                "error": {"code": "INFERENCE_BUSY"},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)),
    )
    result = await run_benchmark(
        BenchmarkConfig(requests=4, warmup=2, concurrency=1),
        [case()],
        snapshot,
        "http://unit",
        "unit-only-token",
    )
    assert result["attempted"] == 4 and result["warmup_count"] == 2
    assert result["successful"] == 2 and result["failed"] == 2 and result["error_rate"] == 0.5
    assert result["timeout_count"] == 1 and result["server_success_sample_count"] == 2
    assert result["fast_targets_observed"] is False


async def test_object_checks_preserve_rank_and_bound_speculation(settings):

    from app.schemas.search import Filters
    from app.services.search.search_service import SearchService
    from app.services.search.vector_retriever import Candidate

    settings.search_object_check_concurrency = 2
    runtime = SimpleNamespace(
        settings=settings,
        services=SimpleNamespace(),
        registry=SimpleNamespace(
            index=SimpleNamespace(id=UUID(int=1)), model=SimpleNamespace(manifest_sha256="s")
        ),
    )
    search = SearchService(runtime)
    inflight = peak = 0
    visited = []

    async def check(image, receipt):
        nonlocal inflight, peak
        visited.append(image.id)
        inflight += 1
        peak = max(peak, inflight)
        await asyncio.sleep(0.005 if image.id.int % 2 else 0.001)
        inflight -= 1
        return image.id.int != 1

    search.object_available = check
    rows = {}
    tags = {}
    ranked = []
    for n in range(1, 8):
        identity = UUID(int=n)
        image = SimpleNamespace(
            id=identity,
            sha256=str(n),
            metadata_revision=1,
            width=1,
            height=1,
            media_type="image/png",
            byte_size=1,
        )
        rows[identity] = (image, None, None, None)
        tags[identity] = []
        ranked.append(
            Candidate(
                identity,
                1 / n,
                {
                    "image_id": str(identity),
                    "index_id": str(UUID(int=1)),
                    "manifest_sha256": "s",
                    "source_sha256": str(n),
                    "metadata_revision": 1,
                },
            )
        )
    results, missing = await search.format_results(
        ranked, SimpleNamespace(top_k=3, filters=Filters()), {}, rows, tags
    )
    assert [row.image_id.int for row in results] == [2, 3, 4] and missing == 1
    assert peak == 2 and max(i.int for i in visited) == 4


def test_report_csv_and_charts_use_actual_input_artifact(tmp_path, monkeypatch):
    from app.evaluation.reporting import generate_report

    monkeypatch.chdir(tmp_path)
    experiment = Experiment(tmp_path / "results", "unit", {"name": "unit_fixture"})
    experiment.complete(
        {
            "status": "measured",
            "config": {"name": "unit_fixture", "profile": "fast", "concurrency": 1},
            "attempted": 4,
            "successful": 4,
            "failed": 0,
            "error_rate": 0,
            "successful_requests_per_second": 2,
            "server_success_latency": {"p50_ms": 1, "p90_ms": 2, "p95_ms": 3},
        }
    )
    result = generate_report(tmp_path / "results", tmp_path / "report")
    assert result["experiments"] == 1
    assert "unit_fixture" in (tmp_path / "report/summary.csv").read_text()
    assert (tmp_path / "report/latency.png").stat().st_size > 1000
    assert "Không tự tạo human judgments" in (tmp_path / "report/REPORT.md").read_text()


async def test_open_loop_capacity_drop_accounting_and_bound(tmp_path, monkeypatch):
    file = tmp_path / "image"
    file.write_bytes(b"unit fixture")
    snapshot = {
        "images": [{"image_id": "a", "cache_file": str(file)}],
        "active": {"index_id": "i", "model_id": "m", "manifest_sha256": "s"},
    }
    server = []
    inflight = peak = 0

    async def respond(request):
        nonlocal inflight, peak
        if request.url.path == "/api/v1/health":
            return httpx.Response(200, json={})
        if request.url.path == "/api/v1/system/search-metrics":
            return httpx.Response(200, json={"samples": server})
        inflight += 1
        peak = max(peak, inflight)
        await asyncio.sleep(0.04)
        inflight -= 1
        server.append(
            {
                "request_id": request.headers["x-request-id"],
                "server_response_ms": 40,
                "complete": True,
            }
        )
        return httpx.Response(
            200,
            json={
                "index_id": "i",
                "model_id": "m",
                "manifest_sha256": "s",
                "results": [],
                "latency": {"processing_ms": 1},
                "effective_settings": {},
                "search_mode": "text",
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)),
    )
    result = await run_benchmark(
        BenchmarkConfig(requests=8, warmup=0, concurrency=1, rate=100.0),
        [case()],
        snapshot,
        "http://unit",
        "unit-token",
    )
    assert result["attempted"] == 8 and result["successful"] + result["failed"] == 8
    assert result["error_codes"]["CLIENT_CAPACITY_DROP"] > 0 and peak == 1
