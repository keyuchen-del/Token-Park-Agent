"""Pydantic API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================
# Write
# ============================================================
class WriteRequestModel(BaseModel):
    """POST /api/write 请求体。"""

    topic: str = Field(..., description="选题方向，一句话")
    material: str | None = Field(default=None, description="信源链接 / 素材 / PDF 文本")
    angle: str | None = Field(default=None, description="切入角度，特殊要求")


class GrepHitModel(BaseModel):
    """单条命中。"""

    rule_id: str
    rule_name: str
    line_no: int
    line_content: str
    matched_text: str
    is_exception: bool


class GrepReportModel(BaseModel):
    """扫描结果。"""

    can_publish: bool
    total_hits: int
    rule_summary: dict[str, int]
    hits: list[GrepHitModel]
    exceptions: list[GrepHitModel]


class WriteResponseModel(BaseModel):
    """POST /api/write 响应。"""

    session_id: int | None = None
    article_markdown: str
    article_path: str = Field(..., description="保存到的绝对路径")
    char_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    grep_report: GrepReportModel


# ============================================================
# Topics
# ============================================================
class TopicsRequestModel(BaseModel):
    """POST /api/topics 请求体。"""

    direction: str = Field(..., description="选题方向，一句话")
    seed_links: list[str] | None = Field(default=None, description="可选信源链接")
    avoid_topics: list[str] | None = Field(default=None, description="避免撞稿的近期选题")


class TopicsResponseModel(BaseModel):
    """POST /api/topics 响应。"""

    candidates_markdown: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    web_search_count: int


# ============================================================
# Ops
# ============================================================
class OpsRequestModel(BaseModel):
    """POST /api/ops 请求体。"""

    article_path: str = Field(..., description="已有文章 .md 的绝对路径")
    topic: str = Field(..., description="选题（用于 ops 文件名）")
    session_id: int | None = Field(default=None, description="如有 session，会更新状态")


class OpsResponseModel(BaseModel):
    """POST /api/ops 响应。"""

    ops_markdown: str
    ops_path: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    grep_report: GrepReportModel


# ============================================================
# Images
# ============================================================
class ImageSpecModel(BaseModel):
    """单张图 spec。"""

    image_id: str
    image_title: str
    prompt_zh: str | None
    prompt_en: str | None
    negative_words: str | None
    is_required: bool


class ImagesParseRequestModel(BaseModel):
    """POST /api/images/parse 请求体（dry-run，只解析）。"""

    ops_path: str
    required_only: bool = True


class ImagesParseResponseModel(BaseModel):
    """ops 解析结果（不实际出图）。"""

    specs: list[ImageSpecModel]
    estimated_cost_usd: float = Field(description="按默认 standard / 1792x1024 / 3 候选估算")


class GeneratedImageModel(BaseModel):
    """单张已生成图。"""

    index: int
    image_path: str
    revised_prompt: str


class ImagesGenerateRequestModel(BaseModel):
    """POST /api/images/generate 请求体（实际调 DALL-E）。"""

    ops_path: str
    required_only: bool = True
    candidates: int = 3
    size: str = "1792x1024"
    quality: str = "standard"


class ImagesGenerateResponseModel(BaseModel):
    """实际出图结果。"""

    images_dir: str
    by_spec: dict[str, list[GeneratedImageModel]]
    total_cost_usd: float


# ============================================================
# Sessions
# ============================================================
class SessionModel(BaseModel):
    """session 列表里的单条记录。"""

    id: int
    topic: str
    angle: str | None
    material: str | None
    stage: str
    can_publish: bool
    grep_hits: int
    article_path: str | None
    ops_path: str | None
    images_dir: str | None
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class SessionListResponseModel(BaseModel):
    """GET /api/sessions 响应。"""

    sessions: list[SessionModel]
    total: int
