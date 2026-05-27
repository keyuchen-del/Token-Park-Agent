"""POST /api/ops — 基于已有文章生成图运营合一 ops 文档。"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from tpagent.agents.ops_writer import OpsWriter, OpsWriteRequest
from tpagent.grep import scan_file
from tpagent.models import (
    GrepHitModel,
    GrepReportModel,
    OpsRequestModel,
    OpsResponseModel,
)
from tpagent.storage import save_ops
from tpagent.storage.session import SessionStage, update_session

router = APIRouter(tags=["ops"])


@router.post("/ops", response_model=OpsResponseModel)
async def generate_ops(req: OpsRequestModel) -> OpsResponseModel:
    """基于已有文章正文，生成 ops 配套文档。"""
    article_path = Path(req.article_path)
    if not article_path.exists():
        raise HTTPException(status_code=404, detail=f"文章不存在: {req.article_path}")

    article_md = article_path.read_text(encoding="utf-8")

    try:
        writer = OpsWriter()
        result = writer.write(OpsWriteRequest(article_markdown=article_md, topic=req.topic))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ops 生成失败: {e}") from e

    ops_path = save_ops(result.ops_markdown, req.topic)

    # 跑 grep
    report = scan_file(ops_path)

    # 更新 session
    if req.session_id:
        update_session(
            req.session_id,
            stage=SessionStage.ops,
            ops_path=str(ops_path),
        )

    return OpsResponseModel(
        ops_markdown=result.ops_markdown,
        ops_path=str(ops_path),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cache_read_tokens=result.cache_read_tokens,
        cache_creation_tokens=result.cache_creation_tokens,
        grep_report=GrepReportModel(
            can_publish=report.can_publish,
            total_hits=report.total_hits,
            rule_summary=report.rule_summary,
            hits=[
                GrepHitModel(
                    rule_id=h.rule_id,
                    rule_name=h.rule_name,
                    line_no=h.line_no,
                    line_content=h.line_content,
                    matched_text=h.matched_text,
                    is_exception=h.is_exception,
                )
                for h in report.hits
            ],
            exceptions=[
                GrepHitModel(
                    rule_id=h.rule_id,
                    rule_name=h.rule_name,
                    line_no=h.line_no,
                    line_content=h.line_content,
                    matched_text=h.matched_text,
                    is_exception=h.is_exception,
                )
                for h in report.exceptions
            ],
        ),
    )
