import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest
from minio.error import S3Error

from app.core.container import Services
from app.integrations.minio import MinioStorage


async def test_probes_are_bounded_and_isolated(settings):
    async def slow():
        await asyncio.sleep(0.3)

    services = Services.__new__(Services)
    services.settings = settings.model_copy(update={"dependency_timeout_seconds": 0.02})
    services.database = Mock(probe=AsyncMock())
    services.qdrant = Mock(probe=AsyncMock(side_effect=slow))
    services.minio = Mock(probe=AsyncMock(side_effect=RuntimeError("PRIVATE_ERROR")))
    assert await services.readiness() == {
        "postgresql": "healthy",
        "qdrant": "timeout",
        "minio": "unhealthy",
    }


async def test_shutdown_closes_all_adapters_even_when_one_fails(settings):
    services = Services.__new__(Services)
    services.database = Mock(close=AsyncMock(side_effect=RuntimeError()))
    services.qdrant = Mock(close=AsyncMock())
    services.minio = Mock(close=AsyncMock())
    await services.close()
    services.qdrant.close.assert_awaited_once()
    services.minio.close.assert_awaited_once()


async def test_minio_creates_private_bucket_without_policy_mutation(settings):
    settings.minio_auto_create_bucket = True
    storage = MinioStorage(settings)
    storage.client = Mock()
    storage.client.bucket_exists.return_value = False
    storage.client.get_bucket_policy.side_effect = S3Error(
        response=None,
        code="NoSuchBucketPolicy",
        message="missing",
        resource="resource",
        request_id="request",
        host_id="host",
    )
    try:
        await storage.probe()
        storage.client.make_bucket.assert_called_once_with(settings.minio_bucket)
        storage.client.set_bucket_policy.assert_not_called()
    finally:
        await storage.close()


async def test_existing_public_bucket_is_rejected_without_mutating_policy(settings):
    storage = MinioStorage(settings)
    storage.client = Mock()
    storage.client.bucket_exists.return_value = True
    storage.client.get_bucket_policy.return_value = json.dumps(
        {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": "s3:GetObject",
                }
            ]
        }
    )
    try:
        with pytest.raises(RuntimeError, match="bucket_public_policy_rejected"):
            await storage.probe()
        storage.client.set_bucket_policy.assert_not_called()
    finally:
        await storage.close()
