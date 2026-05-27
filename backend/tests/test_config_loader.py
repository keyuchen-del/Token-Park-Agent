"""测试配置加载。"""
import pytest

from tpagent.config_loader import ConfigLoader, get_config


def test_writing_style_loads() -> None:
    """writing-style.yaml 应该能加载。"""
    config = get_config()
    style = config.writing_style
    assert "connectors" in style
    assert "brackets" in style
    assert "ending" in style


def test_grep_rules_loads() -> None:
    """grep-rules.yaml 应该能加载 + 含 6 条规则。"""
    config = get_config()
    rules = config.grep_rules
    assert "rules" in rules
    rule_ids = {r["id"] for r in rules["rules"]}
    expected = {
        "cross_date_reference",
        "ai_high_freq_words",
        "half_brackets",
        "templated_connectors",
        "khazix_ending_signatures",
        "ai_heading_smell",
    }
    assert expected.issubset(rule_ids)


def test_brand_loads_with_fallback() -> None:
    """brand.yaml 不存在时 fallback brand.yaml.example。"""
    config = get_config()
    brand = config.brand
    assert "account" in brand
    assert brand["account"]["name_zh"]


def test_article_writer_prompt_loads() -> None:
    """article-writer.md prompt 应该加载且不为空。"""
    config = get_config()
    prompt = config.article_writer_prompt
    assert len(prompt) > 500  # 至少有内容
    assert "Token 公园" in prompt


def test_ops_writer_prompt_loads() -> None:
    """ops-writer.md prompt 应该加载且不为空。"""
    config = get_config()
    prompt = config.ops_writer_prompt
    assert len(prompt) > 500
    assert "Image2 Prompt" in prompt
