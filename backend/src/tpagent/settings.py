"""环境变量配置加载."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从 .env 读取的设置。所有 secret 通过 env 注入，不在代码里硬编码。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === Claude API ===
    # 改成 Optional，让 grep / scan 等不需要 API 的命令也能跑
    # 调 Claude 的 ArticleWriter 实例化时再检查
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude 模型名",
    )

    # === OpenAI（V0.2 启用）===
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    dalle_model: str = "dall-e-3"

    # === Cloudflare R2（V0.2 启用，未配置时自动 fallback 本地）===
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str = "tpagent-images"
    r2_public_url: str | None = None

    # === 存储 ===
    data_dir: Path = Field(default=Path("./data"))
    sessions_dir: Path = Field(default=Path("./sessions"))
    db_path: Path = Field(default=Path("./data/tpagent.db"))

    # === 服务 ===
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # === 配置文件目录（默认指向 agent/config）===
    config_dir: Path = Field(default=Path("../config"))

    def ensure_dirs(self) -> None:
        """确保所有需要的目录存在."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


# 全局单例
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置单例（懒加载）。"""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
        _settings.ensure_dirs()
    return _settings
