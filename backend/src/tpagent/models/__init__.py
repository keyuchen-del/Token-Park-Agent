"""Pydantic API schemas。"""

from pydantic import BaseModel, Field


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

    article_markdown: str
    article_path: str = Field(..., description="保存到的绝对路径")
    char_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    grep_report: GrepReportModel
