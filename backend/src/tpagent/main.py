"""FastAPI 应用入口."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tpagent import __version__
from tpagent.routes import api_router
from tpagent.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动 / 关闭事件。"""
    settings = get_settings()
    settings.ensure_dirs()
    print(f"📦 token-park-agent v{__version__}")
    print(f"📂 配置目录: {settings.config_dir.resolve()}")
    print(f"📂 会话目录: {settings.sessions_dir.resolve()}")
    yield


app = FastAPI(
    title="token-park-agent",
    version=__version__,
    description="Token 公园内容生产 Agent (V0.1 MVP)",
    lifespan=lifespan,
)

# CORS（开发期允许所有来源，部署时收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    """健康检查。"""
    return {
        "name": "token-park-agent",
        "version": __version__,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """liveness probe."""
    return {"status": "ok"}
