"""OpenAI DALL-E 3 出图服务。

用法：
    from tpagent.services.image_generator import DalleImageGenerator
    gen = DalleImageGenerator()
    images = gen.generate(prompt="...", num_candidates=3)

DALL-E 3 限制：
- 一次 API call 只能 n=1（不像 DALL-E 2 支持 n=10）
- 所以 num_candidates 是多次调用
- 中文字几乎一定乱码 → 配合 text_overlay 服务做后期叠字
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import OpenAI

from tpagent.settings import get_settings


@dataclass
class GeneratedImage:
    """单张生成结果。"""

    index: int                # 候选序号
    image_path: Path          # 本地保存路径
    revised_prompt: str       # DALL-E 实际用的 prompt（OpenAI 会改写）
    url: str                  # OpenAI 返回的 URL（24h 后失效）


@dataclass
class GenerationResult:
    """一次出图结果集。"""

    candidates: list[GeneratedImage]
    prompt: str
    cost_usd: float           # 估算成本


# DALL-E 3 定价（2026 当前公开价）
_DALLE_PRICING = {
    "standard": {
        "1024x1024": 0.040,
        "1792x1024": 0.080,
        "1024x1792": 0.080,
    },
    "hd": {
        "1024x1024": 0.080,
        "1792x1024": 0.120,
        "1024x1792": 0.120,
    },
}


class DalleImageGenerator:
    """DALL-E 3 出图。"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "未找到 OPENAI_API_KEY。\n"
                "请在 agent/.env 里填入：OPENAI_API_KEY=sk-xxx\n"
                "（从 https://platform.openai.com/api-keys 拿）"
            )
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.dalle_model

    def _generate_one(
        self,
        prompt: str,
        size: str,
        quality: str,
    ) -> tuple[str, str]:
        """单次调用 DALL-E 3。返回 (image_url, revised_prompt)."""
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,  # type: ignore[arg-type]
            quality=quality,  # type: ignore[arg-type]
            n=1,  # DALL-E 3 强制 n=1
        )
        data = response.data[0]
        return (data.url or "", data.revised_prompt or prompt)

    def _download_image(self, url: str, target: Path) -> None:
        """下载图片到本地。"""
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            target.write_bytes(resp.content)

    def generate(
        self,
        prompt: str,
        num_candidates: int = 3,
        size: str = "1792x1024",   # 接近 1.91:1 公众号封面比例
        quality: str = "standard",  # standard / hd
        output_dir: Path | None = None,
        slug: str = "image",
    ) -> GenerationResult:
        """生成 N 个候选。

        Args:
            prompt: image2 prompt（建议从 ops 文档解析得来）
            num_candidates: 候选数量
            size: 1024x1024 / 1792x1024 / 1024x1792
            quality: standard 或 hd
            output_dir: 保存目录，None 时用 sessions_dir/today/images
            slug: 文件名前缀

        Returns:
            GenerationResult，含 N 张候选路径
        """
        if output_dir is None:
            settings = get_settings()
            output_dir = settings.sessions_dir / "tmp_images"
        output_dir.mkdir(parents=True, exist_ok=True)

        candidates = []
        for i in range(num_candidates):
            url, revised = self._generate_one(prompt, size, quality)
            image_path = output_dir / f"{slug}-candidate-{i + 1}.png"
            self._download_image(url, image_path)
            candidates.append(GeneratedImage(
                index=i + 1,
                image_path=image_path,
                revised_prompt=revised,
                url=url,
            ))

        cost_per_image = _DALLE_PRICING.get(quality, {}).get(size, 0.04)
        total_cost = round(cost_per_image * num_candidates, 4)

        return GenerationResult(
            candidates=candidates,
            prompt=prompt,
            cost_usd=total_cost,
        )

    async def generate_async(
        self,
        prompt: str,
        num_candidates: int = 3,
        size: str = "1792x1024",
        quality: str = "standard",
        output_dir: Path | None = None,
        slug: str = "image",
    ) -> GenerationResult:
        """异步版本：N 个候选并发生成（节省时间）。"""
        if output_dir is None:
            settings = get_settings()
            output_dir = settings.sessions_dir / "tmp_images"
        output_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        async def gen_one(idx: int) -> GeneratedImage:
            url, revised = await loop.run_in_executor(
                None, self._generate_one, prompt, size, quality
            )
            image_path = output_dir / f"{slug}-candidate-{idx + 1}.png"
            await loop.run_in_executor(None, self._download_image, url, image_path)
            return GeneratedImage(
                index=idx + 1,
                image_path=image_path,
                revised_prompt=revised,
                url=url,
            )

        candidates = await asyncio.gather(
            *[gen_one(i) for i in range(num_candidates)]
        )

        cost_per_image = _DALLE_PRICING.get(quality, {}).get(size, 0.04)
        total_cost = round(cost_per_image * num_candidates, 4)

        return GenerationResult(
            candidates=list(candidates),
            prompt=prompt,
            cost_usd=total_cost,
        )
