# token-park-agent · 设计蓝图

> 一句话：一个把"选题 → 公众号长文 + 配图 + 运营手册"全流程半自动化的 Web Agent，人在四道关，机器跑剩下的 80% 工作量。
>
> 开源定位：Token 公园自用，同时可以被其他自媒体作者 fork 复用。

---

## 一、产品定位

### 解决什么问题

每天写一篇公众号长文的工作流大概是：

```
找选题（30 分钟刷热点）
→ 核事实（20 分钟搜资料）
→ 写正文（90 分钟，含改稿）
→ 出配图 prompt（10 分钟）
→ 调 AI 出图 + 后期叠字（30 分钟）
→ 写运营手册（20 分钟）
→ 跑发布前 grep（5 分钟）
→ 人工上传公众号后台（10 分钟）
```

合计每天 **3-4 小时**。其中**重复劳动**约 70%——拉热点、写 ops 模板、跑 grep 这些每天都做同样的事。

**token-park-agent 把这 70% 砍掉**，留 30% 给人做最重要的判断：选题、独家观点、图片审美、最终决定要不要发。

### 核心设计哲学

1. **人在环（Human-in-the-Loop）**：四道关都让人审，绝不全自动发布
2. **可复用开源**：其他自媒体作者拿 README 5 分钟跑通
3. **风格可配置**：写作风格规则、色板、字体、模板都是配置项，不是硬编码
4. **失败优雅**：API 限流 / 模型出错 / 网络中断 都能恢复，不丢工作进度

---

## 二、整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                         前端 (Next.js)                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │ 阶段 1  │→ │ 阶段 2  │→ │ 阶段 3  │→ │ 阶段 4  │→ │ 完成    │  │
│  │ 选题待审│  │ 初稿待审│  │ 图片待选│  │ 上传待审│  │ 已归档  │  │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  │
│       ↑           ↑           ↑           ↑           ↑       │
│       │           │           │           │           │       │
│   人审决策    人审修改     人审选图    人审下载      自归档     │
└───────┼───────────┼───────────┼───────────┼───────────┼──────┘
        │           │           │           │           │
        ↓           ↓           ↓           ↓           ↓
┌──────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI + Claude Agent SDK)           │
│  ┌──────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐ ┌───────┐    │
│  │研究/拉热点│ │写作引擎  │ │图像生成 │ │grep 校验 │ │打包归档│    │
│  │  (Web    │ │ (Claude  │ │ (DALL-E│ │ (本地    │ │ (zip   │    │
│  │   Search)│ │  Agent)  │ │  3 API)│ │  脚本)   │ │  + R2)│    │
│  └──────────┘ └─────────┘ └────────┘ └─────────┘ └───────┘    │
│       │           │           │           │           │       │
└───────┼───────────┼───────────┼───────────┼───────────┼──────┘
        │           │           │           │           │
        └───────────┴───────────┴───────────┴───────────┘
                              ↓
                  ┌─────────────────────┐
                  │     存储层           │
                  │  ┌────────────────┐ │
                  │  │ SQLite (会话)   │ │
                  │  │ 文件系统 (产物) │ │
                  │  │ Cloudflare R2 / │ │
                  │  │  S3 (图片 CDN)  │ │
                  │  └────────────────┘ │
                  └─────────────────────┘
```

---

## 三、四阶段数据流

### 阶段 1 — 选题待审（输入端）

**用户操作**：在表单提交三件套（选题 + 链接 / 素材 + 特殊要求）

**Agent 自动做**：
1. WebSearch 拉相关事实（如选题是 AI 热点，先调 aihot 失败再 fallback WebSearch）
2. 整理 5-10 个候选选题 + 一句话事实概要 + 角度建议 + 风险提示
3. 推荐 Top 3，标注推荐理由

**人审决策**：
- 用户在 Web 上看候选清单 → 点选 1 个或自己输入新选题 → 提交角度偏好

**产物**：`session/{session-id}/01-topic.json`

---

### 阶段 2 — 初稿待审

**Agent 自动做**：
1. 按 `writing-style.md` 写正文
2. 跑 6 项 grep 扫描（跨日期 / AI 高频词 / 半括号 / 模板连词 / 卡兹克标志 / AI 标题）
3. 任何命中自动修复后再跑一遍
4. 输出 `articles/{M.D}/{YYYY-MM-DD}-{slug}.md`

**人审修改**：
- Web 显示正文 markdown 预览
- 提供"改某一段"、"换某个比喻"、"再来一稿"按钮
- 用户满意后点"通过"，进入阶段 3

**产物**：`session/{session-id}/02-article.md`

---

### 阶段 3 — 图片待选

**Agent 自动做**：
1. 按 `article-ops-template.md` 写 ops 文档（含整体风格指南 + 每张 AI 生图的中英双语 image2 prompt）
2. 对每张 ⭐ 必配图调用 **DALL-E 3 API**，每张生成 **3 个候选**
3. 用 `sharp` / `canvas` 库自动给图叠中文文字（避开 DALL-E 中文乱码）
4. 上传到 R2 / S3，返回 URL

**人审选图**：
- Web 网格展示候选图（每张图 3 选 1）
- 不满意可以点"重生成"补出新候选
- 选完所有 ⭐ 图后点"通过"

**产物**：`session/{session-id}/03-images/*.png` + `session/{session-id}/03-ops.md`

---

### 阶段 4 — 上传待审

**Agent 自动做**：
1. 把正文 markdown 转成"公众号可粘贴的富文本"（处理段落、加粗、引用、配图位置占位）
2. 把所有选定的图打包到 zip
3. 同时输出 ops 文档作为运营 cheatsheet
4. 显示一份"发布前 checklist"（事实再核 / 邮箱替换 / 标题 A/B / 推送时间）

**人审下载**：
- Web 提供 zip 下载 + 微信文章直接预览
- 用户人工复制粘贴到公众号后台
- 用户点"已发布"标记完成

**产物**：`session/{session-id}/04-final.zip`（含 .md + .docx + 图片 + ops）

---

### 完成阶段

- Agent 把整个 session 归档到 `articles/{M.D}/`
- 触发 MEMORY 更新（记录今日发布选题，但不引用进未来文章）
- 显示一份发布后 24/48/7 天的数据追踪提醒（按 ops 文档要求）

---

## 四、技术栈

### 后端
- **Python 3.11+**
- **FastAPI**（Web 框架）
- **Claude Agent SDK**（含 prompt caching，跑长文章成本可控）
- **SQLite**（session 元数据，单文件部署友好）
- **httpx**（调 DALL-E 3、WebSearch 等外部 API）
- **Pillow / Wand**（图片后期叠字）
- **python-docx**（生成可粘贴到公众号的 docx）

### 前端
- **Next.js 14 (App Router)** + **Tailwind CSS** + **shadcn/ui**
- **React Hook Form**（表单）
- **TanStack Query**（API 调用 + 缓存）
- **react-markdown** + **rehype-highlight**（正文预览）

### 部署
- **后端**：Railway / Render / Fly.io（一键 Docker 部署）
- **前端**：Vercel
- **图片 CDN**：Cloudflare R2（10GB 免费）
- **域名**：可选自定义，否则用平台域名

### 开发工具
- **uv**（Python 包管理，10x 快于 pip）
- **pnpm**（前端包管理）
- **Docker Compose**（本地一键启动）
- **GitHub Actions**（CI / CD）

---

## 五、配置驱动设计

所有"风格相关"内容都放在 `config/` 目录，不是硬编码：

```
config/
├── writing-style.yaml        # 写作风格规则（连词、半括号、AI 高频词等）
├── grep-rules.yaml           # 6 项扫描脚本配置
├── ops-template.yaml         # ops 文档 8 节模板
├── visual-tokens.yaml        # 色板、字体、尺寸、质感规范
├── prompts/
│   ├── topic-research.md     # 选题研究阶段的 Claude prompt
│   ├── article-writer.md     # 正文写作 prompt（含 khazix-writer 等风格 skill 引用）
│   ├── ops-writer.md         # ops 文档生成 prompt
│   └── image-prompt-builder.md  # 图像 prompt 自动生成
└── brand.yaml                # 账号信息（名称、邮箱、署名、CTA 模板）
```

**为什么这样设计**：
- 其他自媒体作者 fork 后只需要改 `config/` 就能跑成自己的风格
- 风格规则改动不需要改代码
- A/B 测试不同写作风格变得简单

---

## 六、API 接口设计

```
POST /api/session                    创建新 session
GET  /api/session/{id}               查询 session 状态

POST /api/session/{id}/topic         提交选题
GET  /api/session/{id}/candidates    获取候选清单
POST /api/session/{id}/select        选定一个选题

POST /api/session/{id}/write         触发写正文
GET  /api/session/{id}/article       获取正文
POST /api/session/{id}/revise        修改正文（局部 / 重写）

POST /api/session/{id}/images        触发出图（一张或全部）
GET  /api/session/{id}/images/{key}  获取某张图的候选
POST /api/session/{id}/select-image  选定某张图的最终版

GET  /api/session/{id}/export        打包下载 zip
POST /api/session/{id}/publish       标记已发布

GET  /api/sessions                   列出历史 sessions
```

每个接口的请求 / 响应 schema 用 Pydantic 定义，自动生成 OpenAPI 文档。

---

## 七、开发路线图

### V0.1 — MVP（2-3 周）

**目标**：跑通主线，能从"输入选题"到"输出 markdown + 图"

- [ ] 后端 FastAPI 框架 + Claude Agent SDK 调通
- [ ] 配置驱动加载（YAML → 内存）
- [ ] 阶段 1+2 主线：选题输入 → 候选清单 → 写文 → grep 扫描 → 输出 .md
- [ ] 前端最小表单 + 进度展示
- [ ] **不接图**，先用 placeholder
- [ ] 本地 Docker Compose 跑通

**交付物**：能在本地跑通端到端，输出一份正文 .md

### V0.2 — 图像接入（1 周）

- [ ] DALL-E 3 API 接入
- [ ] Pillow 中文字叠加 pipeline
- [ ] R2 / S3 上传
- [ ] 前端图片网格选择 UI

**交付物**：跑通完整四阶段，能下载 zip

### V0.3 — 部署 + 开源（1 周）

- [ ] Vercel + Railway 部署脚本
- [ ] 环境变量管理（用户填自己的 API keys）
- [ ] README + 5 分钟启动文档
- [ ] LICENSE（MIT）
- [ ] GitHub Actions CI

**交付物**：GitHub 仓库公开，README 让别人 5 分钟跑通

### V0.4 — 体验打磨（持续）

- [ ] 局部改稿功能（改一段而非全文重写）
- [ ] 图片重生成按钮
- [ ] 历史 session 列表 + 搜索
- [ ] 多账号 brand 切换
- [ ] 数据追踪面板（24/48/7 天指标）

### V1.0 — 公众号 API 自动上传（可选 · 后期）

- [ ] 公众号开发者认证打通
- [ ] 草稿箱 API 接入（cgi-bin/draft/add）
- [ ] 永久素材上传（图片）
- [ ] 用户配置可选"自动上传草稿"或"打包下载"

---

## 八、成本估算

按一天写一篇长文（含 4-5 张配图）的实际消耗：

| 项目 | 单价 | 单篇用量 | 单篇成本 |
|---|---|---|---|
| Claude API（正文 + ops + grep 重试）| Sonnet $3/$15 per MTok | ~30K input + 15K output | ~$0.32 |
| DALL-E 3 标准质量 | $0.04/张 | 5 张候选（每图 3 候选 × 1-2 张 ⭐ 图） | ~$0.40 |
| WebSearch | 包含在 Claude API 里 | - | $0 |
| R2 存储 | 10GB 免费额度 | <100MB / 篇 | $0 |
| 前后端托管 | Vercel 免费 + Railway $5/月 | - | ~$0.17/天 |
| **合计** | | | **~$0.89 / 篇** |

按每月 30 篇算：**约 $27 / 月**。

如果跟"自己人工每天 3 小时 × 30 天 = 90 小时"对比，这是按 $0.30/小时 在请人代工。

---

## 九、风险与边界

### 技术风险

| 风险 | 应对 |
|---|---|
| Claude API 限流 | exponential backoff + 多 key 轮询 |
| DALL-E 中文乱码 | 永远用 sharp / canvas 后期叠字，AI 只出底图 |
| 国内访问 OpenAI 受限 | 提供 Azure OpenAI 兼容 endpoint 配置 |
| WebSearch 拉到过时信息 | 优先调用 aihot skill（如果可访问），同时给用户事实核对环节 |
| 图床被墙 | R2 / S3 / 自建图床三选一可配置 |

### 内容风险

| 风险 | 应对 |
|---|---|
| 写出来抄袭风险 | 写作风格 + 个人触点强制要求，从设计上规避 |
| 事实错误 | 阶段 1 强制要求用户核对事实再进入阶段 2 |
| 民族情绪 / 投资建议越界 | ops 文档强制要求填"风险与禁忌"段 |
| 跨日期引用旧文 | grep 强制扫描，硬规则 |

### 开源风险

| 风险 | 应对 |
|---|---|
| 用户 API key 泄漏 | 永远只读 env，不存数据库；前端永远不暴露 |
| 配置文件含敏感信息 | `.gitignore` 默认排除 `.env` + `brand.yaml` |
| 被滥用做信息流污染号 | LICENSE 加注道德条款（虽然法律效力弱，但价值观要明确） |

---

## 十、目录结构（开发开始时建）

```
token-park-agent/
├── README.md
├── DESIGN.md（本文件）
├── LICENSE
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── routes/            # API 路由
│   │   ├── agents/            # Claude Agent SDK 包装
│   │   ├── services/          # DALL-E / R2 / WebSearch 等
│   │   ├── models/            # Pydantic schemas
│   │   ├── storage/           # SQLite + 文件系统
│   │   └── config/            # YAML 配置加载
│   ├── tests/
│   └── Dockerfile
│
├── frontend/
│   ├── package.json
│   ├── app/                   # Next.js App Router
│   ├── components/
│   ├── lib/
│   └── public/
│
├── config/
│   ├── writing-style.yaml
│   ├── grep-rules.yaml
│   ├── ops-template.yaml
│   ├── visual-tokens.yaml
│   ├── prompts/
│   └── brand.yaml.example
│
└── docs/
    ├── DEPLOY.md
    ├── CONFIG.md
    └── CONTRIBUTING.md
```

---

## 十一、为什么不直接接公众号 API

启动阶段刻意不接 API 自动上传，原因：

1. **公众号未认证个人号 API 极受限**：群发接口需要订阅号认证（300 元/年）+ 实名 + 资质审核
2. **草稿箱也要认证号才能用 draft/add 接口**
3. **第一次发布失败的成本极高**（错配图、错标题、引战内容直接挂在线上）
4. **人工上传那 5-10 分钟 是值得的最后一道保险**

V1.0 后期再考虑接入，且默认提供"上传到草稿箱"而非"直接群发"。

---

## 十二、下一步

文档过完，等用户拍板，进入开发：

1. **如果同意设计** → 我开始写 V0.1 MVP 代码，先把后端 FastAPI 框架 + Claude Agent SDK 调通，跑通"选题输入 → 写文 → grep 扫描"主线
2. **如果想改设计** → 标注具体哪几条要改，我重写
3. **如果想先看 demo** → 我用 token-park 现有的 SOP 跑一遍"模拟流程"，把每个阶段的输入输出实际演示一遍，让你提前看到产品形态

无论选哪条，下次对话开始前请补一件事：

- **OpenAI API key**（用于 DALL-E 3 和 fallback 的 Claude 调用，仅本地用，不进仓库）
- **目标部署平台偏好**（Vercel + Railway / 自建 VPS / 其它）
- **GitHub 仓库准备好了吗**（要新建一个还是 fork 已有）
