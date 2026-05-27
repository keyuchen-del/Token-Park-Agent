"""API 路由集合."""
from fastapi import APIRouter

from tpagent.routes.write import router as write_router

# 总 router
api_router = APIRouter(prefix="/api")
api_router.include_router(write_router)
