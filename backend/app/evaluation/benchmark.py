"""HTTP load generator đóng/mở, accounting cả failures, joins final ASGI samples."""

import asyncio
import json
import random
from collections import Counter
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from app.evaluation.statistics import describe, latency_bootstrap


def workload(cases, profile, requests, seed):
    groups = {
        "fast": [c for c in cases if c.query_type == "single_intent"],
        "image": [c for c in cases if c.query_type == "image"],
        "advanced": [c for c in cases if c.query_type in {"multi_intent", "multimodal"}],
    }
    rng = random.Random(seed)
    positions = Counter()
    output = []
    for _ in range(requests):
        name = (
            rng.choices(["fast", "image", "advanced"], weights=[0.5, 0.2, 0.3])[0]
            if profile == "mixed"
            else profile
        )
        if not groups[name]:
            raise ValueError("missing_workload_queries")
        output.append(groups[name][positions[name] % len(groups[name])])
        positions[name] += 1
    return output


def request_options(case, config):
    request = {**case.request, "top_k": config.top_k, "candidate_count": config.candidate_count}
    if case.query_type in {"multi_intent", "multimodal"}:
        request.update(
            {
                "rerank": {"enabled": config.rerank, "on_failure": "error"},
                "fusion": {"method": config.fusion},
                "retrieval_strategy": config.strategy
                if case.query_type == "multi_intent"
                else "fused",
            }
        )
    if config.filters:
        request["filters"] = config.filters
    if case.query_type == "multi_intent" and config.strategy == "whole_query":
        request["mode"] = "text"
        request.pop("constraints", None)
        request["rerank"] = {"enabled": False}
    if case.query_type == "multimodal" and config.paired_text_only:
        request.pop("image_id", None)
        request["mode"] = "text"
        request.pop("constraints", None)
        request["rerank"] = {"enabled": False}
    return request


async def run_benchmark(config, cases, snapshot, base_url, token):
    selected = [
        case for case in cases if not config.query_types or case.query_type in config.query_types
    ]
    sequence = workload(selected, config.profile, config.requests + config.warmup, config.seed)
    files = {
        row["image_id"]: await asyncio.to_thread(Path(row["cache_file"]).read_bytes)
        for row in snapshot["images"]
    }
    samples = []
    resources = []
    warmups = []
    stop_monitor = asyncio.Event()

    async def monitor():
        async with httpx.AsyncClient(
            base_url=base_url, headers={"Authorization": "Bearer " + token}, timeout=5
        ) as client:
            while not stop_monitor.is_set():
                try:
                    response = await client.get("/api/v1/system/search-runtime")
                    response.raise_for_status()
                    resources.append({"at_monotonic": perf_counter(), **response.json()})
                except Exception as exc:
                    resources.append({"unavailable": type(exc).__name__})
                try:
                    await asyncio.wait_for(stop_monitor.wait(), timeout=1)
                except TimeoutError:
                    pass

    monitor_task = asyncio.create_task(monitor()) if config.sample_resources else None
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=config.client_timeout,
        limits=httpx.Limits(
            max_connections=config.concurrency, max_keepalive_connections=config.concurrency
        ),
    ) as client:
        headers = {"Authorization": "Bearer " + token}
        health = await client.get("/api/v1/health?check=search", headers=headers)
        health.raise_for_status()

        async def send(case, scheduled=None):
            identity = str(uuid4())
            started = perf_counter()
            row = {
                "request_id": identity,
                "query_id": case.query_id,
                "query_type": case.query_type,
                "language": case.language,
                "group_id": case.group_id,
                "client_started_monotonic": started,
                "scheduling_lag_ms": max(0, (started - scheduled) * 1000) if scheduled else 0,
            }
            try:
                options = request_options(case, config)
                if (
                    case.query_type == "image"
                    or case.query_type == "multimodal"
                    and not config.paired_text_only
                ):
                    data = (
                        await asyncio.to_thread(Path(case.image_file).read_bytes)
                        if case.image_file
                        else files[options.pop("image_id")]
                    )
                    response = await client.post(
                        "/api/v1/search/multimodal",
                        headers=headers | {"X-Request-ID": identity},
                        files={"image": ("reference", data, "application/octet-stream")},
                        data={"options": json.dumps(options)},
                    )
                else:
                    response = await client.post(
                        "/api/v1/search", headers=headers | {"X-Request-ID": identity}, json=options
                    )
                row.update(
                    {"http_status": response.status_code, "success": response.status_code == 200}
                )
                value = response.json()
                if response.status_code == 200:
                    row.update(
                        {
                            "result_ids": [r["image_id"] for r in value["results"]],
                            "scores": [r["score"] for r in value["results"]],
                            "effective_settings": value["effective_settings"],
                            "processing_ms": value["latency"]["processing_ms"],
                            "model_id": value["model_id"],
                            "index_id": value["index_id"],
                            "executed_search_mode": value.get("search_mode"),
                        }
                    )
                    if any(
                        value[key] != snapshot["active"][key]
                        for key in ["model_id", "index_id", "manifest_sha256"]
                    ):
                        row.update(success=False, error_code="INDEX_DRIFT")
                else:
                    row["error_code"] = value.get("error", {}).get("code", "HTTP_ERROR")
            except Exception as exc:
                row.update(
                    {"http_status": None, "success": False, "error_code": type(exc).__name__}
                )
            row["client_ms"] = (perf_counter() - started) * 1000
            return row

        for case in sequence[: config.warmup]:
            warmups.append(await send(case))
        measured = sequence[config.warmup :]
        started = perf_counter()
        if config.rate is None:
            counter = iter(measured)

            async def worker():
                for case in counter:
                    if config.duration and perf_counter() - started >= config.duration:
                        break
                    samples.append(await send(case))

            await asyncio.gather(*(worker() for _ in range(config.concurrency)))
        else:
            tasks = set()
            for number, case in enumerate(measured):
                scheduled = started + number / config.rate
                if config.duration and scheduled >= started + config.duration:
                    break
                await asyncio.sleep(max(0, scheduled - perf_counter()))
                tasks = {task for task in tasks if not task.done()}
                if len(tasks) >= config.concurrency:
                    samples.append(
                        {
                            "request_id": str(uuid4()),
                            "query_id": case.query_id,
                            "query_type": case.query_type,
                            "language": case.language,
                            "http_status": None,
                            "success": False,
                            "error_code": "CLIENT_CAPACITY_DROP",
                            "client_ms": 0,
                            "client_started_monotonic": perf_counter(),
                            "scheduling_lag_ms": max(0, (perf_counter() - scheduled) * 1000),
                        }
                    )
                    continue

                async def attempt(case=case, scheduled=scheduled):
                    samples.append(await send(case, scheduled))

                tasks.add(asyncio.create_task(attempt()))
            if tasks:
                await asyncio.gather(*tasks)
        elapsed = perf_counter() - started
        metric_response = await client.get(
            "/api/v1/system/search-metrics?limit=10000", headers=headers
        )
        metric_response.raise_for_status()
        server = {row["request_id"]: row for row in metric_response.json()["samples"]}
    stop_monitor.set()
    if monitor_task:
        await monitor_task
    samples.sort(key=lambda r: r["client_started_monotonic"])
    for row in samples:
        span = server.get(row["request_id"])
        if span:
            row.update(
                {
                    "server_response_ms": span["server_response_ms"],
                    "server_complete": span["complete"],
                    "stages": span.get("stages", {}),
                    "serialization_send_ms": span.get("serialization_send_ms"),
                }
            )
    successes = [s for s in samples if s["success"]]
    durations = [s["server_response_ms"] for s in successes if s.get("server_complete")]
    errors = Counter(s.get("error_code", "UNKNOWN") for s in samples if not s["success"])
    count = len(samples)
    return {
        "status": "measured" if len(durations) == len(successes) else "incomplete_server_coverage",
        "config": config.model_dump(),
        "attempted": count,
        "requested_cap": config.requests,
        "successful": len(successes),
        "failed": count - len(successes),
        "error_rate": (count - len(successes)) / count if count else None,
        "timeout_count": sum(
            v for k, v in errors.items() if "TIMEOUT" in k.upper() or "DEADLINE" in k.upper()
        ),
        "error_codes": dict(errors),
        "http_status_counts": dict(Counter(str(s["http_status"]) for s in samples)),
        "duration_seconds_including_drain": elapsed,
        "achieved_attempts_per_second": count / elapsed,
        "successful_requests_per_second": len(successes) / elapsed,
        "offered_rate": config.rate,
        "offered_model": "open_loop_fixed_rate_with_capacity_drop"
        if config.rate
        else "closed_loop_bounded_clients",
        "server_success_latency": describe(durations),
        "client_success_latency": describe([r["client_ms"] for r in successes]),
        "client_all_attempt_latency": describe([r["client_ms"] for r in samples]),
        "server_success_sample_count": len(durations),
        "warmup_count": len(warmups),
        "warmup_failures": sum(not row["success"] for row in warmups),
        "warmup_samples": warmups,
        "cache_state": (
            "preloaded model/pools; explicit warmup; no query-result cache; "
            "OS page cache uncontrolled"
        ),
        "p90_bootstrap": latency_bootstrap(durations, seed=config.seed),
        "fast_targets_observed": config.profile == "fast"
        and count >= 300
        and len(durations) == count
        and describe(durations)["p90_ms"] <= 300
        and describe(durations)["p95_ms"] <= 500,
        "subgroups": {
            kind: {
                "attempted": sum(s["query_type"] == kind for s in samples),
                "successful": sum(s["success"] and s["query_type"] == kind for s in samples),
                "server_success_latency": describe(
                    [
                        s["server_response_ms"]
                        for s in successes
                        if s["query_type"] == kind and s.get("server_complete")
                    ]
                ),
            }
            for kind in sorted({s["query_type"] for s in samples})
        },
        "resource_samples": resources,
        "samples": samples,
    }
