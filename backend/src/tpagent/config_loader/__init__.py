"""YAML 配置加载器。把 config/ 下的写作规则、grep 规则、prompts 加载到内存。"""
from pathlib import Path
from typing import Any

import yaml

from tpagent.settings import get_settings


class ConfigLoader:
    """加载 config/ 目录下所有 YAML + prompts。"""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or get_settings().config_dir
        if not self.config_dir.exists():
            raise FileNotFoundError(
                f"配置目录不存在: {self.config_dir.resolve()}\n"
                f"请确认 .env 里 CONFIG_DIR 指向正确路径，或使用默认 ../config"
            )

    def _load_yaml(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_text(self, relative_path: str) -> str:
        path = self.config_dir / relative_path
        if not path.exists():
            raise FileNotFoundError(f"prompt 文件不存在: {path}")
        return path.read_text(encoding="utf-8")

    # === 写作风格 ===
    @property
    def writing_style(self) -> dict[str, Any]:
        return self._load_yaml("writing-style.yaml")

    # === grep 规则 ===
    @property
    def grep_rules(self) -> dict[str, Any]:
        return self._load_yaml("grep-rules.yaml")

    # === 品牌信息 ===
    @property
    def brand(self) -> dict[str, Any]:
        # 优先 brand.yaml（用户私有），fallback brand.yaml.example
        private = self.config_dir / "brand.yaml"
        if private.exists():
            return self._load_yaml("brand.yaml")
        return self._load_yaml("brand.yaml.example")

    # === Prompts ===
    @property
    def article_writer_prompt(self) -> str:
        return self._load_text("prompts/article-writer.md")

    @property
    def topic_research_prompt(self) -> str:
        return self._load_text("prompts/topic-research.md")

    @property
    def ops_writer_prompt(self) -> str:
        return self._load_text("prompts/ops-writer.md")


# 全局单例
_config: ConfigLoader | None = None


def get_config() -> ConfigLoader:
    """获取配置加载器单例。"""
    global _config
    if _config is None:
        _config = ConfigLoader()
    return _config
