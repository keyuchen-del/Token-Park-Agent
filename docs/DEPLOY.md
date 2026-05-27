# 部署指南

token-park-agent 推荐的部署组合：

- **后端**：Railway（Dockerfile 一键部署）
- **前端**：Vercel（Next.js 原生支持）
- **图床**：Cloudflare R2（10GB 免费，按 V0.2 配置）
- **本地开发**：Docker Compose 一键启动

---

## 一、本地开发（最简单，3 行命令）

```bash
# 1. 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY 等

# 2. 一键启动（前后端 + 数据卷）
docker compose up --build

# 3. 访问
# 后端 API:   http://localhost:8000/docs
# 前端:       http://localhost:3000  （V0.3 加入前端后）
```

需要先装 Docker Desktop（macOS / Windows）或 Docker Engine（Linux）。

如果不想用 Docker，也可以本地直接跑：

```bash
# 后端
cd backend
uv sync
uv run uvicorn tpagent.main:app --reload --port 8000

# 前端（V0.3）
cd frontend
pnpm install
pnpm dev
```

---

## 二、部署到 Railway（后端）

[Railway](https://railway.app) 免费额度 $5/月，可以跑 token-park-agent 后端到挂掉为止。

### 2.1 一次性配置

1. 注册 Railway 账号 + 用 GitHub OAuth 登录
2. New Project → Deploy from GitHub repo → 选 `keyuchen-del/Token-Park-Agent`
3. Railway 自动检测到根目录 `railway.toml` + `backend/Dockerfile`
4. 进 Service Settings → Variables，添加：

```
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx          ← 跑 images 才需要
R2_ACCOUNT_ID=xxx              ← 用云端图床才需要
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET=tpagent-images
R2_PUBLIC_URL=https://your-r2-domain.example.com
```

5. Railway 会自动 build + deploy。完成后给你一个域名，如 `tpagent.up.railway.app`

### 2.2 验证

```bash
curl https://你的域名/health
# {"status":"ok"}

curl https://你的域名/api/sessions
# {"sessions":[],"total":0}
```

### 2.3 持久化

Railway 默认不持久化容器文件系统。要持久化 SQLite + sessions：

- 在 Railway service 里 attach 一个 Volume，mount 到 `/app/data`
- 数据卷大小：1GB 起步够用 6 个月

---

## 三、部署到 Vercel（前端）

V0.3 加入前端后启用。

### 3.1 一次性配置

1. 注册 Vercel 账号 + GitHub OAuth
2. Add New Project → Import Git Repository → 选 `keyuchen-del/Token-Park-Agent`
3. Root Directory 设为 `frontend`
4. Framework Preset 自动检测为 Next.js
5. Environment Variables：
   - `NEXT_PUBLIC_API_URL` = `https://你的-railway-后端.up.railway.app`
6. Deploy

完成后给你一个域名，如 `tpagent.vercel.app`。

### 3.2 自定义域名（可选）

Vercel → Project Settings → Domains → Add → 填你的域名，按指引改 DNS。

---

## 四、Cloudflare R2 图床配置

V0.2 已经写好 R2 上传服务。未配置时自动 fallback 本地存储。

### 4.1 创建 bucket

1. 注册 [Cloudflare](https://dash.cloudflare.com/) 账号（免费）
2. R2 → Create bucket → 名字 `tpagent-images`
3. Bucket → Settings → Public Access → Connect Domain（可选，绑你自己的域名做图床公开访问）

### 4.2 创建 API token

1. R2 → Manage R2 API Tokens → Create API token
2. Permissions: Object Read & Write
3. 记下：
   - Account ID
   - Access Key ID
   - Secret Access Key
4. 填进 Railway 的 Environment Variables（见上文 2.1）

### 4.3 验证

```bash
# 在已部署的后端上跑
curl -X POST https://你的域名/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{"ops_path": "/app/sessions/5.26/xxx-ops.md"}'

# 返回的 by_spec[*][*].image_path 应该是 R2 URL 而非本地路径
```

---

## 五、GitHub Actions CI

仓库已经配置好 `.github/workflows/ci.yml`：

- 每次 push / PR 自动跑 ruff lint + pytest + grep smoke test
- 矩阵覆盖 Python 3.11 / 3.13
- PR 不过不能 merge（在 GitHub Settings → Branches → Branch protection rules 里设）

### 5.1 启用 branch protection

1. GitHub repo → Settings → Branches → Add branch protection rule
2. Branch name pattern: `main`
3. 勾选：
   - [x] Require status checks to pass before merging
   - [x] 选 `Backend (Python 3.13)` + `grep 6 项扫描自检`
4. Save

之后 PR 只有 CI 全绿才能 merge。

---

## 六、成本估算

按 V0.2 用量（每天 1 篇文章 + 4 张图）：

| 项 | 月成本 |
|---|---|
| Anthropic API（文章 + ops）| ~$10 |
| OpenAI DALL-E 3（5 候选 × 1 主图）| ~$12 |
| Cloudflare R2（10GB 免费）| $0 |
| Railway 后端 hobby plan | $5 |
| Vercel 前端 hobby plan | $0 |
| **合计** | **~$27 / 月** |

如果只发周更（每月 4 篇）：约 $10/月。

---

## 七、回滚

```bash
# Railway：在 dashboard → Deployments → 点旧版本 → Redeploy
# Vercel：同理在 Project → Deployments → Promote to Production
# GitHub: git revert + push 也会触发新部署
```
