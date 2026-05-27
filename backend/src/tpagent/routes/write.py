"""POST /api/write — 写文章 + grep 校验."""
from fastapi import APIRouter, HTTPException

from tpagent.agents import ArticleWriter, WriteRequest
from tpagent.grep import scan_file
from tpagent.models import (
    GrepHitModel,
    GrepReportModel,
    WriteRequestModel,
    WriteResponseModel,
)
from tpagent.storage import save_article
from tpagent.storage.session import (
    SessionStage,
    create_session,
    estimate_cost,
    update_session,
)

router = APIRouter(tags=["write"])


@router.post("/write", response_model=WriteResponseModel)
async def write_article(req: WriteRequestModel) -> WriteResponseModel:
    """写一篇 Token 公园风格的公众号长文，返回正文 + grep 校验结果。

    流程：
    1. 调 Claude API 写文章（带 prompt caching）
    2. 保存到 sessions/{M.D}/{YYYY-MM-DD}-{slug}.md
    3. 跑 6 项 grep 扫描
    4. 返回正文 + 路径 + grep 报告
    """
    # 先创建 session（无论后续成功失败都有记录）
    article_session = create_session(
        topic=req.topic,
        angle=req.angle,
        material=req.material,
    )

    try:
        writer = ArticleWriter()
        write_req = WriteRequest(
            topic=req.topic,
            material=req.material,
            angle=req.angle,
        )
        result = writer.write(write_req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写作失败: {e}") from e

    # 保存到文件
    article_path = save_article(result.article_markdown, req.topic)

    # 跑 grep 扫描
    report = scan_file(article_path)

    # 更新 session
    update_session(
        article_session.id,  # type: ignore[arg-type]
        stage=SessionStage.article,
        article_path=str(article_path),
        can_publish=report.can_publish,
        grep_hits=report.total_hits,
        total_input_tokens=result.input_tokens,
        total_output_tokens=result.output_tokens,
        total_cache_read_tokens=result.cache_read_tokens,
        estimated_cost_usd=estimate_cost(
            result.input_tokens,
            result.output_tokens,
            result.cache_read_tokens,
            result.cache_creation_tokens,
        ),
    )

    return WriteResponseModel(
        article_markdown=result.article_markdown,
        article_path=str(article_path),
        char_count=len(result.article_markdown),
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
