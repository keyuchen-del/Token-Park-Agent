"""6 项发布前 grep 扫描 (Python 化).

迁移自 templates/writing-style.md 第七节扫描脚本。
"""
import re
from dataclasses import dataclass
from pathlib import Path

from tpagent.config_loader import get_config


@dataclass
class GrepHit:
    """单条命中记录。"""

    rule_id: str
    rule_name: str
    file: str
    line_no: int
    line_content: str
    matched_text: str
    is_exception: bool = False


@dataclass
class GrepReport:
    """扫描报告。"""

    hits: list[GrepHit]
    exceptions: list[GrepHit]
    rule_summary: dict[str, int]
    can_publish: bool

    @property
    def total_hits(self) -> int:
        return len(self.hits)

    def format_text(self) -> str:
        """格式化为人读的扫描报告。"""
        lines = []
        lines.append("=" * 60)
        lines.append("📋 发布前 grep 扫描报告")
        lines.append("=" * 60)
        for rule_id, count in self.rule_summary.items():
            status = "✓" if count == 0 else "❌"
            lines.append(f"  {status} {rule_id}: {count} 处命中")

        if self.hits:
            lines.append("\n❌ 必须修复的命中:")
            for h in self.hits:
                lines.append(
                    f"  [{h.rule_name}] {Path(h.file).name}:{h.line_no}\n"
                    f"      命中文字: {h.matched_text!r}\n"
                    f"      所在行: {h.line_content.strip()[:120]}"
                )

        if self.exceptions:
            lines.append("\n⚠️  例外（需人工判断）:")
            for h in self.exceptions:
                lines.append(
                    f"  [{h.rule_name}] {Path(h.file).name}:{h.line_no}\n"
                    f"      命中文字: {h.matched_text!r}（属于配置的例外，请人工确认）"
                )

        lines.append("\n" + "=" * 60)
        lines.append("✅ 可以发布" if self.can_publish else "❌ 不能发布，先修复上方命中")
        lines.append("=" * 60)
        return "\n".join(lines)


def scan_file(file_path: Path) -> GrepReport:
    """扫描单个 markdown 文件."""
    return scan_files([file_path])


def scan_files(file_paths: list[Path]) -> GrepReport:
    """扫描多个 markdown 文件。返回综合报告。"""
    config = get_config()
    rules = config.grep_rules.get("rules", [])

    hits: list[GrepHit] = []
    exceptions: list[GrepHit] = []
    rule_summary: dict[str, int] = {}

    for file_path in file_paths:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        for rule in rules:
            rule_id = rule["id"]
            rule_name = rule["name"]
            patterns = rule.get("patterns", [])
            exceptions_list = rule.get("exceptions", [])
            multiline = rule.get("multiline", False)

            rule_summary.setdefault(rule_id, 0)

            for pattern in patterns:
                if multiline:
                    # 行首匹配 (如 ^## 接下来)
                    regex = re.compile(pattern, re.MULTILINE)
                else:
                    regex = re.compile(pattern)

                for line_no, line in enumerate(lines, start=1):
                    for match in regex.finditer(line):
                        matched_text = match.group(0)
                        # 检查例外
                        is_exception = any(exc in line for exc in exceptions_list)

                        hit = GrepHit(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            file=str(file_path),
                            line_no=line_no,
                            line_content=line,
                            matched_text=matched_text,
                            is_exception=is_exception,
                        )
                        if is_exception:
                            exceptions.append(hit)
                        else:
                            hits.append(hit)
                            rule_summary[rule_id] += 1

    can_publish = len(hits) == 0

    return GrepReport(
        hits=hits,
        exceptions=exceptions,
        rule_summary=rule_summary,
        can_publish=can_publish,
    )


def scan_directory(directory: Path) -> GrepReport:
    """扫描目录下所有 .md 文件。"""
    md_files = sorted(directory.glob("*.md"))
    return scan_files(md_files)
