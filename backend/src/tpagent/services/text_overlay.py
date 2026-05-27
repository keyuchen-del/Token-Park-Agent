"""中文文字叠加工具。

DALL-E 等图像模型对中文字符渲染极差，几乎一定乱码。
工作流：AI 生成无文字底图 → 用 Pillow 在本地用真实字体叠加中文。
"""

import platform
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 常见中文字体路径（按平台找）
_CHINESE_FONT_CANDIDATES = {
    "Darwin": [  # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Songti.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ],
    "Linux": [
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ],
    "Windows": [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
    ],
}


def find_chinese_font() -> Path:
    """在当前系统中寻找一个可用的中文字体。"""
    system = platform.system()
    candidates = _CHINESE_FONT_CANDIDATES.get(system, [])
    for path_str in candidates:
        p = Path(path_str)
        if p.exists():
            return p
    raise RuntimeError(
        f"在 {system} 上没找到可用的中文字体。\n"
        "请手动指定字体路径，或安装思源字体 / 微软雅黑 / 苹方等。"
    )


@dataclass
class TextLayer:
    """单个文字图层。"""

    text: str
    x: int  # 左上角 x
    y: int  # 左上角 y
    font_size: int = 48
    color: str = "#3A1C1C"  # 默认深棕红黑（Token 公园色板）
    font_path: Path | None = None  # None = 自动找
    align: str = "left"  # left / center / right
    max_width: int | None = None  # 超过自动换行


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """把长文本按最大宽度换行（中文按字符，英文按词）。"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        width = bbox[2] - bbox[0]
        if width > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def overlay_text(
    base_image_path: Path,
    layers: list[TextLayer],
    output_path: Path | None = None,
) -> Path:
    """在底图上叠加多个文字图层。

    Args:
        base_image_path: AI 生成的无文字底图
        layers: 要叠加的文字图层列表
        output_path: 输出路径，None 时在原图旁加 -overlay 后缀

    Returns:
        输出图片的绝对路径
    """
    if not base_image_path.exists():
        raise FileNotFoundError(f"底图不存在: {base_image_path}")

    img = Image.open(base_image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    default_font_path = find_chinese_font()

    for layer in layers:
        font_path = layer.font_path or default_font_path
        font = ImageFont.truetype(str(font_path), layer.font_size)

        # 处理换行
        lines = _wrap_text(layer.text, font, layer.max_width) if layer.max_width else [layer.text]

        # 逐行绘制
        y = layer.y
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1] + 8  # 加 8px 行距

            if layer.align == "center":
                x = layer.x - line_width // 2
            elif layer.align == "right":
                x = layer.x - line_width
            else:
                x = layer.x

            draw.text((x, y), line, font=font, fill=layer.color)
            y += line_height

    # 合成
    result = Image.alpha_composite(img, overlay).convert("RGB")

    if output_path is None:
        stem = base_image_path.stem
        output_path = base_image_path.parent / f"{stem}-overlay.png"

    result.save(output_path, "PNG", optimize=True)
    return output_path


def make_cover_with_text(
    base_image_path: Path,
    title: str,
    main_number: str | None = None,
    main_symbol: str | None = None,
    output_path: Path | None = None,
    width: int = 1200,
    height: int = 630,
    text_color: str = "#3A1C1C",
    accent_color: str = "#C9302C",
) -> Path:
    """给封面图叠加 Token 公园标准排版：主数字 + 符号 + 标题。

    参考 ops-writer.md 里的"封面"image2 prompt 设计：
    - 左侧三分之一放大字号"主数字"（如 55%）
    - 右侧三分之二放小一号"符号"（如 τ）
    - 底部一行放主标题
    """
    layers = []

    if main_number:
        layers.append(
            TextLayer(
                text=main_number,
                x=int(width * 0.08),
                y=int(height * 0.20),
                font_size=int(height * 0.45),
                color=text_color,
            )
        )

    if main_symbol:
        layers.append(
            TextLayer(
                text=main_symbol,
                x=int(width * 0.70),
                y=int(height * 0.30),
                font_size=int(height * 0.30),
                color=accent_color,
            )
        )

    layers.append(
        TextLayer(
            text=title,
            x=int(width * 0.08),
            y=int(height * 0.80),
            font_size=int(height * 0.06),
            color=text_color,
            max_width=int(width * 0.84),
        )
    )

    return overlay_text(base_image_path, layers, output_path)
