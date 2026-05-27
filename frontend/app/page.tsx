"use client";

import { useState } from "react";
import { Loader2, Sparkles, FileText, Image as ImageIcon } from "lucide-react";
import { api, type WriteResponse, type OpsResponse, type TopicsResponse, type ImagesParseResponse } from "@/lib/api";
import { MarkdownView } from "@/components/MarkdownView";
import { GrepReportView } from "@/components/GrepReportView";
import { StageProgress, type Stage } from "@/components/StageProgress";

type Phase = "idle" | Stage;

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 输入
  const [topic, setTopic] = useState("");
  const [angle, setAngle] = useState("");
  const [material, setMaterial] = useState("");
  const [direction, setDirection] = useState("");

  // 产物
  const [topicsResult, setTopicsResult] = useState<TopicsResponse | null>(null);
  const [writeResult, setWriteResult] = useState<WriteResponse | null>(null);
  const [opsResult, setOpsResult] = useState<OpsResponse | null>(null);
  const [imagesResult, setImagesResult] = useState<ImagesParseResponse | null>(null);

  function reset() {
    setPhase("idle");
    setTopic("");
    setAngle("");
    setMaterial("");
    setDirection("");
    setTopicsResult(null);
    setWriteResult(null);
    setOpsResult(null);
    setImagesResult(null);
    setError(null);
  }

  async function runTopics() {
    if (!direction.trim()) return;
    setBusy(true);
    setError(null);
    setPhase("topic");
    try {
      const r = await api.topics({ direction });
      setTopicsResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runWrite() {
    if (!topic.trim()) return;
    setBusy(true);
    setError(null);
    setPhase("article");
    try {
      const r = await api.write({
        topic,
        angle: angle || undefined,
        material: material || undefined,
      });
      setWriteResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runOps() {
    if (!writeResult) return;
    setBusy(true);
    setError(null);
    setPhase("ops");
    try {
      const r = await api.ops({
        article_path: writeResult.article_path,
        topic,
        session_id: writeResult.session_id ?? undefined,
      });
      setOpsResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runImagesParse() {
    if (!opsResult) return;
    setBusy(true);
    setError(null);
    setPhase("images");
    try {
      const r = await api.imagesParse(opsResult.ops_path, true);
      setImagesResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      {/* 进度条 */}
      <StageProgress current={phase} />

      {error && (
        <div className="card border-accent bg-accent/10 text-accent-strong">
          <strong>出错：</strong>
          <pre className="mt-1 text-xs whitespace-pre-wrap">{error}</pre>
        </div>
      )}

      {/* 阶段 1：选题研究（可选） */}
      <section className="card">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-bold">阶段 1 · 选题研究（可选）</h2>
        </div>
        <p className="text-sm text-muted mb-4">
          用 Claude web_search 拉今日热点 + 整理候选清单。如果你已经有明确选题可跳过。
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            placeholder="今天 AI 圈和国内科技圈"
            className="input flex-1"
            disabled={busy}
          />
          <button
            onClick={runTopics}
            disabled={busy || !direction.trim()}
            className="btn-primary"
          >
            {busy && phase === "topic" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "拉候选"
            )}
          </button>
        </div>
        {topicsResult && (
          <div className="mt-4 border-t border-border pt-4">
            <div className="text-xs text-muted mb-2">
              用了 {topicsResult.web_search_count} 次 web search ·{" "}
              {topicsResult.input_tokens.toLocaleString()} in /{" "}
              {topicsResult.output_tokens.toLocaleString()} out tokens
            </div>
            <MarkdownView content={topicsResult.candidates_markdown} />
          </div>
        )}
      </section>

      {/* 阶段 2：写正文 */}
      <section className="card">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-bold">阶段 2 · 写正文</h2>
        </div>
        <div className="space-y-3">
          <div>
            <label className="label">选题（必填）</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="例如：Anthropic 主动雪藏 Mythos 模型"
              className="input"
              disabled={busy}
            />
          </div>
          <div>
            <label className="label">切入角度（可选）</label>
            <input
              type="text"
              value={angle}
              onChange={(e) => setAngle(e.target.value)}
              placeholder="例如：AI 公司自己喊停的剧本"
              className="input"
              disabled={busy}
            />
          </div>
          <div>
            <label className="label">素材 / 信源链接（可选）</label>
            <textarea
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              placeholder="https://anthropic.com/news/mythos&#10;...其它资料粘贴在这里"
              className="input min-h-[100px] font-mono text-sm"
              disabled={busy}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={runWrite}
              disabled={busy || !topic.trim()}
              className="btn-primary"
            >
              {busy && phase === "article" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "写正文"
              )}
            </button>
            <button onClick={reset} className="btn-secondary" disabled={busy}>
              重置
            </button>
          </div>
        </div>

        {writeResult && (
          <div className="mt-5 border-t border-border pt-5 space-y-4">
            <div className="text-xs text-muted">
              session #{writeResult.session_id} · {writeResult.char_count} 字符
              · {writeResult.input_tokens.toLocaleString()} in /{" "}
              {writeResult.output_tokens.toLocaleString()} out · 缓存命中{" "}
              {writeResult.cache_read_tokens.toLocaleString()}
            </div>
            <GrepReportView report={writeResult.grep_report} />
            <details className="card" open>
              <summary className="cursor-pointer font-medium">
                📄 正文 markdown 预览
              </summary>
              <div className="mt-4">
                <MarkdownView content={writeResult.article_markdown} />
              </div>
            </details>
            <div>
              <button
                onClick={runOps}
                disabled={busy}
                className="btn-primary"
              >
                {busy && phase === "ops" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "→ 生成 ops 文档"
                )}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* 阶段 3：ops 文档 */}
      {opsResult && (
        <section className="card">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-bold">阶段 3 · ops 配套</h2>
          </div>
          <div className="text-xs text-muted mb-4">
            {opsResult.ops_path}
          </div>
          <GrepReportView report={opsResult.grep_report} />
          <details className="card mt-4">
            <summary className="cursor-pointer font-medium">
              📋 ops 文档预览
            </summary>
            <div className="mt-4">
              <MarkdownView content={opsResult.ops_markdown} />
            </div>
          </details>
          <div className="mt-4">
            <button
              onClick={runImagesParse}
              disabled={busy}
              className="btn-primary"
            >
              {busy && phase === "images" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "→ 解析图 spec"
              )}
            </button>
          </div>
        </section>
      )}

      {/* 阶段 4：图 specs */}
      {imagesResult && (
        <section className="card">
          <div className="flex items-center gap-2 mb-3">
            <ImageIcon className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-bold">阶段 4 · 图候选</h2>
          </div>
          <div className="text-sm text-muted mb-4">
            解析到 <strong>{imagesResult.specs.length}</strong> 张必配图 · 预估
            DALL-E 成本{" "}
            <strong className="text-accent-strong">
              ${imagesResult.estimated_cost_usd}
            </strong>
            （standard / 1792×1024 / 3 候选 × {imagesResult.specs.length} 图）
          </div>
          <ul className="space-y-3">
            {imagesResult.specs.map((s) => (
              <li key={s.image_id} className="border border-border rounded p-3 bg-surface/30">
                <div className="flex items-center gap-2 font-medium">
                  {s.is_required && <span className="text-accent">⭐</span>}
                  {s.image_id} · {s.image_title}
                </div>
                <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                  <div>
                    <div className="text-muted mb-1">中文 prompt:</div>
                    <div className="font-mono bg-canvas border border-border rounded p-2 max-h-24 overflow-y-auto">
                      {s.prompt_zh || <em className="text-muted">无</em>}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted mb-1">English prompt:</div>
                    <div className="font-mono bg-canvas border border-border rounded p-2 max-h-24 overflow-y-auto">
                      {s.prompt_en || <em className="text-muted">无</em>}
                    </div>
                  </div>
                </div>
                {s.negative_words && (
                  <div className="text-xs text-muted mt-2">
                    <strong>negative:</strong> {s.negative_words}
                  </div>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-4 p-3 bg-surface/60 border border-border rounded text-sm text-muted">
            💡 实际调 DALL-E 出图需要在 backend .env 里填{" "}
            <code className="font-mono text-accent">OPENAI_API_KEY</code>，
            然后调 <code className="font-mono">/api/images/generate</code> 端点
            （前端按钮 V0.4 加）。
          </div>
        </section>
      )}
    </div>
  );
}
