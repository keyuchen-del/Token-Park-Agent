"""API 路由集合."""

from fastapi import APIRouter

from tpagent.routes.images import router as images_router
from tpagent.routes.ops import router as ops_router
from tpagent.routes.sessions import router as sessions_router
from tpagent.routes.topics import router as topics_router
from tpagent.routes.write import router as write_router

# 总 router
api_router = APIRouter(prefix="/api")
api_router.include_router(write_router)
api_router.include_router(topics_router)
api_router.include_router(ops_router)
api_router.include_router(images_router)
api_router.include_router(sessions_router)
