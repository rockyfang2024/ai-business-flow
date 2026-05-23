# Business Flow Skill Web

AI 驱动的业务流程知识管理平台。

## 功能

- 📋 **业务流程管理**：新建、查看、删除业务流程
- 📄 **文档上传**：上传 Markdown 文件或指定本地路径
- 🧠 **AI 知识抽取**：基于文档自动抽取结构化 YAML（主流程、决策树、异常矩阵）
- 💬 **对话式梳理**：无文档时通过多轮对话梳理业务流程
- 🔍 **知识问答**：基于已抽取的知识文档回答业务问题

## 技术栈

- **前端**：Next.js + React + TypeScript + Tailwind CSS
- **后端**：FastAPI + Python
- **存储**：本地文件系统

## 快速启动

### 前置要求

- Python 3.10+
- Node.js 18+
- OpenAI API Key（或 Anthropic API Key）

### 步骤

```bash
# 1. 克隆业务知识库（供 AI 抽取 Prompt 模板使用）
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill

# 2. 设置 API Key
export OPENAI_API_KEY=sk-...

# 3. 启动服务
./start.sh
```

启动后访问 http://localhost:3000

## 项目结构

```
business-flow-skill-web/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── routers/
│   │   │   ├── processes.py  # 业务流程 CRUD + 文档管理
│   │   │   ├── extraction.py  # AI 知识抽取 API
│   │   │   └── query.py      # 知识问答 + 对话梳理 API
│   │   └── models/
│   │       └── schemas.py    # Pydantic 数据模型
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/              # Next.js App Router
│       ├── components/       # React 组件
│       │   ├── ProcessList.tsx
│       │   ├── ProcessDetail.tsx
│       │   ├── NewProcessDialog.tsx
│       │   └── tabs/
│       │       ├── DocumentTab.tsx
│       │       ├── KnowledgeTab.tsx
│       │       └── DialogueTab.tsx
│       ├── lib/api.ts        # API 客户端
│       └── types/index.ts   # TypeScript 类型
├── data/                    # 业务流程数据（自动创建）
├── start.sh                 # 启动脚本
└── README.md
```

## 工作流程

### 方式一：基于文档抽取

```
新建流程 → 上传 Markdown 文档 → 点击「AI 知识抽取」→ 查看知识结构 → 对话问答
```

### 方式二：对话式梳理（无文档）

```
新建流程 → 切换到「对话」标签 → AI 向你提问 → 回答问题 → 自动生成 YAML
```

## API 文档

启动后端后访问：http://localhost:8000/docs