import asyncio
import logging
from typing import Literal, Protocol

from app.core.config import Settings
from app.db.session import Database
from app.integrations.minio import MinioStorage
from app.integrations.qdrant import QdrantConnection

logger = logging.getLogger("app.dependencies")
DependencyStatus = Literal["healthy", "unhealthy", "timeout"]


class Probe(Protocol):
    async def probe(self) -> None: ...
    async def close(self) -> None: ...


class Services:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings)
        self.qdrant = QdrantConnection(settings)
        self.minio = MinioStorage(settings)

    async def readiness(self) -> dict[str, DependencyStatus]:
        async def check(name: str, service: Probe) -> tuple[str, DependencyStatus]:
            try:
                async with asyncio.timeout(self.settings.dependency_timeout_seconds):
                    await service.probe()
                return name, "healthy"
            except TimeoutError:
                logger.warning("dependency_timeout", extra={"dependency": name})
                return name, "timeout"
            except Exception:
                logger.warning("dependency_unavailable", extra={"dependency": name})
                return name, "unhealthy"

        return dict(
            await asyncio.gather(
                check("postgresql", self.database),
                check("qdrant", self.qdrant),
                check("minio", self.minio),
            )
        )

    async def initialize(self) -> None:
        if self.settings.minio_auto_create_bucket:
            try:
                async with asyncio.timeout(self.settings.dependency_timeout_seconds):
                    await self.minio.probe()
            except Exception:
                # Process vẫn live; readiness phản ánh dịch vụ chưa sẵn sàng.
                logger.warning("bucket_initialization_pending", extra={"dependency": "minio"})

    async def close(self) -> None:
        outcomes = await asyncio.gather(
            self.database.close(), self.qdrant.close(), self.minio.close(), return_exceptions=True
        )
        if any(isinstance(value, BaseException) for value in outcomes):
            logger.warning("dependency_shutdown_failed")
