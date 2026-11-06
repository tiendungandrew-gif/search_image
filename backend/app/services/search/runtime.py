import asyncio
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from PIL import Image

from app.core.exceptions import AppError
from app.services.embeddings.query_encoder import ClipQueryEncoder
from app.services.search.query_decoder import QueryDecoder
from app.services.search.registry import SearchRegistry


class SearchRuntime:
    def __init__(self, services):
        self.services = services
        self.settings = services.settings
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="search-inference")
        self.slot = asyncio.Semaphore(1)
        self.waiting = 0
        self.available = False
        self.failure_code = "NOT_READY"
        self.encoder = None
        self.decoder = QueryDecoder(self.settings)

    async def compute(self, operation):
        if self.waiting >= self.settings.search_queue_capacity:
            raise AppError(503, "INFERENCE_BUSY", "Hàng chờ inference đã đầy", retryable=True)
        self.waiting += 1
        try:
            await asyncio.wait_for(
                self.slot.acquire(), timeout=self.settings.search_queue_wait_seconds
            )
        except TimeoutError:
            raise AppError(503, "INFERENCE_BUSY", "Inference đang bận", retryable=True) from None
        finally:
            self.waiting -= 1
        try:
            future = asyncio.get_running_loop().run_in_executor(self.executor, operation)
        except BaseException:
            self.slot.release()
            raise

        def release(completed):
            self.slot.release()
            if not completed.cancelled():
                completed.exception()

        future.add_done_callback(release)
        return await asyncio.shield(future)

    async def initialize(self, index_id=None):
        start = perf_counter()
        self.encoder = await self.compute(lambda: ClipQueryEncoder(self.settings))
        self.registry = SearchRegistry(self.services, self.encoder)
        await self.registry.load(index_id)

        def warmup():
            self.encoder.encode_text(["a photograph"])
            with Image.new("RGB", (224, 224)) as image:
                self.encoder.encode_images([image])

        await self.compute(warmup)
        await self.compute(self.decoder.start)
        self.initialization_ms = (perf_counter() - start) * 1000
        self.available = True

    async def close(self):
        self.available = False
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=True)
        await asyncio.to_thread(self.decoder.stop)
        self.encoder = None
        self.registry = None
