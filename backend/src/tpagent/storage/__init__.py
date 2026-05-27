"""文件系统 + SQLite session 存储。"""
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from tpagent.settings import get_settings


def slugify(text: str, max_length: int = 50) -> str:
    """把中文 / 任意文本转成文件名 slug.

    Token 公园规则：保留拼音 / 英文 / 数字 / 横线，其余转横线。
    中文直接保留（macOS / 多数系统支持中文文件名）。
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().lower()
    # 替换连续空白为单个横线
    text = re.sub(r"\s+", "-", text)
    # 删除控制字符 + 特殊符号
    text = re.sub(r"[^\w\-一-鿿]", "", text, flags=re.UNICODE)
    text = text[:max_length].strip("-")
    return text or "untitled"


def get_session_dir(session_date: datetime | None = None) -> Path:
    """获取当日子文件夹路径 articles/{M.D}/。

    规则：M.D 不带前导零、不带年份。
    """
    settings = get_settings()
    now = session_date or datetime.now()
    folder_name = f"{now.month}.{now.day}"
    target = settings.sessions_dir / folder_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_article_filename(
    topic: str,
    date: datetime | None = None,
    suffix: str = "",
) -> str:
    """生成文章文件名 YYYY-MM-DD-{slug}{suffix}.md。"""
    now = date or datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    slug = slugify(topic, max_length=40)
    return f"{date_str}-{slug}{suffix}.md"


def save_article(article_md: str, topic: str, date: datetime | None = None) -> Path:
    """把文章保存到当日子文件夹。返回文件绝对路径。"""
    session_dir = get_session_dir(date)
    filename = build_article_filename(topic, date)
    target = session_dir / filename
    target.write_text(article_md, encoding="utf-8")
    return target


def save_ops(ops_md: str, topic: str, date: datetime | None = None) -> Path:
    """把 ops 文档保存到当日子文件夹。文件名为 {YYYY-MM-DD}-{slug}-ops.md。"""
    session_dir = get_session_dir(date)
    filename = build_article_filename(topic, date, suffix="-ops")
    target = session_dir / filename
    target.write_text(ops_md, encoding="utf-8")
    return target
