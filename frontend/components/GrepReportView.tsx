"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import type { GrepReport } from "@/lib/api";

const RULE_NAMES: Record<string, string> = {
  cross_date_reference: "跨日期引用",
  ai_high_freq_words: "AI 高频词",
  half_brackets: "半括号",
  templated_connectors: "模板连词",
  khazix_ending_signatures: "卡兹克结尾",
  ai_heading_smell: "AI 标题",
};

export function GrepReportView({ report }: { report: GrepReport }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">发布前 grep 扫描</h3>
        {report.can_publish ? (
          <span className="badge bg-accent/15 text-accent-strong">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            可以发布
          </span>
        ) : (
          <span className="badge bg-accent-strong text-canvas">
            <XCircle className="w-3.5 h-3.5 mr-1" />
            {report.total_hits} 处违规
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
        {Object.entries(report.rule_summary).map(([id, count]) => (
          <div
            key={id}
            className="flex items-center justify-between text-sm px-3 py-1.5 rounded bg-surface/60 border border-border"
          >
            <span className="text-muted">{RULE_NAMES[id] || id}</span>
            <span
              className={
                count === 0 ? "text-accent-strong" : "text-accent"
              }
            >
              {count === 0 ? "✓" : count}
            </span>
          </div>
        ))}
      </div>

      {report.hits.length > 0 && (
        <details open className="mb-3">
          <summary className="cursor-pointer text-sm font-medium text-accent mb-2">
            ❌ 必须修复的命中 ({report.hits.length})
          </summary>
          <ul className="space-y-2 mt-2">
            {report.hits.map((h, i) => (
              <li
                key={i}
                className="text-xs bg-accent/10 border border-accent/30 rounded px-3 py-2"
              >
                <div className="font-medium">
                  [{RULE_NAMES[h.rule_id] || h.rule_id}] 第 {h.line_no} 行
                </div>
                <div className="font-mono mt-1 text-accent-strong">
                  &ldquo;{h.matched_text}&rdquo;
                </div>
                <div className="text-muted mt-1 truncate">
                  {h.line_content.slice(0, 100)}
                </div>
              </li>
            ))}
          </ul>
        </details>
      )}

      {report.exceptions.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-medium text-muted">
            <AlertTriangle className="inline w-3.5 h-3.5 mr-1" />
            例外（需人工判断） ({report.exceptions.length})
          </summary>
          <ul className="space-y-1 mt-2">
            {report.exceptions.map((h, i) => (
              <li key={i} className="text-xs text-muted px-3 py-1">
                [{RULE_NAMES[h.rule_id] || h.rule_id}] {h.matched_text} —{" "}
                {h.line_content.slice(0, 60)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
