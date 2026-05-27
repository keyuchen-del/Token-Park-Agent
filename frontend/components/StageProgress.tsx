"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type Stage = "topic" | "article" | "ops" | "images" | "ready";

const STAGES: { id: Stage; label: string; desc: string }[] = [
  { id: "topic", label: "选题", desc: "拉热点 + 候选清单" },
  { id: "article", label: "初稿", desc: "写正文 + grep 校验" },
  { id: "ops", label: "ops", desc: "图运营合一文档" },
  { id: "images", label: "图片", desc: "DALL-E 出图候选" },
  { id: "ready", label: "下载", desc: "打包 + 发布" },
];

export function StageProgress({
  current,
}: {
  current: Stage | "idle";
}) {
  const currentIdx = STAGES.findIndex((s) => s.id === current);
  return (
    <ol className="flex items-center justify-between gap-2 py-4 px-2 overflow-x-auto">
      {STAGES.map((s, i) => {
        const done = currentIdx > i;
        const active = currentIdx === i;
        return (
          <li key={s.id} className="flex-1 flex items-center min-w-0">
            <div className="flex flex-col items-center min-w-0 flex-1">
              <div
                className={cn(
                  "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0",
                  done && "bg-accent text-canvas",
                  active && "bg-accent-strong text-canvas ring-4 ring-accent/30",
                  !done && !active && "bg-surface text-muted border border-border",
                )}
              >
                {done ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <div className="mt-2 text-center">
                <div
                  className={cn(
                    "text-sm font-medium",
                    active ? "text-ink" : "text-muted",
                  )}
                >
                  {s.label}
                </div>
                <div className="text-xs text-muted/80 hidden sm:block">
                  {s.desc}
                </div>
              </div>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className={cn(
                  "h-px flex-shrink-0 w-6 mx-1 self-start mt-4",
                  done ? "bg-accent" : "bg-border",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
