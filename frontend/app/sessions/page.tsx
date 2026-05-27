"use client";

import useSWR from "swr";
import { api, type Session } from "@/lib/api";
import { formatDate, stageLabel } from "@/lib/utils";
import { Loader2 } from "lucide-react";

const fetcher = () => api.listSessions(50);

export default function SessionsPage() {
  const { data, error, isLoading, mutate } = useSWR("/sessions", fetcher, {
    refreshInterval: 30000, // 30 秒自动刷新
  });

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-16 text-center">
        <Loader2 className="w-6 h-6 animate-spin mx-auto text-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="card border-accent bg-accent/10 text-accent-strong">
          <strong>加载失败：</strong> {String(error)}
          <br />
          <button onClick={() => mutate()} className="mt-2 underline">
            重试
          </button>
        </div>
      </div>
    );
  }

  const sessions = data?.sessions || [];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">历史 Sessions</h1>
        <div className="text-sm text-muted">
          共 {data?.total || 0} 条 · 每 30 秒自动刷新
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="card text-center text-muted py-16">
          还没有 session 记录。回到{" "}
          <a href="/" className="text-accent underline">
            首页
          </a>{" "}
          开始第一篇。
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface text-left text-sm">
                <th className="px-3 py-2 border border-border">ID</th>
                <th className="px-3 py-2 border border-border">时间</th>
                <th className="px-3 py-2 border border-border">选题</th>
                <th className="px-3 py-2 border border-border">阶段</th>
                <th className="px-3 py-2 border border-border text-right">
                  Grep
                </th>
                <th className="px-3 py-2 border border-border text-center">
                  可发布
                </th>
                <th className="px-3 py-2 border border-border text-right">
                  成本 $
                </th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s: Session) => {
                const stage = stageLabel(s.stage);
                return (
                  <tr key={s.id} className="hover:bg-surface/40">
                    <td className="px-3 py-2 border border-border text-muted">
                      #{s.id}
                    </td>
                    <td className="px-3 py-2 border border-border text-xs text-muted">
                      {formatDate(s.created_at)}
                    </td>
                    <td className="px-3 py-2 border border-border">
                      <div className="font-medium">{s.topic}</div>
                      {s.angle && (
                        <div className="text-xs text-muted">{s.angle}</div>
                      )}
                    </td>
                    <td className="px-3 py-2 border border-border">
                      <span className={`badge ${stage.color}`}>
                        {stage.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 border border-border text-right">
                      {s.grep_hits === 0 ? (
                        <span className="text-accent-strong">✓</span>
                      ) : (
                        <span className="text-accent">{s.grep_hits}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 border border-border text-center">
                      {s.can_publish ? "✅" : "❌"}
                    </td>
                    <td className="px-3 py-2 border border-border text-right font-mono text-xs">
                      {s.estimated_cost_usd.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
