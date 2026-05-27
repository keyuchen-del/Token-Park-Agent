"""GET /api/sessions — session 列表。"""

from fastapi import APIRouter, HTTPException

from tpagent.models import SessionListResponseModel, SessionModel
from tpagent.storage.session import SessionStage, get_session, list_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_model(s) -> SessionModel:
    """ArticleSession ORM → SessionModel."""
    return SessionModel(
        id=s.id,
        topic=s.topic,
        angle=s.angle,
        material=s.material,
        stage=s.stage.value if hasattr(s.stage, "value") else str(s.stage),
        can_publish=s.can_publish,
        grep_hits=s.grep_hits,
        article_path=s.article_path,
        ops_path=s.ops_path,
        images_dir=s.images_dir,
        total_input_tokens=s.total_input_tokens,
        total_output_tokens=s.total_output_tokens,
        estimated_cost_usd=s.estimated_cost_usd,
        created_at=s.created_at,
        updated_at=s.updated_at,
        published_at=s.published_at,
    )


@router.get("", response_model=SessionListResponseModel)
async def list_all_sessions(
    limit: int = 50,
    stage: str | None = None,
) -> SessionListResponseModel:
    """列出历史 sessions（按时间倒序）。"""
    stage_filter = None
    if stage:
        try:
            stage_filter = SessionStage(stage)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"未知阶段 '{stage}'。可选: {', '.join(s.value for s in SessionStage)}",
            ) from e

    sessions = list_sessions(limit=limit, stage=stage_filter)
    return SessionListResponseModel(
        sessions=[_to_model(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionModel)
async def get_single_session(session_id: int) -> SessionModel:
    """查单个 session 详情。"""
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"session {session_id} 不存在")
    return _to_model(s)
