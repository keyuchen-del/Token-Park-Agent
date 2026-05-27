"""Claude Agent SDK 包装。负责调用 Claude API 写文章。"""

from dataclasses import dataclass

from anthropic import Anthropic

from tpagent.config_loader import get_config
from tpagent.settings import get_settings


@dataclass
class WriteRequest:
    """写作请求."""

    topic: str
    material: str | None = None
    angle: str | None = None


@dataclass
class WriteResult:
    """写作结果."""

    article_markdown: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class ArticleWriter:
    """文章写作 Agent。

    用 Claude API + prompt caching：
    - 把 article-writer.md + brand info 作为 cached system prompt
    - 用户消息只传选题 + 素材
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "未找到 ANTHROPIC_API_KEY。\n"
                "请在 agent/.env 里填入：ANTHROPIC_API_KEY=sk-ant-xxx\n"
                "（从 https://console.anthropic.com/ 拿）"
            )
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.config = get_config()

    def _build_system_prompt(self) -> str:
        """组装系统 prompt（写作规则 + 品牌信息）。"""
        article_prompt = self.config.article_writer_prompt
        brand = self.config.brand
        brand_block = (
            f"\n\n## 当前账号信息（必须遵守）\n\n"
            f"- 账号中文名: {brand.get('account', {}).get('name_zh', 'Token 公园')}\n"
            f"- 署名: {brand.get('author', {}).get('signature', '/ 作者：Token 公园')}\n"
            f"- 邮箱: {brand.get('author', {}).get('contact_email', 'xxx@xxx.com')}\n"
        )
        return article_prompt + brand_block

    def _build_user_message(self, req: WriteRequest) -> str:
        """组装用户消息（选题 + 素材）。"""
        parts = [f"# 选题\n\n{req.topic}\n"]
        if req.angle:
            parts.append(f"\n# 切入角度\n\n{req.angle}\n")
        if req.material:
            parts.append(f"\n# 素材 / 信源链接\n\n{req.material}\n")
        parts.append(
            "\n按 Token 公园写作规则，写一篇 3500-5000 字的公众号长文。"
            "**直接输出 markdown 正文**，不要加任何元信息说明、不要写"
            "'以下是文章'之类的前言。"
        )
        return "".join(parts)

    def write(self, req: WriteRequest) -> WriteResult:
        """同步写一篇文章。

        使用 prompt caching：system 段加 cache_control，
        重复请求时只算输入新增部分。
        """
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

        # 提取文本内容
        article_text = ""
        for block in response.content:
            if block.type == "text":
                article_text += block.text

        usage = response.usage
        return WriteResult(
            article_markdown=article_text.strip(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
