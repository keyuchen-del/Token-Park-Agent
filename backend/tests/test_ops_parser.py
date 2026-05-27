"""测试 ops 文档解析。"""
from pathlib import Path

import pytest

from tpagent.services.ops_parser import (
    filter_required,
    parse_ops_images,
    specs_summary,
)


SAMPLE_OPS = """# 配图与运营手册 - 测试

## 一、配图清单

### ⭐ 图 1：封面图

- **位置**：标题之前
- **视觉目标**：测试视觉目标

**Image2 Prompt · 中文版**

```
这是中文封面 prompt 内容
```

**Image2 Prompt · English**

```
This is English cover prompt content
```

**负向词**：illustration, 3D, neon

### ⭐ 图 2：核心数据图

**Image2 Prompt · 中文版**

```
中文数据图 prompt
```

**Image2 Prompt · English**

```
English data chart prompt
```

### 图 3：可选信源截图

- **位置**：第三段附近
- **这张不是 AI 生图，是真实截图操作**
"""


def test_parse_extracts_three_images(tmp_path: Path) -> None:
    ops = tmp_path / "test-ops.md"
    ops.write_text(SAMPLE_OPS, encoding="utf-8")

    specs = parse_ops_images(ops)
    assert len(specs) == 3


def test_required_filter(tmp_path: Path) -> None:
    ops = tmp_path / "test-ops.md"
    ops.write_text(SAMPLE_OPS, encoding="utf-8")

    specs = parse_ops_images(ops)
    required = filter_required(specs)
    assert len(required) == 2  # 图 1 和图 2 带 ⭐


def test_prompt_extraction(tmp_path: Path) -> None:
    ops = tmp_path / "test-ops.md"
    ops.write_text(SAMPLE_OPS, encoding="utf-8")

    specs = parse_ops_images(ops)
    cover = specs[0]
    assert cover.image_id == "图 1"
    assert cover.image_title == "封面图"
    assert cover.prompt_zh == "这是中文封面 prompt 内容"
    assert cover.prompt_en == "This is English cover prompt content"
    assert cover.is_required is True
    assert "illustration" in (cover.negative_words or "")


def test_real_screenshot_image_has_no_prompts(tmp_path: Path) -> None:
    """真实截图类图应该正确识别 prompt 缺失。"""
    ops = tmp_path / "test-ops.md"
    ops.write_text(SAMPLE_OPS, encoding="utf-8")

    specs = parse_ops_images(ops)
    screenshot = specs[2]
    assert screenshot.image_id == "图 3"
    assert screenshot.prompt_zh is None
    assert screenshot.prompt_en is None
    assert screenshot.is_required is False


def test_summary_format(tmp_path: Path) -> None:
    ops = tmp_path / "test-ops.md"
    ops.write_text(SAMPLE_OPS, encoding="utf-8")

    specs = parse_ops_images(ops)
    summary = specs_summary(specs)
    assert "图 1" in summary
    assert "图 3" in summary
    assert "⭐" in summary
