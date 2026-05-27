import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Token 公园 · 内容生产 Agent",
  description: "选题 → 公众号长文 + 配图 prompt + 运营手册，全流程半自动化",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-border bg-canvas/80 backdrop-blur sticky top-0 z-10">
            <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-ink">
                  Token 公园
                  <span className="ml-2 text-sm font-normal text-muted">
                    · 内容生产 Agent
                  </span>
                </h1>
              </div>
              <nav className="flex items-center gap-4 text-sm">
                <a
                  href="/"
                  className="text-ink hover:text-accent transition"
                >
                  写作
                </a>
                <a
                  href="/sessions"
                  className="text-ink hover:text-accent transition"
                >
                  历史
                </a>
                <a
                  href="https://github.com/keyuchen-del/Token-Park-Agent"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted hover:text-accent transition"
                >
                  GitHub ↗
                </a>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-border bg-surface/30">
            <div className="max-w-6xl mx-auto px-6 py-4 text-center text-xs text-muted">
              token-park-agent · MIT License · 开源在{" "}
              <a
                href="https://github.com/keyuchen-del/Token-Park-Agent"
                className="underline hover:text-accent"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
