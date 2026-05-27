"""测试 grep 6 项扫描逻辑。"""
from pathlib import Path

import pytest

from tpagent.grep import scan_file


def _write(tmp_path: Path, content: str) -> Path:
    """辅助函数：写一个临时 md 文件。"""
    target = tmp_path / "test.md"
    target.write_text(content, encoding="utf-8")
    return target


def test_clean_text_passes(tmp_path: Path) -> None:
    """完全合规的文本应该通过。"""
    md = _write(tmp_path, "# 标题\n\n这是一段完全合规的正文，没有任何禁用词。\n")
    report = scan_file(md)
    assert report.can_publish is True
    assert report.total_hits == 0


def test_ai_high_freq_word_caught(tmp_path: Path) -> None:
    """AI 高频词应该被检出。"""
    md = _write(tmp_path, "其实这段话有问题。\n说白了就是不能用。\n")
    report = scan_file(md)
    assert report.can_publish is False
    matched_texts = {h.matched_text for h in report.hits}
    assert "其实" in matched_texts
    assert "说白了" in matched_texts


def test_half_brackets_caught(tmp_path: Path) -> None:
    """半括号「」应该被检出。"""
    md = _write(tmp_path, "这里有「半括号」必须替换。\n")
    report = scan_file(md)
    assert report.can_publish is False
    rule_ids = {h.rule_id for h in report.hits}
    assert "half_brackets" in rule_ids


def test_templated_connector_caught(tmp_path: Path) -> None:
    """第一/第二/第三 模板连词应该被检出。"""
    md = _write(tmp_path, "第一，这是观点。\n第二，这也是。\n")
    report = scan_file(md)
    assert report.can_publish is False


def test_ordinal_exception_not_blocking(tmp_path: Path) -> None:
    """'第三、第四大头' 这类序数连续表述属于例外，不阻塞发布。"""
    md = _write(tmp_path, "成本占比从最大变成了第三、第四大头。\n")
    report = scan_file(md)
    # '第三、' 会被 grep 命中，但因 line 含 '第三、第四' 应识别为 exception
    has_exception = any(h.is_exception for h in report.exceptions)
    assert has_exception, "第三、第四大头 应识别为序数表述例外"
    # 且不会阻塞发布（因为算 exception 不算 hit）
    assert report.can_publish is True


def test_ordinal_with_ordinary_word_doesnt_trigger(tmp_path: Path) -> None:
    """'第三大头' 中 '第三' 后跟 '大'，根本不应触发 grep（pattern 要求紧跟顿号）。"""
    md = _write(tmp_path, "占成本最大头，其次是第三大头。\n")
    report = scan_file(md)
    # 因为 pattern 是 第三[，、]，'第三大' 不匹配
    assert report.can_publish is True
    assert report.total_hits == 0


def test_khazix_ending_signature_caught(tmp_path: Path) -> None:
    """卡兹克标志结尾应该被检出。"""
    md = _write(tmp_path, "大时代啊，朋友们。\n")
    report = scan_file(md)
    assert report.can_publish is False


def test_cross_date_caught(tmp_path: Path) -> None:
    """跨日期引用应该被检出。"""
    md = _write(tmp_path, "昨天我们聊过的那篇文章。\n")
    report = scan_file(md)
    assert report.can_publish is False
