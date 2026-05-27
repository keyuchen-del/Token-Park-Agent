"""图像生成相关路由。"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from tpagent.models import (
    GeneratedImageModel,
    ImagesGenerateRequestModel,
    ImagesGenerateResponseModel,
    ImagesParseRequestModel,
    ImagesParseResponseModel,
    ImageSpecModel,
)
from tpagent.services.ops_parser import filter_required, parse_ops_images

router = APIRouter(prefix="/images", tags=["images"])


# DALL-E 3 价格（与 image_generator.py 一致）
_PRICING = {
    ("standard", "1024x1024"): 0.040,
    ("standard", "1792x1024"): 0.080,
    ("standard", "1024x1792"): 0.080,
    ("hd", "1024x1024"): 0.080,
    ("hd", "1792x1024"): 0.120,
    ("hd", "1024x1792"): 0.120,
}


@router.post("/parse", response_model=ImagesParseResponseModel)
async def parse_ops_for_images(
    req: ImagesParseRequestModel,
) -> ImagesParseResponseModel:
    """从 ops 文档解析 image spec（不实际出图，用于预估成本 + 前端展示清单）。"""
    ops_path = Path(req.ops_path)
    if not ops_path.exists():
        raise HTTPException(status_code=404, detail=f"ops 文件不存在: {req.ops_path}")

    specs = parse_ops_images(ops_path)
    if req.required_only:
        specs = filter_required(specs)

    # 估算成本（默认 standard / 1792x1024 / 3 候选）
    per_image = _PRICING.get(("standard", "1792x1024"), 0.08)
    estimated = round(per_image * len(specs) * 3, 4)

    return ImagesParseResponseModel(
        specs=[
            ImageSpecModel(
                image_id=s.image_id,
                image_title=s.image_title,
                prompt_zh=s.prompt_zh,
                prompt_en=s.prompt_en,
                negative_words=s.negative_words,
                is_required=s.is_required,
            )
            for s in specs
        ],
        estimated_cost_usd=estimated,
    )


@router.post("/generate", response_model=ImagesGenerateResponseModel)
async def generate_images(
    req: ImagesGenerateRequestModel,
) -> ImagesGenerateResponseModel:
    """实际调 DALL-E 3 出图。需 OPENAI_API_KEY."""
    ops_path = Path(req.ops_path)
    if not ops_path.exists():
        raise HTTPException(status_code=404, detail=f"ops 文件不存在: {req.ops_path}")

    specs = parse_ops_images(ops_path)
    if req.required_only:
        specs = filter_required(specs)

    if not specs:
        raise HTTPException(status_code=400, detail="ops 文档里没解析到任何图")

    try:
        from tpagent.services.image_generator import DalleImageGenerator

        gen = DalleImageGenerator()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DALL-E 初始化失败: {e}") from e

    output_dir = ops_path.parent / f"{ops_path.stem}-images"
    output_dir.mkdir(parents=True, exist_ok=True)

    by_spec: dict[str, list[GeneratedImageModel]] = {}
    total_cost = 0.0

    for spec in specs:
        prompt = spec.prompt_en or spec.prompt_zh
        if not prompt:
            continue  # 跳过真实截图类
        try:
            result = gen.generate(
                prompt=prompt,
                num_candidates=req.candidates,
                size=req.size,
                quality=req.quality,
                output_dir=output_dir,
                slug=spec.image_id.replace(" ", "-"),
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"出图 {spec.image_id} 失败: {e}",
            ) from e

        by_spec[spec.image_id] = [
            GeneratedImageModel(
                index=c.index,
                image_path=str(c.image_path),
                revised_prompt=c.revised_prompt,
            )
            for c in result.candidates
        ]
        total_cost += result.cost_usd

    return ImagesGenerateResponseModel(
        images_dir=str(output_dir),
        by_spec=by_spec,
        total_cost_usd=round(total_cost, 4),
    )
