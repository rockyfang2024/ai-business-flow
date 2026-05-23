# AI Business Flow

<p>

**[English](README_en.md)** · 中文

</p>

<p>

AI 驱动的业务流程知识管理平台——将散落的业务文档自动抽取为结构化知识，支持对话式梳理与业务问答。

</p>

<p>

**核心差异化**：从业务文档中提取的不是自然语言，而是可执行的结构化 YAML（主流程 · 决策树 · 异常矩阵）。

</p>

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📋 **业务流程管理** | 新建、查看、删除业务流程 |
| 📄 **文档上传** | 上传 Markdown 文件，或指定本地已有文件路径 |
| 🧠 **AI 知识抽取** | 从上传文档自动提取结构化 YAML |
| 💬 **对话式梳理** | 无文档时通过多轮对话逐步构建业务流程 |
| 🔍 **知识问答** | 基于已提取的结构化知识回答业务问题 |
| ⚙️ **32 个 LLM Provider** | 界面直接配置，无需环境变量 |

---

## 🤖 支持的 LLM Provider

| 类别 | Provider |
|------|-----------|
| **OpenRouter** | 200+ 模型统一入口 |
| **Anthropic / AWS** | `anthropic` · `bedrock` · `copilot` |
| **Google** | `gemini` · `google-gemini-cli` |
| **中国大模型** | `deepseek` · `kimi` · `alibaba` (DashScope/Qwen) · `xiaomi` · `minimax` · `stepfun` |
| **开源 / 本地** | `huggingface` · `ollama-cloud` · `custom` (LM Studio / vLLM / Ollama) |
| **其他** | `nvidia` (NIM) · `nous` · `zai` · `arcee` · `ai-gateway` |

---

## 🚀 快速启动

### 前置要求

- Python 3.10+
- Node.js 18+
- [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill)（知识抽取 Prompt 模板，需单独克隆）

### 一步启动

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
./start.sh
```

> 启动后访问 **http://localhost:3000**

### Docker 部署

**前置要求：** Docker + Docker Compose v2

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
docker compose up --build
```

> 启动后访问 **http://localhost:3000**，API 文档：**http://localhost:8000/docs**

**停止服务：**

```bash
docker compose down
```

**重新构建（代码变更后）：**

```bash
docker compose up --build
```

---

## 📖 工作流程

### 方式一：文档抽取（已有业务文档时）

```
上传 .md 文件 → 点击「AI 知识抽取」→ 查看生成的 YAML → 对话问答
```

AI 提取为四个文件：

- **`main.yaml`** — 主流程步骤，含职责分工和 SLA
- **`decision-tree.yaml`** — 决策节点和分支逻辑
- **`exceptions.yaml`** — 异常处理矩阵
- **`extraction-report.md`** — 置信度报告，含待确认项

### 方式二：对话式梳理（无文档，从零开始）

```
创建流程 → 切换到「对话」标签 → AI 向你提问 → 逐步回答 → YAML 自动生成
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端                                │
│                 Next.js 16 · React 19                   │
│              http://localhost:3000                       │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP / JSON
┌─────────────────────▼───────────────────────────────────┐
│                      后端                                 │
│          FastAPI · Python 3.10+ · 23 条 API 路由         │
│              http://localhost:8000/docs                   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌──────────┐  ┌──────────┐
   │  LLM    │  │  本地文件  │  │ business │
   │ Client  │  │  存储      │  │ -flow-   │
   │(32 provider)│         │  │ skill    │
   └─────────┘  └──────────┘  └──────────┘
```

### 关键文件

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口 · CORS · 23 条 API 路由
│   ├── config.py            # 共享配置 + 环境变量解析
│   ├── llm_config.py        # 32 个 Provider 注册表
│   ├── routers/
│   │   ├── processes.py     # 流程 CRUD + 文档管理
│   │   ├── extraction.py    # AI 知识抽取编排器
│   │   └── query.py         # 知识问答 + 对话梳理
│   └── services/
│       └── llm_client.py    # 工厂类：OpenAI / Anthropic / Bedrock / Codex
├── requirements.txt
frontend/
└── src/
    ├── app/
    ├── components/
    │   ├── ProcessList.tsx
    │   ├── ProcessDetail.tsx
    │   ├── SettingsDialog.tsx   # 32 Provider 配置 + 连接测试
    │   └── tabs/
    │       ├── DocumentTab.tsx
    │       ├── KnowledgeTab.tsx
    │       └── DialogueTab.tsx
    ├── lib/api.ts
    └── types/index.ts
```

---

## 🔧 开发

```bash
# 克隆本项目
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow

# 克隆知识库（供 AI 抽取使用）
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill

# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端开发（另一个终端）
cd frontend
npm install && npm run dev
```

**启动后：**
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 🐳 Docker 部署

完整的 `docker-compose.yml` 已配置好前后端服务，并包含：

| 配置项 | 说明 |
|--------|------|
| `healthcheck` | 前后端启动后自动健康检查，frontend 等 backend 就绪后才启动 |
| `abf-data` volume | 持久化后端数据目录 |
| `llm_config.yaml` read-only 挂载 | LLM 配置文件只读保护 |
| `business-flow-skill` volume | 可选：Prompt 模板目录，默认读取 `../business-flow-skill` |
| `restart: unless-stopped` | 服务崩溃后自动重启 |

详细配置见 [docker-compose.yml](docker-compose.yml)。

---

## 📄 开源协议

Apache License 2.0 — 可免费商用，欢迎贡献代码。

---

## 🙏 致谢

- [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill) — 知识抽取 Prompt 模板
- [FastAPI](https://fastapi.tiangolo.com/) · [Next.js](https://nextjs.org/) · [Anthropic](https://anthropic.com/) · [OpenAI](https://openai.com/)