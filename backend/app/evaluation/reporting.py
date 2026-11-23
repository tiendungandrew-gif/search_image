"""CSV/Markdown/standalone charts từ immutable actual experiments; không fake quality bars."""

import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def generate_report(results, output):
    runs = []
    for path in sorted(Path(results).glob("*/result.json")):
        meta = json.loads((path.parent / "experiment.json").read_text())
        value = json.loads(path.read_text())
        runs.append({"experiment": meta, "result": value, "artifact": path.as_posix()})
    if not runs:
        raise ValueError("no_experiments")
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    summary = []
    for run in runs:
        value = run["result"]
        config = value.get("config", run["experiment"]["config"])
        latency = value.get("server_success_latency", {})
        summary.append(
            {
                "experiment_id": run["experiment"]["experiment_id"],
                "name": config.get("name", config.get("model", run["experiment"]["kind"])),
                "status": value["status"],
                "profile": config.get("profile"),
                "concurrency": config.get("concurrency"),
                "attempted": value.get("attempted"),
                "successful": value.get("successful"),
                "failed": value.get("failed"),
                "p50_ms": latency.get("p50_ms"),
                "p90_ms": latency.get("p90_ms"),
                "p95_ms": latency.get("p95_ms"),
                "requests_per_second": value.get("successful_requests_per_second"),
                "error_rate": value.get("error_rate"),
                "artifact": run["artifact"],
            }
        )
    with (target / "summary.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    with (target / "summary.json").open("x") as handle:
        json.dump(
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "experiments": summary,
                "semantic_quality": "not_measured_unless_human_verified_result_present",
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    with (target / "queries.csv").open("x", newline="") as handle:
        fields = [
            "experiment_id",
            "query_id",
            "task",
            "query_type",
            "language",
            "search_mode",
            "status",
            "encoding_ms",
            "result_ids",
            "metrics",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            for query in run["result"].get("queries", []):
                row = {key: query.get(key) for key in fields}
                row["experiment_id"] = run["experiment"]["experiment_id"]
                row["result_ids"] = json.dumps(query.get("result_ids", []))
                row["metrics"] = json.dumps(query.get("metrics", query.get("identity_metrics")))
                writer.writerow(row)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rag_groups = [
        {"experiment_id": run["experiment"]["experiment_id"], "configuration": name, **group}
        for run in runs
        if "cases" in run["result"]
        for name, group in run["result"].get("groups", {}).items()
    ]
    if rag_groups:
        with (target / "rag_cases.csv").open("x", newline="") as handle:
            fields = [
                "experiment_id",
                "case_id",
                "configuration",
                "language",
                "status",
                "http_status",
                "generated",
                "error_code",
                "client_total_ms",
                "provider_ttft_ms",
                "request_ttlast_ms",
                "citations",
                "exact_quotes",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for run in runs:
                for case in run["result"].get("cases", []):
                    rag = case.get("result", {}).get("rag", {})
                    latency = case.get("result", {}).get("latency", {})
                    audit = case.get("citation_audit", {})
                    writer.writerow(
                        {
                            **{k: case.get(k) for k in fields[1:6]},
                            "experiment_id": run["experiment"]["experiment_id"],
                            "generated": rag.get("generated"),
                            "error_code": rag.get("error_code"),
                            "client_total_ms": case["client_total_ms"],
                            "provider_ttft_ms": latency.get("provider_ttft_ms"),
                            "request_ttlast_ms": latency.get("time_to_last_token_from_request_ms"),
                            "citations": audit.get("citations"),
                            "exact_quotes": audit.get("exact_evidence_citations"),
                        }
                    )
        with (target / "rag_summary.csv").open("x", newline="") as handle:
            fields = [
                "experiment_id",
                "configuration",
                "attempted",
                "generated",
                "http_failures",
                "generation_unavailable",
                "client_p90_ms",
                "provider_ttft_p90_ms",
                "request_ttlast_p90_ms",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for group in rag_groups:
                writer.writerow(
                    {
                        **{k: group[k] for k in fields[:6]},
                        "client_p90_ms": group["client_latency"]["p90_ms"],
                        "provider_ttft_p90_ms": group["provider_ttft"]["p90_ms"],
                        "request_ttlast_p90_ms": group["time_to_last_token_from_request"]["p90_ms"],
                    }
                )
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].bar(
            [g["configuration"] + "@" + g["experiment_id"][-4:] for g in rag_groups],
            [g["client_latency"]["p90_ms"] for g in rag_groups],
        )
        axes[0].set_ylabel("Client P90 ms, all attempts")
        measured = [g for g in rag_groups if g["generated"]]
        axes[1].bar(
            [g["configuration"] + "@" + g["experiment_id"][-4:] for g in measured],
            [g["time_to_last_token_from_request"]["p90_ms"] for g in measured],
        )
        axes[1].axhline(3000, color="red", linestyle="--", label="3 s objective")
        axes[1].set_ylabel("Request to last provider token P90 ms, generated only")
        axes[1].legend()
        for ax in axes:
            plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)
        fig.suptitle("Exploratory RAG timings; failures and sample sizes in rag_summary.csv")
        fig.tight_layout()
        for ext in ["png", "svg"]:
            fig.savefig(target / ("rag_latency." + ext), dpi=160)
        plt.close(fig)

    latency_runs = [row for row in summary if row["p90_ms"] is not None]
    if latency_runs:
        fig, ax = plt.subplots(figsize=(max(9, len(latency_runs) * 0.65), 5.5))
        x = list(range(len(latency_runs)))
        for offset, key, label in [
            (-0.25, "p50_ms", "P50"),
            (0, "p90_ms", "P90"),
            (0.25, "p95_ms", "P95"),
        ]:
            ax.bar(
                [v + offset for v in x], [row[key] for row in latency_runs], width=0.24, label=label
            )
        ax.set_xticks(x, [row["name"] for row in latency_runs], rotation=45, ha="right")
        ax.set_ylabel("Full server latency (ms), successful requests")
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
        fig.tight_layout()
        for ext in ["svg", "png"]:
            fig.savefig(target / ("latency." + ext), dpi=160)
        plt.close(fig)
        loads = [row for row in latency_runs if "load" in row["name"]]
        if loads:
            fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
            for profile in sorted({row["profile"] for row in loads}):
                group = sorted(
                    [r for r in loads if r["profile"] == profile], key=lambda r: r["concurrency"]
                )
                axes[0].plot(
                    [r["concurrency"] for r in group],
                    [r["requests_per_second"] for r in group],
                    marker="o",
                    label=profile,
                )
                axes[1].plot(
                    [r["concurrency"] for r in group],
                    [r["error_rate"] * 100 for r in group],
                    marker="o",
                    label=profile,
                )
            axes[0].set_ylabel("Successful requests/s")
            axes[1].set_ylabel("Failed attempts (%)")
            for ax in axes:
                ax.set_xlabel("Concurrent clients")
                ax.legend()
                ax.grid(alpha=0.2)
            fig.tight_layout()
            for ext in ["svg", "png"]:
                fig.savefig(target / ("load." + ext), dpi=160)
            plt.close(fig)
    latest_models = {}
    for run in runs:
        value = run["result"]
        if "model_initialization_fresh_process_ms" in value:
            latest_models[(value.get("checkpoint", value["model"]), value.get("revision"))] = value
    model_runs = list(latest_models.values())
    if model_runs:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
        axes[0].bar(
            [r["model"] for r in model_runs],
            [r["model_initialization_fresh_process_ms"] for r in model_runs],
        )
        axes[0].set_ylabel("Fresh model initialization + warmup (ms)")
        axes[1].bar(
            [r["model"] for r in model_runs], [r["process_peak_rss_kib"] / 1024 for r in model_runs]
        )
        axes[1].set_ylabel("Process peak RSS (MiB)")
        fig.suptitle("CPU: latest run per checkpoint/revision; all runs retained in raw artifacts")
        fig.tight_layout()
        for ext in ["svg", "png"]:
            fig.savefig(target / ("models." + ext), dpi=160)
        plt.close(fig)
    # Only human-verified semantic aggregates can create a model-quality chart.
    quality_groups = [
        (run["result"].get("model", run["experiment"]["experiment_id"]), group)
        for run in runs
        if run["result"].get("label_sha256")
        for group in run["result"].get("aggregates", [])
        if group["task"] == "semantic_relevance"
    ]
    if quality_groups:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, metric in zip(axes, ["recall@10", "ndcg@10"], strict=True):
            judged = [
                (name, group)
                for name, group in quality_groups
                if group["metrics"].get(metric, {}).get("mean") is not None
            ]
            ax.bar(
                [f"{name}/{g['query_type']}/{g['language']}" for name, g in judged],
                [g["metrics"][metric]["mean"] for _, g in judged],
            )
            ax.set_ylabel(metric)
            ax.set_ylim(0, 1)
            ax.tick_params(axis="x", rotation=65)
        fig.tight_layout()
        for ext in ["png", "svg"]:
            fig.savefig(target / ("semantic_quality." + ext), dpi=160)
        plt.close(fig)
    text = [
        "# Kết quả thí nghiệm retrieval và RAG",
        "",
        (
            "Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. "
            "Không cộng component percentiles hoặc suy SLA từ corpus nhỏ."
        ),
        "",
        "| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary:
        text.append(
            f"| {row['name']} | {row['status']} | {row['attempted']} / {row['failed']} | "
            f"{row['p90_ms']} | {row['p95_ms']} | {row['requests_per_second']} |"
        )
    if rag_groups:
        text.extend(
            [
                "",
                "## RAG: số đo thực, tách failures khỏi generated latency",
                "",
                "| Run / cấu hình | N / generated / unavailable | Client P90 ms | "
                "Provider TTFT P90 ms | Request TTLast P90 ms |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for group in rag_groups:

            def number(value):
                return f"{value:.2f}" if value is not None else "—"

            text.append(
                f"| {group['experiment_id']} / {group['configuration']} | "
                f"{group['attempted']} / {group['generated']} / "
                f"{group['generation_unavailable']} | "
                f"{number(group['client_latency']['p90_ms'])} | "
                f"{number(group['provider_ttft']['p90_ms'])} | "
                f"{number(group['time_to_last_token_from_request']['p90_ms'])} |"
            )
        text.extend(
            [
                "",
                "TTFT/TTLast chỉ trên generated requests; unavailable không bị bỏ khỏi counts. "
                "N nhỏ, không là production SLA proof. Xem rag_cases.csv/JSON cho per-case audits.",
            ]
        )
    text.extend(
        [
            "",
            "## Chất lượng và giới hạn",
            "",
            (
                "Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. "
                "Identity/ANN overlap không thay semantic quality. "
                "Không có GPU comparison khi thiếu GPU."
            ),
            "",
            "## Provenance",
            "",
        ]
    )
    for run in runs:
        text.append(
            f"- `{run['experiment']['experiment_id']}` → "
            f"[raw artifact]({os.path.relpath(run['artifact'], target)})"
        )
    from app.evaluation.agent import report_agent_runs

    text.extend(report_agent_runs(runs, target))
    (target / "REPORT.md").write_text("\n".join(text) + "\n")
    return {
        "status": "generated",
        "experiments": len(runs),
        "directory": target.as_posix(),
        "charts": sorted(p.name for p in target.glob("*.png")),
    }
