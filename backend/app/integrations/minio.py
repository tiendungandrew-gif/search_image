import asyncio
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

import urllib3
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings

T = TypeVar("T")


class MinioStorage:
    def __init__(self, settings: Settings):
        self.bucket = settings.minio_bucket
        self.auto_create = settings.minio_auto_create_bucket
        self.http = urllib3.PoolManager(
            timeout=urllib3.Timeout(
                connect=settings.dependency_timeout_seconds,
                read=settings.dependency_timeout_seconds,
            ),
            retries=False,
            maxsize=2,
        )
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=settings.minio_secure,
            http_client=self.http,
        )
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="minio")
        self._slots = asyncio.Semaphore(2)

    async def run(self, operation: Callable[[], T]) -> T:
        # Giữ slot đến khi blocking I/O thực sự xong, kể cả caller đã timeout/cancel.
        await self._slots.acquire()
        try:
            future = asyncio.get_running_loop().run_in_executor(self._executor, operation)
        except BaseException:
            self._slots.release()
            raise

        def release_slot(completed):
            self._slots.release()
            if not completed.cancelled():
                completed.exception()  # Consume lỗi của I/O đã bị caller cancel/timeout.

        future.add_done_callback(release_slot)
        return await asyncio.shield(future)

    def _verify_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            if not self.auto_create:
                raise RuntimeError("bucket_missing")
            try:
                self.client.make_bucket(self.bucket)
            except S3Error as exc:
                if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                    raise
        try:
            policy = json.loads(self.client.get_bucket_policy(self.bucket))
        except S3Error as exc:
            if exc.code == "NoSuchBucketPolicy":
                return  # Bucket không có anonymous policy: private mặc định.
            raise
        statements = policy.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            principal = statement.get("Principal")
            principals = principal.values() if isinstance(principal, dict) else [principal]
            anonymous = any(p == "*" or (isinstance(p, list) and "*" in p) for p in principals)
            if statement.get("Effect") == "Allow" and anonymous:
                raise RuntimeError("bucket_public_policy_rejected")

    async def probe(self) -> None:
        await self.run(self._verify_bucket)

    async def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.http.clear()
