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
| ⚙️ **模型配置** | 支持 OpenAI / OpenAI 兼容 API（Ollama 等），界面直接配置 |

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

### 配置 LLM（LLM API）

启动后访问 http://localhost:3000 ，点击右上角 **⚙️** 按钮配置：

- **Provider**：选择 `OpenAI 官方` 或 `OpenAI 兼容`（Ollama、本地代理等）
- **API Key**：你的 API Key
- **Base URL**：兼容 API 的地址，如 `http://localhost:11434/v1`（Ollama 默认）
- **模型**：选择使用的模型

> 无需设置环境变量，前端界面配置会持久化到浏览器本地。

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
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 入口，17 条 API 路由
│   │   ├── config.py          # 共享配置（避免循环导入）
│   │   ├── routers/
│   │   │   ├── processes.py   # 业务流程 CRUD + 文档管理
│   │   │   ├── extraction.py # AI 知识抽取（调用 LLM）
│   │   │   └── query.py      # 知识问答 + 对话梳理
│   │   └── models/
│   │       └── schemas.py    # Pydantic 数据模型
│   └── requirements.txt
├── frontend/                   # Next.js 前端
│   └── src/
│       ├── app/               # Next.js App Router
│       ├── components/        # React 组件
│       │   ├── ProcessList.tsx
│       │   ├── ProcessDetail.tsx
│       │   ├── NewProcessDialog.tsx
│       │   ├── SettingsDialog.tsx   # LLM 设置弹窗
│       │   └── tabs/
│       │       ├── DocumentTab.tsx  # 文档上传 + AI 抽取
│       │       ├── KnowledgeTab.tsx # 知识结构查看
│       │       └── DialogueTab.tsx # 问答 + 对话梳理
│       ├── lib/api.ts         # API 客户端
│       └── types/index.ts    # TypeScript 类型
├── start.sh                   # 一键启动脚本（后端 + 前端）
└── README.md
```

**启动后：**
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 外部依赖

AI 知识抽取依赖 [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill) 仓库中的 Prompt 模板，请确保该仓库与本项目平级目录放置，或修改 `backend/app/routers/extraction.py` 中的路径：

```python
# extraction.py 第 54 行
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
| LLM | OpenAI API / OpenAI 兼容接口（Ollama 等） |
| 存储 | 本地文件系统 |