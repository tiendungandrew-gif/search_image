"""Thống kê có seed/denominators rõ; không cộng các component percentiles."""

import math
import random
import statistics

from app.evaluation.metrics import nearest_rank


def describe(values):
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("invalid_latency")
    return {
        "count": len(values),
        "median_ms": statistics.median(values) if values else None,
        "min_ms": min(values) if values else None,
        "mean_ms": statistics.fmean(values) if values else None,
        "p50_ms": nearest_rank(values, 0.5),
        "p90_ms": nearest_rank(values, 0.9),
        "p95_ms": nearest_rank(values, 0.95),
        "p99_ms": nearest_rank(values, 0.99),
        "max_ms": max(values) if values else None,
        "stddev_ms": statistics.pstdev(values) if values else None,
    }


def paired_bootstrap(before, after, groups=None, repetitions=2000, seed=42):
    if set(before) != set(after) or not before or repetitions < 20:
        raise ValueError("paired_query_sets_required")
    ids = sorted(before)
    clusters = {}
    for key in ids:
        if not all(math.isfinite(v) for v in [before[key], after[key]]):
            raise ValueError("invalid_metric")
        clusters.setdefault(groups[key] if groups else key, []).append(after[key] - before[key])
    if len(clusters) < 2:
        return {
            "status": "insufficient_independent_groups",
            "query_count": len(ids),
            "group_count": len(clusters),
        }
    rng = random.Random(seed)
    names = sorted(clusters)
    samples = []
    for _ in range(repetitions):
        differences = [d for name in rng.choices(names, k=len(names)) for d in clusters[name]]
        samples.append(statistics.fmean(differences))
    samples.sort()
    return {
        "status": "measured",
        "mean_paired_delta": statistics.fmean(after[k] - before[k] for k in ids),
        "ci95_low": nearest_rank(samples, 0.025),
        "ci95_high": nearest_rank(samples, 0.975),
        "query_count": len(ids),
        "group_count": len(clusters),
        "repetitions": repetitions,
        "seed": seed,
        "method": "paired cluster bootstrap, percentile 95% CI; shared group resampling",
    }


def latency_bootstrap(values, repetitions=500, block_size=10, seed=42):
    if len(values) < 100:
        return {"status": "insufficient_samples", "count": len(values)}
    rng = random.Random(seed)
    blocks = [values[i : i + block_size] for i in range(0, len(values), block_size)]
    samples = []
    for _ in range(repetitions):
        sample = [v for block in rng.choices(blocks, k=len(blocks)) for v in block][: len(values)]
        samples.append(nearest_rank(sample, 0.9))
    return {
        "status": "measured",
        "p90_ci95_low_ms": nearest_rank(samples, 0.025),
        "p90_ci95_high_ms": nearest_rank(samples, 0.975),
        "method": "consecutive-block bootstrap, descriptive successful-request p90",
        "block_size": block_size,
        "repetitions": repetitions,
        "seed": seed,
    }
