# AI Business Flow

AI 驱动的业务流程知识管理平台——将散落的业务文档自动抽取为结构化知识，支持对话式梳理与业务问答。

## 功能特性

| 功能 | 说明 |
|------|------|
| 📋 **业务流程管理** | 新建、查看、删除业务流程 |
| 📄 **文档上传** | 上传 Markdown 文件，或指定本地已有文件路径 |
| 🧠 **AI 知识抽取** | 基于文档自动抽取为主流程 YAML、决策树、异常矩阵 |
| 💬 **对话式梳理** | 无文档时通过多轮对话逐步构建业务流程结构 |
| 🔍 **知识问答** | 基于已抽取的知识结构回答业务问题 |
| ⚙️ **模型配置** | 支持 32 个 LLM Provider，界面直接配置，无需环境变量 |

### 支持的 LLM Provider

**OpenRouter 生态**
: `openrouter` — 200+ 模型统一入口，支持路由策略与响应缓存

**Anthropic / Amazon**
: `anthropic` · `bedrock` (Claude / Nova / Llama via AWS) · `copilot` · `copilot-acp`

**Google**
: `gemini` · `google-gemini-cli` (OAuth)

**OpenAI / Codex**
: `openai-codex` (Codex Responses API)

**中国大模型**
: `deepseek` · `kimi-coding` · `kimi-coding-cn` · `alibaba` (DashScope/Qwen) · `xiaomi` · `minimax` · `minimax-cn` · `stepfun` · `gmi` · `novita`

**开源 / 本地**
: `huggingface` (20+ 开源模型) · `ollama-cloud` · `kilocode` · `opencode-zen` · `opencode-go` · `custom` (LM Studio / vLLM / Ollama)

**其他**
: `nvidia` (NIM/Nemotron) · `nous` · `zai` · `arcee` · `ai-gateway` · `qwen-oauth` · `alibaba-coding-plan`

所有 Provider 均支持在每次调用时临时覆盖 API Key 和 Base URL。

## 快速部署

### 方式一：一步启动（推荐）

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
./start.sh
```

> 启动后访问 **http://localhost:3000**

---

### 方式二：手动部署

**前置要求**

- Python 3.10+
- Node.js 18+
- [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill)（知识抽取 Prompt 模板，需单独克隆）

```bash
# 1. 克隆本项目
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow

# 2. 克隆知识库（供 AI 抽取使用）
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill

# 3. 安装后端依赖
cd backend
pip install -r requirements.txt

# 4. 安装前端依赖
cd ../frontend
npm install

# 5. 启动
cd ..
./start.sh
```

---

### 配置 LLM

启动后访问 http://localhost:3000 ，点击右上角 **⚙️** 按钮配置。

支持的配置方式：
- **Provider 选择**：从 32 个预置 Provider 中选择
- **API Key**：显式传入，或通过环境变量（`OPENROUTER_API_KEY` 等）自动解析
- **Base URL**：覆盖 Provider 默认端点（如连接本地 Ollama）
- **模型别名**：为常用模型设置简短别名
- **推理Effort**：配置 thinking/reasoning 强度（`xhigh` / `high` / `medium` / `none`）

API 端点：`GET/PATCH /api/config/llm` · `POST /api/config/llm/test`（连接测试）

---

## 工作流程

### 方式一：基于文档抽取（推荐已有业务文档时）

```
新建流程 → 上传 Markdown 文档 → 点击「AI 知识抽取」→ 查看知识结构 → 对话问答
```

### 方式二：对话式梳理（无文档，从零开始）

```
新建流程 → 切换到「对话」标签 → AI 向你提问 → 逐步回答 → 自动生成结构化 YAML
```

---

## 项目结构

```
ai-business-flow/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，23 条 API 路由
│   │   ├── config.py            # 共享配置 + LLM 配置加载
│   │   ├── llm_config.py        # 32 个 Provider 注册表 + transport 解析
│   │   ├── routers/
│   │   │   ├── processes.py     # 业务流程 CRUD + 文档管理
│   │   │   ├── extraction.py    # AI 知识抽取（统一 LLM Client）
│   │   │   └── query.py         # 知识问答 + 对话梳理
│   │   ├── services/
│   │   │   └── llm_client.py    # 多 transport LLM 调用（OpenAI / Anthropic / Bedrock / Codex）
│   │   └── models/
│   │       └── schemas.py       # Pydantic 数据模型（含完整 LLM 配置结构）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       │   ├── SettingsDialog.tsx  # LLM 设置弹窗（32 Provider + 配置测试）
│       │   └── tabs/
│       ├── lib/api.ts
│       └── types/index.ts
├── start.sh
└── README.md
```

**启动后**
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 外部依赖

AI 知识抽取依赖 [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill) 仓库中的 Prompt 模板，请确保该仓库与本项目平级目录放置，或修改 `backend/app/routers/extraction.py` 中的路径：

```python
prompt_template = (
    Path(__file__).parent.parent.parent.parent
    / "business-flow-skill"
    / "references"
    / "extraction-prompt.md"
).read_text(encoding="utf-8")
```

即：`../business-flow-skill/references/extraction-prompt.md`

---

## 开发

```bash
# 后端开发（热重载）
cd backend
uvicorn app.main:app --reload --port 8000

# 前端开发（热重载）
cd frontend
npm run dev

# 前端构建
cd frontend
npm run build
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Next.js 16 + React 19 + TypeScript + CSS Modules |
| 后端 | FastAPI + Python 3.10+ |
| LLM | 32 Provider 支持（OpenAI / Anthropic / AWS Bedrock / Gemini / DeepSeek / 阿里通义 等） |
| 存储 | 本地文件系统 |