"""Snapshot actual indexed corpus và query/label contracts; không gán semantic relevance."""

import base64
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image

from app.evaluation.contracts import QueryCase
from app.evaluation.tracking import digest
from app.schemas.constraints import leaves
from app.schemas.search import SearchRequest
from app.services.query.query_classifier import analyze_query


def read_queries(path):
    cases = [
        QueryCase.model_validate_json(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    if not cases or len({c.query_id for c in cases}) != len(cases):
        raise ValueError("empty_or_duplicate_query_ids")
    groups = {}
    for case in cases:
        if case.group_id in groups and groups[case.group_id] != case.split:
            raise ValueError("related_query_group_split_leakage")
        groups[case.group_id] = case.split
    return cases


def query_digest(cases):
    return digest([case.model_dump(mode="json") for case in cases])


def case_tree(case):
    options = SearchRequest.model_validate(case.request)
    return analyze_query(
        options.text, case.query_type == "multimodal", explicit=options.constraints
    ).constraints


def validate_dataset(base_url, token, index_report, cache, dataset_id="phase07_current_index"):
    ids = json.loads(Path(index_report).read_text())["image_ids"]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("invalid_corpus_ids")
    root = Path(cache)
    root.mkdir(parents=True, exist_ok=True)
    sample = json.loads(Path("datasets/sample_manifest.json").read_text())
    by_sha = {row["sha256"]: row for row in sample["images"]}
    images = []
    with httpx.Client(
        base_url=base_url, headers={"Authorization": "Bearer " + token}, timeout=10
    ) as client:
        ready = client.get("/api/v1/health?check=search")
        ready.raise_for_status()
        probe = client.post(
            "/api/v1/search", json={"text": "a photograph", "mode": "text", "top_k": 1}
        )
        probe.raise_for_status()
        active = {k: probe.json()[k] for k in ["model_id", "index_id", "manifest_sha256"]}
        runtime = client.get("/api/v1/system/search-runtime")
        server = (
            runtime.json()
            if runtime.status_code == 200
            else {"status": "runtime_endpoint_unavailable"}
        )
        for identity in ids:
            response = client.get("/api/v1/images/" + identity)
            response.raise_for_status()
            detail = response.json()
            if detail["status"] != "available" or not any(
                e["index_id"] == active["index_id"] and e["status"] == "ready"
                for e in detail["indexing"]
            ):
                raise ValueError("corpus_image_not_ready")
            raw = client.get(f"/api/v1/images/{identity}/content?variant=original")
            raw.raise_for_status()
            data = raw.content
            sha = hashlib.sha256(data).hexdigest()
            file = root / (identity + ".image")
            file.write_bytes(data)
            file.chmod(0o600)
            with Image.open(io.BytesIO(data)) as decoded:
                width, height = decoded.size
            if (width, height) != (detail["metadata"]["width"], detail["metadata"]["height"]):
                raise ValueError("image_dimension_mismatch")
            provenance = by_sha.get(sha, {})
            images.append(
                {
                    "image_id": identity,
                    "sha256": sha,
                    "byte_size": len(data),
                    "width": width,
                    "height": height,
                    "metadata": detail["metadata"],
                    "filename": provenance.get("filename", identity),
                    "rights_ref": provenance.get("rights_ref"),
                    "cache_file": file.as_posix(),
                }
            )
    if len({row["sha256"] for row in images}) != len(images):
        raise ValueError("duplicate_logical_images")
    result = {
        "dataset_id": dataset_id,
        "version": "1",
        "active": active,
        "images": images,
        "server_environment": server,
        "coverage": {
            "images": len(images),
            "accessible": len(images),
            "indexed_ready": len(images),
        },
        "limitations": [
            "Small existing corpus; not representative large-scale semantic benchmark",
            "No human semantic judgments yet",
        ],
    }
    result["sha256"] = digest(
        {k: v for k, v in result.items() if k not in {"server_environment", "limitations"}}
    )
    result["validated_at_utc"] = datetime.now(UTC).isoformat()
    return result


def prepare_queries(snapshot):
    named = {row["filename"]: row for row in snapshot["images"]}
    cases = []

    def add(
        identity,
        kind,
        lang,
        family,
        text=None,
        reference=None,
        constraints=None,
        task="semantic_relevance",
    ):
        split = "test" if family in {"camera", "rocket", "hubble"} else "dev"
        request = {
            "mode": {
                "single_intent": "text",
                "multi_intent": "multi_intent",
                "image": "image",
                "multimodal": "multimodal",
            }[kind],
            "top_k": 10,
            "exclude_self": False,
        }
        if text:
            request["text"] = text
        if constraints is not None:
            request["constraints"] = constraints
        if reference:
            request["image_id"] = named[reference]["image_id"]
        cases.append(
            QueryCase(
                query_id=identity,
                query_type=kind,
                language=lang,
                group_id=family,
                split=split,
                request=request,
                task=task,
            )
        )

    pairs = [
        ("coffee", "coffee.png", "a cup of coffee", "một tách cà phê"),
        ("cat", "chelsea.png", "a brown cat", "một con mèo màu nâu"),
        ("camera", "camera.png", "a person with a camera", "một người với máy ảnh"),
        ("rocket", "rocket.jpg", "a rocket at a launch site", "một tên lửa ở bệ phóng"),
        (
            "hubble",
            "hubble_deep_field.jpg",
            "stars and galaxies in deep space",
            "các ngôi sao và thiên hà trong vũ trụ",
        ),
        ("horse", "horse.png", "a silhouette of a horse", "bóng hình một con ngựa"),
    ]
    for family, file, en, vi in pairs:
        if file not in named:
            raise ValueError("Sample template requires known files; provide a custom query set")
        for lang, text in [("en", en), ("vi", vi)]:
            add(f"single_{family}_{lang}", "single_intent", lang, family, text)
    for count in [2, 3, 4]:
        for lang in ["en", "vi"]:
            phrases = (
                ["coffee", "a cup", "a saucer", "a wooden table"]
                if lang == "en"
                else ["cà phê", "một cái tách", "một cái đĩa", "một bàn gỗ"]
            )
            text = (" and " if lang == "en" else " và ").join(phrases[:count])
            tree = analyze_query(text, False).constraints
            add(
                f"and{count}_{lang}",
                "multi_intent",
                lang,
                "coffee",
                text,
                constraints=tree.model_dump(mode="json"),
            )
    for lang, text in [("en", "a camera or a rocket"), ("vi", "máy ảnh hoặc tên lửa")]:
        add(
            "or_" + lang,
            "multi_intent",
            lang,
            "camera",
            text,
            constraints=analyze_query(text, False).constraints.model_dump(mode="json"),
        )
    for lang, text in [
        ("en", "coffee and preferably warm light"),
        ("vi", "cà phê và ưu tiên ánh sáng ấm"),
    ]:
        add(
            "optional_" + lang,
            "multi_intent",
            lang,
            "coffee",
            text,
            constraints=analyze_query(text, False).constraints.model_dump(mode="json"),
        )
    for family, file, _, _ in pairs[:4]:
        add("identity_" + family, "image", "und", family, reference=file, task="exact_identity")
    for lang, text in [
        ("en", "a similar cup with a different background"),
        ("vi", "một cái tách tương tự với nền khác"),
    ]:
        add("paired_coffee_" + lang, "multimodal", lang, "coffee", text, "coffee.png")
    return cases


def validate_labels(labels, snapshot, cases):
    if (
        labels.get("human_verified") is not True
        or labels.get("exhaustive_judgments") is not True
        or len(labels.get("annotator", "").strip()) < 2
    ):
        raise ValueError("human_review_required")
    if labels.get("dataset_sha256") != snapshot["sha256"] or labels.get(
        "query_set_sha256"
    ) != query_digest(cases):
        raise ValueError("label_snapshot_mismatch")
    expected = {c.query_id for c in cases if c.task == "semantic_relevance"}
    if set(labels.get("queries", {})) != expected:
        raise ValueError("query_judgment_coverage_incomplete")
    universe = {row["image_id"] for row in snapshot["images"]}
    threshold = labels.get("binary_relevance_min_grade", 2)
    if type(threshold) is not int or threshold not in {1, 2}:
        raise ValueError("invalid_binary_threshold")
    for case in cases:
        if case.task != "semantic_relevance":
            continue
        query = labels["queries"][case.query_id]
        if set(query.get("grades", {})) != universe:
            raise ValueError("exhaustive_corpus_judgments_required")
        if any(type(g) is not int or g not in {0, 1, 2} for g in query["grades"].values()):
            raise ValueError("invalid_grade")
        if (
            not any(g >= threshold for g in query["grades"].values())
            and query.get("allow_no_answer") is not True
        ):
            raise ValueError("explicit_no_answer_policy_required")
        tree = case_tree(case) if case.query_type == "multi_intent" else None
        clause_ids = {leaf.id for leaf in leaves(tree)}
        if clause_ids:
            if (
                set(query.get("constraint_judgments", {})) != universe
                or set(query.get("overall_satisfied", {})) != universe
            ):
                raise ValueError("constraint_labels_incomplete")
            for identity in universe:
                if set(query["constraint_judgments"][identity]) != clause_ids:
                    raise ValueError("clause_judgment_coverage_incomplete")
                if any(
                    value is not None and type(value) is not bool
                    for value in [
                        *query["constraint_judgments"][identity].values(),
                        query["overall_satisfied"][identity],
                    ]
                ):
                    raise ValueError("invalid_constraint_truth")
    return {
        "status": "valid",
        "queries": len(expected),
        "images": len(universe),
        "label_sha256": digest(labels),
        "binary_threshold": threshold,
    }


def annotation_pack(snapshot, cases, template, output):
    images = []
    for row in snapshot["images"]:
        data = Path(row["cache_file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("cached_image_digest_mismatch")
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail((320, 240))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=80)
        images.append(
            {
                "image_id": row["image_id"],
                "preview": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode(),
                "license": row["metadata"]["license"],
            }
        )
    semantic = [c for c in cases if c.task == "semantic_relevance"]
    queries = []
    for case in semantic:
        tree = case_tree(case) if case.query_type == "multi_intent" else None
        queries.append(
            {
                **case.model_dump(mode="json"),
                "clauses": [
                    {
                        "id": leaf.id,
                        "text": leaf.text or "Metadata predicate",
                        "required": leaf.required,
                        "negated": leaf.negated,
                    }
                    for leaf in leaves(tree)
                ],
            }
        )
    payload = {
        "dataset_sha256": snapshot["sha256"],
        "query_set_sha256": query_digest(cases),
        "images": images,
        "queries": queries,
    }
    html = (
        Path(template)
        .read_text()
        .replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c"))
    )
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html)
    target.chmod(0o600)
    return {
        "status": "ready_for_human_annotation",
        "images": len(images),
        "queries": len(semantic),
        "output": str(target),
    }
