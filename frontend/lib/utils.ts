import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const hour = d.getHours().toString().padStart(2, "0");
  const min = d.getMinutes().toString().padStart(2, "0");
  return `${month}/${day} ${hour}:${min}`;
}

export function stageLabel(stage: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    topic: { label: "选题", color: "bg-canvas border border-border text-muted" },
    article: { label: "初稿", color: "bg-surface text-ink" },
    ops: { label: "ops", color: "bg-accent/10 text-accent-strong" },
    images: { label: "图片", color: "bg-accent/20 text-accent-strong" },
    ready: { label: "待发", color: "bg-accent/30 text-accent-strong" },
    published: { label: "已发", color: "bg-accent text-canvas" },
  };
  return map[stage] || { label: stage, color: "bg-canvas text-muted" };
}
