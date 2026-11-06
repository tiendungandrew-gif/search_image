from qdrant_client import AsyncQdrantClient

from app.core.config import Settings


class QdrantConnection:
    def __init__(self, settings: Settings):
        self.client = AsyncQdrantClient(
            url=str(settings.qdrant_url),
            api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
            timeout=settings.dependency_timeout_seconds,
            check_compatibility=False,
        )

    async def probe(self) -> None:
        await self.client.info()

    async def close(self) -> None:
        await self.client.close()
