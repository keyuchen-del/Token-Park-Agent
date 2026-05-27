"""ops 文档解析器。从 ops markdown 里提取每张图的 image2 prompt。"""
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImageSpec:
    """从 ops 文档解析出来的单张图规格。"""

    image_id: str           # 如 "图 1" / "图 2"
    image_title: str        # 如 "封面图" / "数据对比卡片"
    prompt_zh: str | None   # 中文 prompt
    prompt_en: str | None   # 英文 prompt
    negative_words: str | None  # 负向词
    is_required: bool       # 是否带 ⭐（必配）


# 匹配 "### ⭐ 图 1：封面图" / "### 图 3：xxx"
_IMAGE_HEADING_RE = re.compile(
    r"^###\s+(?P<star>⭐\s+)?(?P<id>图\s*\d+)[：:\s]+(?P<title>.+?)$",
    re.MULTILINE,
)

# 匹配 "**Image2 Prompt · 中文版**" 块
_PROMPT_ZH_RE = re.compile(
    r"\*\*Image2\s+Prompt\s*[·•]\s*中文版?\*\*\s*\n+```[a-z]*\n(?P<prompt>.+?)\n```",
    re.DOTALL | re.IGNORECASE,
)

# 匹配 "**Image2 Prompt · English**" 块
_PROMPT_EN_RE = re.compile(
    r"\*\*Image2\s+Prompt\s*[·•]\s*English\*\*\s*\n+```[a-z]*\n(?P<prompt>.+?)\n```",
    re.DOTALL | re.IGNORECASE,
)

# 匹配 "**负向词**：xxx"
_NEGATIVE_RE = re.compile(r"\*\*负向词\*\*[：:]\s*(.+?)(?=\n\n|\n\*\*|\Z)", re.DOTALL)


def parse_ops_images(ops_path: Path) -> list[ImageSpec]:
    """从 ops 文档解析出所有图的 spec。"""
    if not ops_path.exists():
        raise FileNotFoundError(f"ops 文件不存在: {ops_path}")

    content = ops_path.read_text(encoding="utf-8")
    specs: list[ImageSpec] = []

    # 先按 ### 图 N：xxx 切分
    headings = list(_IMAGE_HEADING_RE.finditer(content))
    for idx, heading in enumerate(headings):
        start = heading.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(content)
        block = content[start:end]

        zh_match = _PROMPT_ZH_RE.search(block)
        en_match = _PROMPT_EN_RE.search(block)
        neg_match = _NEGATIVE_RE.search(block)

        specs.append(ImageSpec(
            image_id=heading.group("id").strip(),
            image_title=heading.group("title").strip(),
            prompt_zh=zh_match.group("prompt").strip() if zh_match else None,
            prompt_en=en_match.group("prompt").strip() if en_match else None,
            negative_words=neg_match.group(1).strip() if neg_match else None,
            is_required=bool(heading.group("star")),
        ))

    return specs


def filter_required(specs: list[ImageSpec]) -> list[ImageSpec]:
    """只保留带 ⭐ 的必配图。"""
    return [s for s in specs if s.is_required]


def specs_summary(specs: list[ImageSpec]) -> str:
    """生成 specs 摘要表（人读用）。"""
    lines = []
    for s in specs:
        star = "⭐ " if s.is_required else "   "
        zh_status = "✅" if s.prompt_zh else "❌"
        en_status = "✅" if s.prompt_en else "❌"
        lines.append(
            f"{star}{s.image_id} {s.image_title}"
            f"  [中 {zh_status} / 英 {en_status}]"
        )
    return "\n".join(lines)
