"""Bootstrap và inventory vận hành; không xóa hoặc thay active index."""

import argparse
import ast
import asyncio
import json
import re
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from minio.error import S3Error
from pydantic import ValidationError
from sqlalchemy import func, select, text

from alembic import command
from app.core.config import Settings
from app.core.container import Services
from app.db.models import Image, SearchIndex
from app.db.models.indexing import ActiveSearchIndex, ImageEmbedding, ImageObject, JobItem
from app.schemas.ingestion import JobInput
from app.services.indexing.consistency import verify_index
from app.services.indexing.submission import submit_job


def validate_pending_migrations(paths):
    for path in paths:
        tree = ast.parse(Path(path).read_text())
        upgrade = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
        )
        for node in ast.walk(upgrade):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("drop_"):
                    raise ValueError("MIGRATION_REQUIRES_MANUAL_REVIEW")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.search(r"\b(DROP|TRUNCATE|DELETE\s+FROM)\b", node.value, re.I):
                    raise ValueError("MIGRATION_REQUIRES_MANUAL_REVIEW")


async def bootstrap(services):
    await services.database.probe()
    await services.qdrant.probe()
    config = Config("backend/alembic.ini")
    script = ScriptDirectory.from_config(config)
    async with services.database.engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_lock(731208121)"))
        try:
            exists = await connection.scalar(text("SELECT to_regclass('public.alembic_version')"))
            revision = (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                if exists
                else None
            )
            pending = list(script.iterate_revisions("head", revision or "base"))
            validate_pending_migrations([item.path for item in pending])
            await asyncio.to_thread(command.upgrade, config, "head")

            def bucket():
                if not services.minio.client.bucket_exists(services.minio.bucket):
                    try:
                        services.minio.client.make_bucket(services.minio.bucket)
                    except S3Error as error:
                        if error.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                            raise

            await services.minio.run(bucket)
            await services.minio.probe()
            return {
                "status": "ready",
                "migration_head": script.get_current_head(),
                "migrations_applied": len(pending),
                "bucket": "private",
                "collection_initialization": "deferred_until_model_registration",
            }
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(731208121)"))


async def inventory(services):
    dependencies = await services.readiness()
    async with services.database.sessions() as session:
        counts = {}
        for name, model in [
            ("images", Image),
            ("objects_receipts", ImageObject),
            ("ready_embeddings", ImageEmbedding),
        ]:
            query = select(func.count()).select_from(model)
            if model is ImageEmbedding:
                query = query.where(ImageEmbedding.status == "ready")
            counts[name] = await session.scalar(query)
        jobs = dict(
            (await session.execute(select(JobItem.status, func.count()).group_by(JobItem.status)))
            .tuples()
            .all()
        )
        indexes = [
            {"id": str(row.id), "status": row.status, "collection": row.collection_name}
            for row in (await session.scalars(select(SearchIndex).order_by(SearchIndex.id))).all()
        ]
        pointer = await session.get(ActiveSearchIndex, "default")
        active = (
            {"index_id": str(pointer.index_id), "generation": pointer.generation}
            if pointer
            else None
        )
    collections = []
    for collection in (await services.qdrant.client.get_collections()).collections:
        count = await services.qdrant.client.count(collection.name, exact=True)
        collections.append({"name": collection.name, "points": count.count})
    object_count = await services.minio.run(
        lambda: sum(
            1 for _ in services.minio.client.list_objects(services.minio.bucket, recursive=True)
        )
    )
    cache = Path(services.settings.embedding_cache_dir)
    return {
        "dependencies": dependencies,
        "dataset_state": "EMPTY_DATASET" if counts["images"] == 0 else "DATA_PRESENT",
        "counts": counts,
        "jobs": jobs,
        "indexes": indexes,
        "active": active,
        "collections": collections,
        "stored_objects": object_count,
        "model_artifacts": "present_unverified"
        if (cache / "download.json").is_file()
        else "not_installed",
    }


async def execute(args):
    services = Services(Settings())
    try:
        if args.command == "restore-guard":
            async with services.database.engine.connect() as connection:
                tables = await connection.scalar(
                    text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                )
            collections = (await services.qdrant.client.get_collections()).collections
            buckets = await services.minio.run(services.minio.client.list_buckets)
            objects = await services.minio.run(
                lambda: sum(
                    1
                    for bucket in buckets
                    for _ in services.minio.client.list_objects(bucket.name, recursive=True)
                )
            )
            result = {"empty": tables == 0 and not collections and objects == 0}
            if not result["empty"]:
                raise ValueError("RESTORE_REQUIRES_EMPTY_DESTINATION")
        elif args.command == "bootstrap":
            result = await bootstrap(services)
        elif args.command == "inventory":
            result = await inventory(services)
        elif args.command == "carry-forward":
            async with services.database.sessions() as session:
                pointer = await session.get(ActiveSearchIndex, "default")
                identities = []
                if pointer and pointer.index_id != args.index:
                    identities = list(
                        (
                            await session.scalars(
                                select(ImageEmbedding.image_id)
                                .join(Image, Image.id == ImageEmbedding.image_id)
                                .where(
                                    ImageEmbedding.index_id == pointer.index_id,
                                    ImageEmbedding.status == "ready",
                                    Image.status == "available",
                                )
                                .order_by(ImageEmbedding.image_id)
                            )
                        ).all()
                    )
            jobs = []
            for offset in range(0, len(identities), 500):
                batch = identities[offset : offset + 500]
                jobs.append(
                    await submit_job(
                        services,
                        JobInput(kind="reindex", target_index_id=args.index, image_ids=batch),
                        f"carry-{args.index}-{offset}",
                    )
                )
            result = {"inherited_images": len(identities), "jobs": jobs}
        elif args.command == "index-status":
            async with services.database.sessions() as session:
                result = {
                    "counts": dict(
                        (
                            await session.execute(
                                select(JobItem.status, func.count())
                                .where(JobItem.index_id == args.index)
                                .group_by(JobItem.status)
                            )
                        )
                        .tuples()
                        .all()
                    )
                }
        elif args.command == "verify-all":
            async with services.database.sessions() as session:
                ids = list((await session.scalars(select(SearchIndex.id))).all())
            reports = [await verify_index(services, identity) for identity in ids]
            result = {"status": "pass", "indexes": reports}
            if any(item["status"] != "pass" for item in reports):
                result["status"] = "incomplete"
        else:
            from app.services.embeddings.query_encoder import ClipQueryEncoder

            encoder = await asyncio.to_thread(ClipQueryEncoder, services.settings)
            await asyncio.to_thread(encoder.encode_text, ["a cup of coffee", "một tách cà phê"])
            result = {
                "status": "ready",
                "manifest_sha256": encoder.manifest_sha256,
                "text_manifest_sha256": encoder.text_manifest_sha256,
                "dimension": encoder.dimension,
                "device": encoder.device,
            }
        print(json.dumps(result, ensure_ascii=False))
        return int(result.get("status") == "incomplete")
    finally:
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "bootstrap",
            "inventory",
            "verify-all",
            "model-verify",
            "index-status",
            "restore-guard",
            "carry-forward",
        ],
    )
    parser.add_argument("--index", type=UUID)
    args = parser.parse_args()
    if args.command in {"index-status", "carry-forward"} and args.index is None:
        parser.error("This command requires --index")
    try:
        raise SystemExit(asyncio.run(execute(args)))
    except Exception as error:
        detail = {"status": "failed", "error_type": type(error).__name__}
        if isinstance(error, ValidationError):
            detail["invalid_fields"] = [".".join(map(str, item["loc"])) for item in error.errors()]
        elif re.fullmatch(r"[A-Z][A-Z0-9_]+", str(error)):
            detail["error_code"] = str(error)
        print(json.dumps(detail))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
