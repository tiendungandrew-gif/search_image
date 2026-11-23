import asyncio
import json
import os
import sys
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models.indexing import JobItem
from app.schemas.ingestion import ImageMetadataInput
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, job_response, now
from app.services.indexing.worker import Worker
from tests.fixtures.synthetic import SyntheticEncoder, image_bytes

pytestmark = pytest.mark.integration


async def test_actual_worker_process_death_reclaims_durable_job(qa_resources):
    encoder = SyntheticEncoder()
    index, _ = await qa_resources.index(encoder)
    _, receipt = await ingest(
        qa_resources.services,
        image_bytes(),
        ImageMetadataInput(
            source_dataset="qa_process_fixture", license="generated", rights_ref="fixture://process"
        ),
        "qa-process-death",
        index.id,
    )
    env = {
        **os.environ,
        "DATABASE_URL": qa_resources.settings.database_url.get_secret_value(),
        "MINIO_BUCKET": qa_resources.settings.minio_bucket,
        "QA_TEST_INDEX_ID": str(index.id),
    }
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "tests.fixtures.claim_then_wait",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        line = await asyncio.wait_for(process.stdout.readline(), 15)
        assert json.loads(line)["claimed"] == 1
        process.kill()  # Only the child test worker whose PID was returned above.
        await asyncio.wait_for(process.wait(), 5)
        async with qa_resources.services.database.sessions() as session, session.begin():
            item = await session.scalar(
                select(JobItem).where(JobItem.job_id == UUID(receipt["job_id"]))
            )
            assert item.status == "processing" and item.attempt_count == 1
            item.lease_expires_at = now() - timedelta(seconds=1)
        await Worker(qa_resources.services, encoder, index.id).run(once=True)
        job = await job_response(qa_resources.services, UUID(receipt["job_id"]))
        assert job["status"] == "succeeded" and job["items"][0]["attempt_count"] == 2
        assert (await verify_index(qa_resources.services, index.id))["status"] == "pass"
    finally:
        if process.returncode is None:
            process.kill()
            await asyncio.wait_for(process.wait(), 5)
