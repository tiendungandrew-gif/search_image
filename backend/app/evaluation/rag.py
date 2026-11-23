"""R1–R4 real HTTP experiments, labels optional and independent of citation mechanics."""

import base64
import json
from pathlib import Path
from time import perf_counter
from uuid import UUID

import httpx

from app.evaluation.statistics import describe
from app.evaluation.tracking import Experiment, digest


def audit_citations(response):
    results = {r["image_id"] for r in response["results"]}
    evidence = {e["image_id"]: e for e in response["rag"]["evidence"]}
    citations = response["rag"]["citations"]
    valid_ids = 0
    exact = 0
    for citation in citations:
        identity = citation["image_id"]
        valid_ids += identity in results and identity in evidence
        item = evidence.get(identity)
        if item is None:
            continue
        field = citation["evidence_field"]
        value = (
            item["caption"]
            if field == "caption"
            else ", ".join(item["tags"])
            if field == "tags"
            else item["metadata"].get(field)
        )
        exact += value is not None and str(value) == citation["quote"]
    return {
        "citations": len(citations),
        "valid_image_citations": valid_ids,
        "exact_evidence_citations": exact,
        "citation_id_validity": valid_ids / len(citations) if citations else None,
        "exact_quote_support": exact / len(citations) if citations else None,
        "faithfulness_to_visual_content": None,
        "answer_relevance": None,
        "human_review_status": "pending",
        "unsupported_claim_rate": None,
    }


def validate_review(labels, results):
    results = [row for row in results if row["configuration"] in {"R3", "R4"}]
    if labels.get("human_verified") is not True or not labels.get("annotator"):
        raise ValueError("human_review_required")
    expected = {row["case_id"] for row in results}
    if set(labels.get("cases", {})) != expected:
        raise ValueError("review_coverage_mismatch")
    for value in labels["cases"].values():
        if set(value) != {"answer_relevance", "faithfulness", "unsupported_claims", "claims"}:
            raise ValueError("review_schema_invalid")
        if any(
            value[k] is not None and (type(value[k]) is not int or value[k] not in {0, 1, 2})
            for k in ["answer_relevance", "faithfulness"]
        ):
            raise ValueError("review_grade_invalid")
        if (
            any(type(value[k]) is not int or value[k] < 0 for k in ["claims", "unsupported_claims"])
            or value["unsupported_claims"] > value["claims"]
        ):
            raise ValueError("review_claim_counts_invalid")
    groups = {}
    for mode, language in sorted({(r["configuration"], r["language"]) for r in results}):
        values = [
            labels["cases"][r["case_id"]]
            for r in results
            if r["language"] == language and r["configuration"] == mode
        ]
        claims = sum(v["claims"] for v in values)
        graded = {
            k: [v[k] for v in values if v[k] is not None]
            for k in ["answer_relevance", "faithfulness"]
        }
        groups[mode + "/" + language] = {
            "reviewed_cases": len(values),
            "means_0_to_2": {k: sum(v) / len(v) if v else None for k, v in graded.items()},
            "evaluated_cases": {k: len(v) for k, v in graded.items()},
            "unsupported_claim_rate": sum(v["unsupported_claims"] for v in values) / claims
            if claims
            else None,
        }
    return {"status": "valid", "reviewed_cases": len(expected), "by_task_and_language": groups}


def run_experiments(base_url, token, results, requests=20, workload=None):
    if workload:
        if requests < 4 * len(workload) or requests % 4:
            raise ValueError("Workload cần đủ 4 cấu hình cho mỗi câu hỏi")
        for item in workload:
            if set(item) != {"query", "question", "language"} or item["language"] not in {
                "vi",
                "en",
            }:
                raise ValueError("Invalid RAG workload")
            if any(
                not isinstance(item[k], str) or not 1 <= len(item[k]) <= 2000
                for k in ["query", "question"]
            ):
                raise ValueError("Invalid RAG workload text")
    experiment = Experiment(
        results,
        "rag",
        {
            "requests": requests,
            "modes": ["R1", "R2", "R3", "R4"],
            "seed": 42,
            "workload": workload,
            "workload_sha256": digest(workload),
        },
    )
    rows = []
    headers = {"Authorization": "Bearer " + token}
    with httpx.Client(base_url=base_url, headers=headers, timeout=65) as client:
        status = client.get("/api/v1/rag/status")
        status.raise_for_status()
        for number in range(requests):
            kind = ["R1", "R2", "R3", "R4"][number % 4]
            language = "vi" if number // 4 % 2 == 0 else "en"
            question = (
                "Metadata ghi định dạng và kích thước của ảnh như thế nào?"
                if language == "vi"
                else "What are the image format and dimensions in the metadata?"
            )
            task = (
                workload[number // 4 % len(workload)]
                if workload
                else {"query": "a cup of coffee", "question": question, "language": language}
            )
            body = {
                **task,
                "top_k": 3,
                "max_evidence_items": 1 if kind == "R4" else 3,
            }
            started = perf_counter()
            row = {"case_id": f"{kind}_{number:03}", "configuration": kind, **task}
            try:
                if kind in {"R1", "R2"}:
                    response = client.post(
                        "/api/v1/search", json={"text": body["query"], "mode": "text", "top_k": 3}
                    )
                    response.raise_for_status()
                    value = response.json()
                    row.update(
                        status="search_only" if kind == "R1" else "metadata_baseline", result=value
                    )
                else:
                    response = client.post("/api/v1/rag/explain", json=body)
                    response.raise_for_status()
                    value = response.json()
                    row.update(
                        status=value["rag"]["grounding_status"],
                        result=value,
                        citation_audit=audit_citations(value),
                    )
                row["http_status"] = response.status_code
            except httpx.HTTPError as error:
                row.update(
                    status="failed",
                    error_type=type(error).__name__,
                    http_status=getattr(getattr(error, "response", None), "status_code", None),
                )
            row["client_total_ms"] = (perf_counter() - started) * 1000
            rows.append(row)
    groups = {}
    for kind in ["R1", "R2", "R3", "R4"]:
        group = [r for r in rows if r["configuration"] == kind]
        generated = [r for r in group if r.get("result", {}).get("rag", {}).get("generated")]
        groups[kind] = {
            "attempted": len(group),
            "http_failures": sum(r["status"] == "failed" for r in group),
            "generated": len(generated),
            "generation_unavailable": sum(r["status"] == "generation_unavailable" for r in group),
            "client_latency": describe([r["client_total_ms"] for r in group]),
            "provider_ttft": describe(
                [r["result"]["latency"]["provider_ttft_ms"] for r in generated]
            ),
            "time_to_last_token_from_request": describe(
                [r["result"]["latency"]["time_to_last_token_from_request_ms"] for r in generated]
            ),
            "semantic_answer_quality": "pending_human_review",
        }
    result = {
        "status": "measured",
        "runtime": status.json(),
        "cases": rows,
        "groups": groups,
        "sample_size_note": "exploratory small-N RAG trial; not a production percentile/SLA proof",
        "R2_policy": "actual metadata displayed without LLM; no generated prose claimed",
        "R5": "unavailable_no_vision_grounding",
    }
    experiment.complete(result)
    return {
        "experiment_id": experiment.identifier,
        "directory": str(experiment.directory),
        "groups": groups,
    }


def build_review_pack(base_url, token, result_path, output, *, transport=None):
    """Freeze actual answers/evidence and authenticated images into offline review HTML."""
    result_path, output = Path(result_path), Path(output)
    result = json.loads(result_path.read_text())
    rows = [r for r in result["cases"] if r["configuration"] in {"R3", "R4"}]
    if not rows or len(rows) > 100:
        raise ValueError("REVIEW_CASE_LIMIT")
    identities = sorted(
        {
            str(UUID(item["image_id"]))
            for row in rows
            for item in row.get("result", {}).get("results", [])
        }
    )
    if len(identities) > 50:
        raise ValueError("REVIEW_IMAGE_LIMIT")
    images = {}
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": "Bearer " + token},
        timeout=15,
        transport=transport,
    ) as client:
        for identity in identities:
            with client.stream(
                "GET", f"/api/v1/images/{identity}/content?variant=original"
            ) as response:
                response.raise_for_status()
                mime = response.headers.get("content-type", "").split(";")[0]
                if mime not in {"image/jpeg", "image/png", "image/webp"}:
                    raise ValueError("REVIEW_IMAGE_TYPE")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 20 * 1024**2:
                        raise ValueError("REVIEW_IMAGE_SIZE")
            images[identity] = f"data:{mime};base64," + base64.b64encode(raw).decode()
    labels = {
        "schema_version": 1,
        "result_sha256": digest(result),
        "experiment_id": result_path.parent.name,
        "label_version": "human-v1",
        "annotator": "",
        "human_verified": False,
        "reviewed_at_utc": None,
        "cases": {
            r["case_id"]: {
                "answer_relevance": None,
                "faithfulness": None,
                "claims": None,
                "unsupported_claims": None,
            }
            for r in rows
        },
    }
    payload = json.dumps({"cases": rows, "images": images, "labels": labels}, ensure_ascii=False)
    template = Path("evaluation/annotation/rag_review.html").read_text()
    # Never let imported captions terminate the executable script element.
    html = template.replace("/*__DATA__*/", payload.replace("<", "\\u003c"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        handle.write(html)
    output.chmod(0o600)
    return {
        "status": "created",
        "path": str(output),
        "cases": len(rows),
        "images": len(images),
        "result_sha256": digest(result),
        "human_verified": False,
    }
