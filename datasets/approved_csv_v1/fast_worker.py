"""Temporary bulk-import scheduler; uses unchanged decoder, encoder and receipts."""
import asyncio
import ctypes
import hashlib
import inspect
import os
import textwrap

os.environ.update(EMBEDDING_BATCH_SIZE='16', IMAGE_DECODE_TIMEOUT_SECONDS='15', DATABASE_POOL_SIZE='16', DATABASE_MAX_OVERFLOW='16', DATABASE_POOL_TIMEOUT_SECONDS='10')

import app.services.indexing.worker as module
from decoder_pool import install
install(1,clip_preprocess=True)

original_process = module.Worker.process
original_get = module.get_original
original_prepare = module.prepared_image
cached_bytes = {}
cached_images = {}

async def cached_get(services, image):
    return cached_bytes.get(image.id) or await original_get(services, image)

def cached_prepare(data, settings):
    key = hashlib.sha256(data).hexdigest()
    image = cached_images.pop(key, None)
    return image if image is not None else original_prepare(data, settings)

# Stage writes and per-image completion transactions are independent within a claim.
source = textwrap.dedent(inspect.getsource(original_process))
for stage in ('embed', 'vector'):
    before = f'        for item in valid:\n            await self.stage(item, "{stage}")'
    after = f'        await asyncio.gather(*(self.stage(item, "{stage}") for item in valid))'
    assert before in source
    source = source.replace(before, after)
namespace = dict(module.__dict__)
exec(compile(source, '<approved-csv-bulk-scheduler>', 'exec'), namespace)
scheduled_process = namespace['process']

async def process(self, items):
    semaphore = asyncio.Semaphore(1)
    async def prefetch(item):
        async with semaphore:
            try:
                async with self.services.database.sessions() as session:
                    image = await session.get(module.Image, item.image_id)
                raw = await original_get(self.services, image)
                prepared = await asyncio.to_thread(original_prepare, raw, self.settings)
                cached_bytes[image.id] = raw
                cached_images[hashlib.sha256(raw).hexdigest()] = prepared
            except Exception:
                # The unchanged processing path records or retries the precise error.
                pass
    task = asyncio.create_task(self.heartbeat(items))
    try:
        await asyncio.gather(*(prefetch(item) for item in items))
        await scheduled_process(self, items)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        cached_bytes.clear()
        for image in cached_images.values():
            image.close()
        cached_images.clear()
        getattr(ctypes.CDLL(None),'malloc_trim',lambda _:0)(0)

# scheduled_process resolves functions from its own global namespace.
namespace['get_original'] = cached_get
namespace['prepared_image'] = cached_prepare
module.Worker.process = process

from app.cli.worker import main
main()
