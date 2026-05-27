# token-park-agent

> 把"选题 → 公众号长文 + 配图 prompt + 运营手册"全流程半自动化的 Web Agent。人在四道关，机器跑掉 70% 重复劳动。

设计蓝图见 [DESIGN.md](./DESIGN.md)。

---

## V0.1 现状

当前是 **V0.1 MVP**，跑通核心主线：

- ✅ 项目骨架 + 配置驱动加载
- ✅ Claude Agent SDK 接入
- ✅ 写作风格规则配置化（迁移自 `templates/writing-style.md`）
- ✅ 6 项 grep 扫描脚本 Python 化
- ✅ CLI 工具 `tpagent`（write / scan / list 子命令）
- ✅ FastAPI 基础路由（POST /api/write、GET /api/sessions）
- ⏳ 前端 Next.js 表单（V0.2）
- ⏳ DALL-E 3 出图（V0.2）
- ⏳ 完整四阶段 UI（V0.2）

---

## 5 分钟跑通（本地）

### 准备

- macOS / Linux
- Python 3.11+
- 一个 Anthropic API key（从 [console.anthropic.com](https://console.anthropic.com/) 拿）

### 安装

```bash
# 1. 装 uv（如果还没装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 装依赖
cd backend
uv sync

# 3. 配置环境变量
cp ../.env.example ../.env
# 用编辑器打开 .env，填入 ANTHROPIC_API_KEY
```

### 跑 CLI

```bash
# 用 CLI 直接写一篇文章
uv run tpagent write \
  --topic "Anthropic 主动雪藏 Mythos 模型" \
  --material "https://www.anthropic.com/news/mythos" \
  --angle "AI 公司自己喊停的剧本"

# 输出会落在 ../articles/{M.D}/{YYYY-MM-DD}-{slug}.md
```

### 跑 API 服务

```bash
uv run uvicorn tpagent.main:app --reload --port 8000

# 然后 curl
curl -X POST http://localhost:8000/api/write \
  -H "Content-Type: application/json" \
  -d '{"topic":"Anthropic 主动雪藏 Mythos 模型","material":"https://www.anthropic.com/news/mythos","angle":"AI 公司自己喊停的剧本"}'
```

API 文档自动生成在 `http://localhost:8000/docs`。

---

## 项目结构

```
agent/
├── README.md               (本文件)
├── DESIGN.md               (完整设计蓝图)
├── .env.example            (环境变量模板)
├── .gitignore
│
├── backend/                (Python FastAPI + CLI)
│   ├── pyproject.toml
│   ├── src/tpagent/
│   │   ├── main.py         (FastAPI 入口)
│   │   ├── cli.py          (Typer CLI)
│   │   ├── settings.py     (env 配置)
│   │   ├── routes/         (API 路由)
│   │   ├── agents/         (Claude Agent 包装)
│   │   ├── grep/           (6 项扫描)
│   │   ├── config_loader/  (YAML 配置加载)
│   │   ├── models/         (Pydantic schemas)
│   │   └── storage/        (SQLite + 文件系统)
│   └── tests/
│
├── config/                 (风格规则、模板、prompts —— fork 后改这里)
│   ├── writing-style.yaml
│   ├── grep-rules.yaml
│   ├── ops-template.yaml
│   ├── visual-tokens.yaml
│   ├── brand.yaml.example
│   └── prompts/
│       ├── article-writer.md
│       └── ops-writer.md
│
├── frontend/               (Next.js V0.2 接入)
│
└── docs/
    ├── DEPLOY.md
    └── CONFIG.md
```

---

## 配置怎么改

所有写作风格、grep 规则、ops 模板都在 `config/`，**改配置不需要改代码**。

如果你想用自己的风格 fork：

1. 复制 `config/brand.yaml.example` 为 `config/brand.yaml`，填账号信息
2. 改 `config/writing-style.yaml` 里的禁用词、禁用标点、推荐口语化词组
3. 改 `config/prompts/article-writer.md` 里的"风格内核"段落

详见 [docs/CONFIG.md](./docs/CONFIG.md)。

---

## 路线图

| 版本 | 内容 |
|---|---|
| ✅ V0.1 | 后端 + CLI + grep 校验 |
| 🔜 V0.2 | DALL-E 出图 + Pillow 叠字 + R2 上传 |
| 🔜 V0.3 | Next.js 前端 + 四阶段审核 UI |
| 🔜 V0.4 | Vercel + Railway 部署脚本 + 完整开源文档 |
| 🔜 V1.0 | 公众号 API 草稿箱自动上传（可选） |

---

## LICENSE

MIT
