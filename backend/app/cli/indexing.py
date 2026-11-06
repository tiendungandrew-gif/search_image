"""CLI quản trị local: model/register/worker/ingest/dataset/job/retry/reindex/verify."""

import argparse
import asyncio
import hashlib
import io
import json
import resource
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.models import DatasetSource
from app.schemas.ingestion import ImageMetadataInput, JobInput
from app.services.embeddings.clip_encoder import ClipEncoder
from app.services.health import Services
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import object_orphans, verify_index
from app.services.indexing.jobs import ingest, job_response
from app.services.indexing.submission import submit_job
from app.services.indexing.worker import Worker


def output(value):
    print(json.dumps(value, ensure_ascii=False, default=str, indent=2))


async def execute(args):
    settings = Settings()
    configure_logging(settings.log_level)
    services = Services(settings)
    try:
        await services.initialize()
        if args.command == "register":
            encoder = await asyncio.to_thread(ClipEncoder, settings)
            index, model = await CollectionManager(services).register(encoder, args.version)
            output(
                {
                    "index_id": index.id,
                    "model_id": model.id,
                    "collection": index.collection_name,
                    "manifest_sha256": model.manifest_sha256,
                    "dimension": model.dimension,
                    "device": encoder.device,
                    "model_initialization_ms": encoder.initialization_ms,
                }
            )
        elif args.command == "model":
            async with services.database.sessions() as session:
                from app.db.models import EmbeddingModel

                models = (await session.scalars(select(EmbeddingModel))).all()
                output(
                    [
                        {
                            "model_id": m.id,
                            "manifest_sha256": m.manifest_sha256,
                            "manifest": m.manifest,
                        }
                        for m in models
                    ]
                )
        elif args.command == "orphans":
            output(await object_orphans(services))
        elif args.command == "worker":
            encoder = await asyncio.to_thread(ClipEncoder, settings)
            worker = Worker(services, encoder, args.index)
            worker_started = perf_counter()
            await worker.run(once=args.once)
            worker_ms = (perf_counter() - worker_started) * 1000
            output(
                {
                    "model_initialization_ms": encoder.initialization_ms,
                    "device": encoder.device,
                    "batches": worker.batch_metrics,
                    "worker_ms": worker_ms,
                    "images_per_second": sum(b["batch_size"] for b in worker.batch_metrics)
                    / (worker_ms / 1000),
                    "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
            )
        elif args.command in {"image", "dataset"}:
            root = await asyncio.to_thread(Path(settings.dataset_root).resolve)
            path = await asyncio.to_thread(Path(args.input).resolve)
            if not path.is_relative_to(root) or await asyncio.to_thread(
                Path(args.input).is_symlink
            ):
                raise ValueError("DATASET_PATH_NOT_ALLOWED")
            metadata_by_file = {}
            if args.command == "dataset" and (path / "metadata.jsonl").is_file():
                raw = (path / "metadata.jsonl").read_bytes()
                if len(raw) > 1024 * 1024:
                    raise ValueError("MANIFEST_TOO_LARGE")
                for line in raw.decode().splitlines():
                    row = json.loads(line)
                    name = row.pop("filename")
                    metadata_by_file[name] = row
            candidates = sorted(path.rglob("*")) if path.is_dir() else [path]
            files = [
                p
                for p in candidates
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]
            if not 1 <= len(files) <= 1000:
                raise ValueError("DATASET_COUNT_LIMIT")
            report = {
                "discovered": len(files),
                "validated": 0,
                "duplicates": 0,
                "accepted": 0,
                "failed": 0,
                "ignored": len([p for p in candidates if p.is_file()]) - len(files),
                "results": [],
            }
            import time

            started = time.perf_counter()
            for file in files:
                try:
                    if file.is_symlink() or not file.resolve().is_relative_to(root):
                        raise ValueError("SYMLINK_NOT_ALLOWED")
                    with file.open("rb") as handle:
                        data = handle.read(settings.image_max_upload_mb * 1024**2 + 1)
                    relative = file.relative_to(path).as_posix() if path.is_dir() else file.name
                    values = {
                        "source_dataset": args.name,
                        "license": args.license,
                        "rights_ref": args.rights_ref,
                        **metadata_by_file.get(relative, {}),
                    }
                    metadata = ImageMetadataInput.model_validate(values)
                    key = (
                        "cli-"
                        + hashlib.sha256(
                            data
                            + json.dumps(values, sort_keys=True).encode()
                            + str(args.index).encode()
                        ).hexdigest()
                    )
                    status, response = await ingest(services, data, metadata, key, args.index)
                    report["validated"] += 1
                    report["accepted"] += 1
                    report["duplicates"] += int(response["duplicate"])
                    report["results"].append({"filename": relative, **response})
                except Exception as exc:
                    report["failed"] += 1
                    report["results"].append(
                        {
                            "filename": file.name,
                            "error_code": getattr(exc, "code", "INVALID_SOURCE"),
                        }
                    )
            report["ingestion_ms"] = (time.perf_counter() - started) * 1000
            ids = sorted({r["image_id"] for r in report["results"] if "image_id" in r})
            if args.command == "dataset" and ids:
                manifest = json.dumps({"image_ids": ids}, sort_keys=True).encode()
                digest = hashlib.sha256(manifest).hexdigest()
                key = "datasets/" + digest + ".json"
                await services.minio.run(
                    lambda: services.minio.client.put_object(
                        services.minio.bucket,
                        key,
                        io.BytesIO(manifest),
                        len(manifest),
                        content_type="application/json",
                    )
                )
                async with services.database.sessions() as session, session.begin():
                    name = args.name + "-" + digest[:12]
                    source = await session.scalar(
                        select(DatasetSource).where(DatasetSource.name == name)
                    )
                    if source is None:
                        source = DatasetSource(
                            id=uuid4(),
                            name=name,
                            kind="object_manifest",
                            root_config_key="DATASET_ROOT",
                            manifest_ref=key,
                            manifest_sha256=digest,
                            rights_ref=args.rights_ref,
                            enabled=True,
                        )
                        session.add(source)
                    report["source_id"] = str(source.id)
            output(report)
        elif args.command == "job":
            output(await job_response(services, args.job, limit=100))
        elif args.command in {"retry", "reindex", "source"}:
            if args.command == "retry":
                options = JobInput(kind="retry", retry_of=args.job, item_ids=args.items)
            elif args.command == "source":
                options = JobInput(
                    kind="ingest_dataset", source_id=args.source, target_index_id=args.index
                )
            else:
                options = JobInput(
                    kind="reindex", target_index_id=args.index, image_ids=args.images
                )
            output(await submit_job(services, options, args.key))
        elif args.command == "verify":
            report = await verify_index(services, args.index, args.repair, args.mark_ready)
            output(report)
            if report["status"] != "pass":
                return 1
        return 0
    finally:
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("register")
    p.add_argument("--version", required=True)
    sub.add_parser("model")
    sub.add_parser("orphans")
    p = sub.add_parser("worker")
    p.add_argument("--index", type=UUID, required=True)
    p.add_argument("--once", action="store_true")
    for name in ["image", "dataset"]:
        p = sub.add_parser(name)
        p.add_argument("--input", required=True)
        p.add_argument("--index", type=UUID, required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--license", required=True)
        p.add_argument("--rights-ref", required=True)
    p = sub.add_parser("job")
    p.add_argument("--job", type=UUID, required=True)
    p = sub.add_parser("retry")
    p.add_argument("--job", type=UUID, required=True)
    p.add_argument("--items", nargs="+", type=UUID, required=True)
    p.add_argument("--key", required=True)
    for name in ["source", "reindex"]:
        p = sub.add_parser(name)
        p.add_argument("--index", type=UUID, required=True)
        p.add_argument("--key", required=True)
        if name == "source":
            p.add_argument("--source", type=UUID, required=True)
        else:
            p.add_argument("--images", nargs="+", type=UUID, required=True)
    p = sub.add_parser("verify")
    p.add_argument("--index", type=UUID, required=True)
    p.add_argument("--repair", action="store_true")
    p.add_argument("--mark-ready", action="store_true")
    try:
        return asyncio.run(execute(parser.parse_args()))
    except Exception as exc:
        output({"status": "failed", "error_code": getattr(exc, "code", type(exc).__name__)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
