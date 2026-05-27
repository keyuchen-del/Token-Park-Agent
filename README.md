# token-park-agent

> 把"选题 → 公众号长文 + 配图 prompt + 运营手册"全流程半自动化的 Web Agent。人在四道关，机器跑掉 70% 重复劳动。

完整设计见 [DESIGN.md](./DESIGN.md) · 部署指南见 [docs/DEPLOY.md](./docs/DEPLOY.md)。

[![CI](https://github.com/keyuchen-del/Token-Park-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/keyuchen-del/Token-Park-Agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## V0.3 现状

- ✅ **后端 FastAPI**：8 个 CLI 子命令 + 7 个 REST API
- ✅ **写作风格配置化**：所有规则在 `config/` YAML，fork 改配置就能跑成自己的风格
- ✅ **6 项 grep 校验**：Python 化扫描脚本 + 18 单元测试
- ✅ **DALL-E 3 出图** + **Pillow 中文叠字** + **R2 上传**（代码骨架完成，等 key 即可跑）
- ✅ **SQLite session 持久化** + 成本统计
- ✅ **GitHub Actions CI**：ruff lint + pytest + grep smoke test，PR 不过不能 merge
- ✅ **Docker Compose 一键启动**：前后端 + 数据卷持久化
- ✅ **Railway + Vercel 部署配置**：连 GitHub 直接部署
- ✅ **Next.js 前端**：四阶段工作流 UI + session 历史页

---

## 5 分钟跑通（本地）

### 准备
- macOS / Linux / Windows
- Docker Desktop（推荐）或 Python 3.11+ / Node 20+ 本地装

### 用 Docker（最简单）

```bash
# 1. 克隆 + 进目录
git clone https://github.com/keyuchen-del/Token-Park-Agent.git
cd Token-Park-Agent

# 2. 配置环境变量
cp .env.example .env
# 用编辑器打开 .env，填入 ANTHROPIC_API_KEY

# 3. 一键启动
docker compose up --build

# 4. 访问
open http://localhost:3000      # 前端工作流
open http://localhost:8000/docs  # 后端 API 文档
```

### 不用 Docker（本地原生）

```bash
# 后端
cd backend
uv sync
cp ../.env.example ../.env  # 填 ANTHROPIC_API_KEY
uv run uvicorn tpagent.main:app --reload --port 8000

# 前端（新开终端）
cd frontend
pnpm install
NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev
```

---

## CLI 用法

不想用 Web 界面也可以直接命令行：

```bash
cd backend && uv sync

# 拉今日热点 + 候选清单
uv run tpagent topics -d "今天 AI 圈和国内科技圈"

# 写正文 + ops 一站式
uv run tpagent write \
  -t "Anthropic 雪藏 Mythos 模型" \
  -a "AI 公司自己喊停的剧本" \
  --with-ops

# 解析 ops → 调 DALL-E 出图（需 OPENAI_API_KEY）
uv run tpagent images ./sessions/5.26/2026-05-26-xxx-ops.md

# 看历史
uv run tpagent list

# 跑 grep 扫描
uv run tpagent scan ./sessions/5.26/

# 启动 API 服务
uv run tpagent serve
```

---

## 项目结构

```
agent/
├── README.md / DESIGN.md / LICENSE
├── docker-compose.yml          一键启动前后端
├── railway.toml                后端部署配置
├── .github/workflows/ci.yml    CI: ruff + pytest + grep smoke
│
├── backend/                    Python FastAPI + CLI
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/tpagent/
│   │   ├── agents/             Claude / DALL-E Agent 包装
│   │   ├── routes/             7 个 REST API
│   │   ├── services/           ops 解析 / 文字叠加 / R2 上传
│   │   ├── grep/               6 项扫描
│   │   ├── storage/            SQLite session
│   │   ├── config_loader/      YAML 配置加载
│   │   ├── cli.py              tpagent CLI（8 子命令）
│   │   └── main.py             FastAPI 入口
│   └── tests/                  18 单元测试
│
├── frontend/                   Next.js 14 + Tailwind
│   ├── Dockerfile / vercel.json
│   ├── app/
│   │   ├── page.tsx            主页（四阶段工作流）
│   │   ├── sessions/page.tsx   历史页（自动 30s 刷新）
│   │   └── layout.tsx
│   ├── components/             MarkdownView / GrepReportView / StageProgress
│   └── lib/api.ts              API client（含全部类型定义）
│
├── config/                     ← fork 后改这里改风格
│   ├── writing-style.yaml
│   ├── grep-rules.yaml
│   ├── brand.yaml.example
│   └── prompts/
│
└── docs/DEPLOY.md
```

---

## 配置怎么改

所有写作风格、grep 规则、视觉色板都在 `config/`，**改配置不需要改代码**：

1. 复制 `config/brand.yaml.example` → `config/brand.yaml`，填账号信息
2. 改 `config/writing-style.yaml` 调禁用词、推荐词
3. 改 `config/prompts/article-writer.md` 改写作风格内核

详见 [DEPLOY.md](./docs/DEPLOY.md)。

---

## API 接口

启动后访问 `http://localhost:8000/docs` 看交互式 OpenAPI 文档：

| 接口 | 用途 | 依赖 |
|---|---|---|
| `POST /api/topics` | 拉热点 + 候选清单 | ANTHROPIC_API_KEY |
| `POST /api/write` | 写正文 + grep 校验 + 入库 | ANTHROPIC_API_KEY |
| `POST /api/ops` | 生成 ops 配套文档 | ANTHROPIC_API_KEY |
| `POST /api/images/parse` | 解析 ops，估算成本（不出图） | 无 |
| `POST /api/images/generate` | 调 DALL-E 出图 | OPENAI_API_KEY |
| `GET /api/sessions` | session 列表 | 无 |
| `GET /api/sessions/{id}` | 单条 session 详情 | 无 |

---

## 路线图

| 版本 | 内容 | 状态 |
|---|---|---|
| V0.1 | 后端 + CLI + grep 校验 | ✅ |
| V0.2 | DALL-E + Pillow 叠字 + R2 + 7 个 REST API + SQLite | ✅ |
| V0.3 | Next.js 前端 + Docker + CI + 部署配置 | ✅ |
| V0.4 | 前端实际出图按钮 + 图选择 UI + 历史详情页 | 🔜 |
| V1.0 | 公众号 API 草稿箱自动上传（可选） | 🔜 |

---

## LICENSE

MIT
