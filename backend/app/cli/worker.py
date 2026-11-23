"""Worker thường trực: idle khi chưa có dataset, lazy-load model, heartbeat an toàn."""

import argparse
import asyncio
import json
import os
import signal
import time
from pathlib import Path

HEARTBEAT = Path("/run/app/worker.json")


def health(path=HEARTBEAT):
    value = json.loads(path.read_text())
    fresh = time.time() - value["heartbeat_unix"] < 30
    return fresh and value["state"] in {"idle", "running", "stopping"}


async def pending_index(services, manifest=None, excluded=()):
    """Pick work for the installed encoder; future leases/retries cannot block fresh jobs."""
    from datetime import timedelta

    from sqlalchemy import case, or_, select

    from app.db.models import EmbeddingModel, SearchIndex
    from app.db.models.indexing import JobItem
    from app.services.indexing.jobs import now

    statement = (
        select(JobItem.index_id)
        .join(SearchIndex, SearchIndex.id == JobItem.index_id)
        .join(EmbeddingModel, EmbeddingModel.id == SearchIndex.model_id)
        .where(
            SearchIndex.status.in_(["building", "ready"]),
            or_(
                JobItem.status == "queued",
                (JobItem.status == "retry_wait")
                & or_(JobItem.next_attempt_at.is_(None), JobItem.next_attempt_at <= now()),
                (JobItem.status == "processing") & (JobItem.lease_expires_at < now()),
                (JobItem.status == "awaiting_input")
                & (JobItem.created_at < now() - timedelta(seconds=3)),
            ),
            JobItem.index_id.not_in(excluded),
        )
        .order_by(case((JobItem.status == "queued", 0), else_=1), JobItem.created_at, JobItem.id)
        .limit(1)
    )
    if manifest is not None:
        statement = statement.where(EmbeddingModel.manifest_sha256 == manifest)
    async with services.database.sessions() as session:
        return await session.scalar(statement)


async def serve():
    from app.core.config import Settings
    from app.core.container import Services
    from app.core.logging import configure_logging
    from app.services.embeddings.clip_encoder import ClipEncoder
    from app.services.indexing.worker import Worker

    settings = Settings()
    configure_logging(settings.log_level)
    services = Services(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(name, stop.set)
    state = {"state": "idle", "pid": os.getpid(), "index_id": None, "error_category": None}

    async def heartbeat():
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        while not stop.is_set():
            temporary = HEARTBEAT.with_suffix(".tmp")
            temporary.write_text(json.dumps({**state, "heartbeat_unix": time.time()}))
            temporary.replace(HEARTBEAT)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except TimeoutError:
                pass

    monitor = asyncio.create_task(heartbeat())
    encoder = None
    cooldown = {}
    try:
        while not stop.is_set():
            identity = None
            try:
                cooldown = {
                    key: until for key, until in cooldown.items() if until > time.monotonic()
                }
                identity = await pending_index(
                    services, encoder.manifest_sha256 if encoder else None, tuple(cooldown)
                )
                if identity is not None and encoder is None:
                    encoder = await asyncio.to_thread(ClipEncoder, settings)
                    identity = await pending_index(
                        services, encoder.manifest_sha256, tuple(cooldown)
                    )
                if identity is not None:
                    state.update(state="running", index_id=str(identity), error_category=None)
                    await Worker(services, encoder, identity).run(once=True)
                state.update(state="idle", index_id=None, error_category=None)
                delay = 2
            except Exception as error:
                if identity is not None:
                    cooldown[identity] = time.monotonic() + 30
                state.update(
                    state="blocked",
                    error_category="MODEL_NOT_INSTALLED"
                    if isinstance(error, (FileNotFoundError, ImportError))
                    else "WORKER_OPERATION_FAILED",
                )
                delay = 15
            try:
                await asyncio.wait_for(stop.wait(), timeout=delay)
            except TimeoutError:
                pass
    finally:
        stop.set()
        state["state"] = "stopping"
        await monitor
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health", action="store_true")
    args = parser.parse_args()
    if args.health:
        try:
            raise SystemExit(0 if health() else 1)
        except (OSError, ValueError, KeyError):
            raise SystemExit(1) from None
    asyncio.run(serve())


if __name__ == "__main__":
    main()
