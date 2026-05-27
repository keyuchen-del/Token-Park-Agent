"""Cloudflare R2 上传服务（兼容 S3 API）。

R2 提供 10GB 免费存储 + 流量免费，适合 token-park-agent 的图床。
未配置 R2 时自动 fallback 本地存储。

获取 R2 credentials:
1. https://dash.cloudflare.com/ 注册账号
2. R2 → Manage R2 API Tokens → Create API token
3. 填进 .env: R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_BUCKET
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

from tpagent.settings import get_settings


@dataclass
class UploadResult:
    """上传结果。"""

    key: str            # 在 bucket 里的 key
    url: str            # 可访问的 URL（如配置了 R2_PUBLIC_URL）
    size_bytes: int
    is_local: bool      # True = 还在本地未上传到云


def _calc_key(file_path: Path, prefix: str = "") -> str:
    """基于内容 hash + 文件名生成 key。同样内容多次上传只占一份空间。"""
    sha = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    suffix = file_path.suffix
    name = file_path.stem
    if prefix:
        return f"{prefix.strip('/')}/{name}-{sha}{suffix}"
    return f"{name}-{sha}{suffix}"


class R2Uploader:
    """Cloudflare R2 / S3 兼容上传器。

    未配置 R2 credentials 时自动用本地路径作为"URL"返回，
    方便 V0.1 本地开发。
    """

    def __init__(self) -> None:
        from tpagent.settings import get_settings as _gs
        # 延迟加载，便于检测配置完整性
        settings = _gs()
        self.account_id = getattr(settings, "r2_account_id", "") or ""
        self.access_key = getattr(settings, "r2_access_key_id", "") or ""
        self.secret_key = getattr(settings, "r2_secret_access_key", "") or ""
        self.bucket = getattr(settings, "r2_bucket", "tpagent-images") or "tpagent-images"
        self.public_url = getattr(settings, "r2_public_url", "") or ""
        self._client = None

    @property
    def is_configured(self) -> bool:
        """是否完整配置了 R2."""
        return bool(self.account_id and self.access_key and self.secret_key)

    def _get_client(self):
        """懒加载 boto3 client（S3 兼容协议）。"""
        if self._client is None:
            import boto3
            endpoint = f"https://{self.account_id}.r2.cloudflarestorage.com"
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name="auto",
            )
        return self._client

    def upload(
        self,
        file_path: Path,
        prefix: str = "",
        content_type: str = "image/png",
    ) -> UploadResult:
        """上传一个文件到 R2。未配置时自动 fallback 本地路径。"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        size = file_path.stat().st_size

        if not self.is_configured:
            # 未配置 R2：返回本地路径作为 URL
            return UploadResult(
                key=str(file_path),
                url=f"file://{file_path.resolve()}",
                size_bytes=size,
                is_local=True,
            )

        key = _calc_key(file_path, prefix)
        client = self._get_client()

        client.upload_file(
            Filename=str(file_path),
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=31536000",  # CDN 永久缓存
            },
        )

        # 拼 URL
        if self.public_url:
            url = f"{self.public_url.rstrip('/')}/{key}"
        else:
            # 用 R2.dev 临时域名（不推荐生产用）
            url = f"https://pub-{self.account_id}.r2.dev/{key}"

        return UploadResult(
            key=key,
            url=url,
            size_bytes=size,
            is_local=False,
        )

    def upload_batch(
        self,
        file_paths: list[Path],
        prefix: str = "",
    ) -> list[UploadResult]:
        """批量上传。"""
        return [self.upload(p, prefix=prefix) for p in file_paths]
