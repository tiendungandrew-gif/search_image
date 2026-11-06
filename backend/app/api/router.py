from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.images import router as images_router
from app.api.v1.indexing import router as indexing_router
from app.api.v1.rag import router as rag_router
from app.api.v1.search import router as search_router
from app.api.v1.system import router as system_router
from app.schemas.errors import ErrorEnvelope

router = APIRouter(responses={status: {"model": ErrorEnvelope} for status in (401, 422, 500, 504)})
router.include_router(health_router)
router.include_router(system_router)
router.include_router(images_router)
router.include_router(indexing_router)
router.include_router(search_router)
router.include_router(rag_router)
