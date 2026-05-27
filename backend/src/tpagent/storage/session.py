"""SQLite session 持久化。"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select

from tpagent.settings import get_settings


class SessionStage(StrEnum):
    """四阶段状态机。"""

    topic = "topic"  # 选题待审
    article = "article"  # 初稿待审
    images = "images"  # 图片待选
    ops = "ops"  # ops 文档已生成
    ready = "ready"  # 上传待审
    published = "published"  # 已发布


class ArticleSession(SQLModel, table=True):
    """一篇文章的完整 session 记录。"""

    __tablename__ = "article_sessions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    topic: str = Field(description="选题")
    angle: str | None = Field(default=None, description="切入角度")
    material: str | None = Field(default=None, description="素材链接")

    # 状态
    stage: SessionStage = Field(default=SessionStage.topic)
    can_publish: bool = Field(default=False)
    grep_hits: int = Field(default=0)

    # 产物路径
    article_path: str | None = None
    ops_path: str | None = None
    images_dir: str | None = None

    # 资源消耗
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_cache_read_tokens: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    published_at: datetime | None = None


_engine = None


def get_engine():
    """获取 SQLite 引擎单例。"""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(_engine)
    return _engine


def create_session(
    topic: str,
    angle: str | None = None,
    material: str | None = None,
) -> ArticleSession:
    """创建一个新的 session。"""
    article_session = ArticleSession(
        topic=topic,
        angle=angle,
        material=material,
    )
    with Session(get_engine()) as db:
        db.add(article_session)
        db.commit()
        db.refresh(article_session)
    return article_session


def update_session(
    session_id: int,
    **updates,
) -> ArticleSession | None:
    """更新某个 session。"""
    with Session(get_engine()) as db:
        article_session = db.get(ArticleSession, session_id)
        if not article_session:
            return None
        for key, value in updates.items():
            if hasattr(article_session, key):
                setattr(article_session, key, value)
        article_session.updated_at = datetime.now()
        db.add(article_session)
        db.commit()
        db.refresh(article_session)
    return article_session


def list_sessions(
    limit: int = 50,
    stage: SessionStage | None = None,
) -> list[ArticleSession]:
    """列出所有历史 session（按时间倒序）。"""
    with Session(get_engine()) as db:
        statement = select(ArticleSession).order_by(ArticleSession.created_at.desc())  # type: ignore[attr-defined]
        if stage:
            statement = statement.where(ArticleSession.stage == stage)
        statement = statement.limit(limit)
        return list(db.exec(statement).all())


def get_session(session_id: int) -> ArticleSession | None:
    """按 ID 查 session。"""
    with Session(get_engine()) as db:
        return db.get(ArticleSession, session_id)


# === 成本估算（基于 claude-sonnet-4-5 定价）===
COST_PER_M_INPUT_TOKENS = 3.0
COST_PER_M_OUTPUT_TOKENS = 15.0
COST_PER_M_CACHE_READ_TOKENS = 0.30
COST_PER_M_CACHE_CREATION_TOKENS = 3.75


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """估算单次调用的美金成本。"""
    return round(
        input_tokens / 1_000_000 * COST_PER_M_INPUT_TOKENS
        + output_tokens / 1_000_000 * COST_PER_M_OUTPUT_TOKENS
        + cache_read_tokens / 1_000_000 * COST_PER_M_CACHE_READ_TOKENS
        + cache_creation_tokens / 1_000_000 * COST_PER_M_CACHE_CREATION_TOKENS,
        4,
    )
