"""POST /api/topics — 拉热点 + 整理候选清单。"""

from fastapi import APIRouter, HTTPException

from tpagent.agents.topic_researcher import TopicResearcher, TopicResearchRequest
from tpagent.models import TopicsRequestModel, TopicsResponseModel

router = APIRouter(tags=["topics"])


@router.post("/topics", response_model=TopicsResponseModel)
async def research_topics(req: TopicsRequestModel) -> TopicsResponseModel:
    """拉今日热点 + 整理候选清单（含 Claude web_search）."""
    try:
        researcher = TopicResearcher()
        result = researcher.research(
            TopicResearchRequest(
                direction=req.direction,
                seed_links=req.seed_links,
                avoid_topics=req.avoid_topics,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"选题研究失败: {e}") from e

    return TopicsResponseModel(
        candidates_markdown=result.candidates_markdown,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cache_read_tokens=result.cache_read_tokens,
        cache_creation_tokens=result.cache_creation_tokens,
        web_search_count=result.web_search_count,
    )
