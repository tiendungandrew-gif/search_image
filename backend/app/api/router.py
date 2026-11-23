from fastapi import APIRouter

from app.api.v1.admin_accounts import router as admin_accounts_router
from app.api.v1.admin_content import router as admin_content_router
from app.api.v1.agent import router as agent_router
from app.api.v1.authentication import router as authentication_router
from app.api.v1.comments import router as comments_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.images import router as images_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.public import router as public_router
from app.api.v1.indexing import router as indexing_router
from app.api.v1.rag import router as rag_router
from app.api.v1.search import router as search_router
from app.api.v1.system import router as system_router
from app.schemas.errors import ErrorEnvelope

router = APIRouter(responses={status: {"model": ErrorEnvelope} for status in (401, 422, 500, 504)})
router.include_router(health_router)
router.include_router(authentication_router)
router.include_router(chat_router)
router.include_router(profiles_router)
router.include_router(comments_router)
router.include_router(admin_accounts_router)
router.include_router(admin_content_router)
router.include_router(system_router)
router.include_router(images_router)
router.include_router(public_router)
router.include_router(indexing_router)
router.include_router(search_router)
router.include_router(rag_router)
router.include_router(agent_router)
