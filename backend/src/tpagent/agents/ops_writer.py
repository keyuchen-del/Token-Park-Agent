"""ops 文档生成 Agent。基于已有文章正文，生成图运营合一文档。"""
from dataclasses import dataclass

from anthropic import Anthropic

from tpagent.config_loader import get_config
from tpagent.settings import get_settings


@dataclass
class OpsWriteRequest:
    """ops 文档生成请求。"""

    article_markdown: str  # 已有的文章正文
    topic: str             # 选题（用于标题）


@dataclass
class OpsWriteResult:
    """ops 文档结果。"""

    ops_markdown: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class OpsWriter:
    """ops 文档写作 Agent。

    输入：已有的文章 markdown
    输出：8 节完整的 ops 文档（配图清单 + image2 prompts + 标题 A/B 等）

    使用 prompt caching：ops-writer.md prompt + brand 信息作为 cached system，
    每次只算新的文章正文 token。
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "未找到 ANTHROPIC_API_KEY。\n"
                "请在 agent/.env 里填入：ANTHROPIC_API_KEY=sk-ant-xxx"
            )
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.config = get_config()

    def _build_system_prompt(self) -> str:
        """系统 prompt = ops-writer 规则 + brand 视觉规范。"""
        ops_prompt = self.config.ops_writer_prompt
        brand = self.config.brand
        colors = brand.get("colors", {})
        typography = brand.get("typography", {})
        sizes = brand.get("sizes", {})

        brand_block = (
            f"\n\n## 当前账号视觉规范\n\n"
            f"### 色板\n"
            f"- 主背景: {colors.get('bg_primary', '#FDF2EE')}\n"
            f"- 卡片背景: {colors.get('bg_card', '#F8E1DA')}\n"
            f"- 主文字: {colors.get('text_primary', '#3A1C1C')}\n"
            f"- 主红: {colors.get('accent_main', '#C9302C')}\n"
            f"- 强调红: {colors.get('accent_strong', '#8B1A2E')}\n"
            f"\n### 字体\n"
            f"- 中文标题: {typography.get('chinese_heading', '思源宋体 Heavy')}\n"
            f"- 中文正文: {typography.get('chinese_body', '思源宋体 Regular')}\n"
            f"- 英文: {typography.get('latin', 'Söhne / Inter')}\n"
            f"\n### 尺寸\n"
            f"- 封面: {sizes.get('cover_ratio', '1.91:1')}, {sizes.get('cover_px', '1200×630')}\n"
            f"- 正文图: {sizes.get('body_image_ratio', '4:3')}, {sizes.get('body_image_px', '1200×900')}\n"
        )
        return ops_prompt + brand_block

    def _build_user_message(self, req: OpsWriteRequest) -> str:
        """用户消息 = 选题 + 文章正文。"""
        return (
            f"# 选题\n\n{req.topic}\n\n"
            f"---\n\n"
            f"# 已经写好的文章正文（基于此写 ops）\n\n"
            f"{req.article_markdown}\n\n"
            f"---\n\n"
            f"按 8 节结构生成完整 ops 文档。"
            f"配图建议 5-6 张，每张必须有完整的中英双语 image2 prompt + 负向词。"
            f"直接输出 markdown 正文，不要加任何元信息说明。"
        )

    def write(self, req: OpsWriteRequest) -> OpsWriteResult:
        """生成 ops 文档。"""
        system_prompt = self._build_system_prompt()
        user_message = self._build_user_message(req)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": user_message},
            ],
        )

        ops_text = ""
        for block in response.content:
            if block.type == "text":
                ops_text += block.text

        usage = response.usage
        return OpsWriteResult(
            ops_markdown=ops_text.strip(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
