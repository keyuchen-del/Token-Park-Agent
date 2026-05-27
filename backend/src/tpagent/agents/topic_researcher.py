"""选题研究 Agent。用 Claude + web_search tool 拉今日热点 + 整理候选清单。"""

from dataclasses import dataclass

from anthropic import Anthropic

from tpagent.config_loader import get_config
from tpagent.settings import get_settings


@dataclass
class TopicResearchRequest:
    """选题研究请求。"""

    direction: str  # 一句话主题方向
    seed_links: list[str] | None = None  # 可选：用户提供的信源链接
    avoid_topics: list[str] | None = None  # 最近发过的选题（避免撞稿）


@dataclass
class TopicResearchResult:
    """选题研究结果。"""

    candidates_markdown: str  # 候选清单（markdown 表格）
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    web_search_count: int = 0  # 调用 web search 的次数


class TopicResearcher:
    """选题研究 Agent。

    工作流：
    1. 接收用户的方向（如"今天科技圈"）
    2. 让 Claude 调 web_search 拉最近 24-48 小时事实
    3. 让 Claude 整理候选清单 + 推荐排序
    4. 返回 markdown 表格
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "未找到 ANTHROPIC_API_KEY。\n请在 agent/.env 里填入：ANTHROPIC_API_KEY=sk-ant-xxx"
            )
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.config = get_config()

    def _build_system_prompt(self) -> str:
        """组装选题研究 prompt。"""
        topic_prompt = self.config.topic_research_prompt
        brand = self.config.brand
        brand_block = (
            f"\n\n## 当前账号信息\n\n"
            f"- 账号: {brand.get('account', {}).get('name_zh', 'Token 公园')}\n"
            f"- 定位: {brand.get('account', {}).get('positioning', '泛科技')}\n"
            f"- 视角: {brand.get('account', {}).get('perspective', '学习者 / 同行者')}\n"
        )
        return topic_prompt + brand_block

    def _build_user_message(self, req: TopicResearchRequest) -> str:
        """组装用户消息。"""
        parts = [f"# 选题方向\n\n{req.direction}\n"]
        if req.seed_links:
            parts.append("\n# 用户提供的信源\n\n")
            for link in req.seed_links:
                parts.append(f"- {link}\n")
        if req.avoid_topics:
            parts.append("\n# 最近发过的选题（避免撞稿）\n\n")
            for topic in req.avoid_topics:
                parts.append(f"- {topic}\n")
        parts.append(
            "\n用 web_search 工具拉最近 48 小时的事实，"
            "整理一份候选清单 + 推荐排序。"
            "用 markdown 表格格式输出。"
        )
        return "".join(parts)

    def research(self, req: TopicResearchRequest) -> TopicResearchResult:
        """研究选题 + 返回候选清单。

        启用 Claude web search tool（max_uses=5 控制成本）。
        """
        system_prompt = self._build_system_prompt()
        user_message = self._build_user_message(req)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }
            ],
            messages=[
                {"role": "user", "content": user_message},
            ],
        )

        # 提取最终回复文本（跳过 tool_use 块）
        candidates_text = ""
        web_search_count = 0
        for block in response.content:
            if block.type == "text":
                candidates_text += block.text
            elif block.type == "server_tool_use" and getattr(block, "name", None) == "web_search":
                web_search_count += 1

        usage = response.usage
        return TopicResearchResult(
            candidates_markdown=candidates_text.strip(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            web_search_count=web_search_count,
        )
