# AI Business Flow

<p>

**English** · [中文](README.md)

</p>

<p>

AI-powered business process knowledge management — convert scattered documents into structured, actionable knowledge with multi-LLM support.

</p>

<p>

**Key differentiator**: Extracts structured YAML (main flow · decision tree · exception matrix) — not just natural language — from your business documents.

</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📋 **Process Management** | Create, view, delete business processes |
| 📄 **Document Upload** | Upload `.md` files or link local file paths |
| 🧠 **AI Knowledge Extraction** | Automatically extract structured YAML from uploaded documents |
| 💬 **Dialog-based Structuring** | Build process structure from scratch via multi-turn AI dialogue |
| 🔍 **Knowledge Q&A** | Ask questions against extracted structured knowledge |
| ⚙️ **32 LLM Providers** | Configure any provider directly in the UI — no env vars needed |

---

## 🤖 Supported LLM Providers

| Category | Providers |
|----------|-----------|
| **OpenRouter** | 200+ models via unified gateway |
| **Anthropic / AWS** | `anthropic` · `bedrock` · `copilot` |
| **Google** | `gemini` · `google-gemini-cli` |
| **Chinese Models** | `deepseek` · `kimi` · `alibaba` (DashScope/Qwen) · `xiaomi` · `minimax` · `stepfun` |
| **Open Source** | `huggingface` · `ollama-cloud` · `custom` (LM Studio / vLLM / Ollama) |
| **Other** | `nvidia` (NIM) · `nous` · `zai` · `arcee` · `ai-gateway` |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill) (extraction prompt templates, cloned separately)

### One-command startup

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
./start.sh
```

> Access **http://localhost:3000** after startup.

### Docker

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
docker compose up
```

---

## 📖 How It Works

### Path 1 — Document Extraction (recommended when documents already exist)

```
Upload .md file → Click "AI Knowledge Extraction" → Review generated YAML → Ask questions
```

The AI extracts into four files:

- **`main.yaml`** — Main process steps with responsibilities and SLAs
- **`decision-tree.yaml`** — Decision nodes and branching logic
- **`exceptions.yaml`** — Exception handling matrix
- **`extraction-report.md`** — Confidence report with pending items

### Path 2 — Dialog-based Structuring (no documents needed)

```
Create process → Go to "Dialogue" tab → AI asks questions → You answer → YAML auto-generated
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                            │
│                 Next.js 16 · React 19                   │
│              http://localhost:3000                       │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP / JSON
┌─────────────────────▼───────────────────────────────────┐
│                      Backend                             │
│          FastAPI · Python 3.10+ · 23 API routes          │
│              http://localhost:8000/docs                  │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌──────────┐  ┌──────────┐
   │  LLM    │  │  Local   │  │ business │
   │ Client  │  │ File     │  │ -flow-   │
   │(32 prov)│  │ Storage  │  │ skill    │
   └─────────┘  └──────────┘  └──────────┘
```

### Key Files

```
backend/
├── app/
│   ├── main.py              # FastAPI entry · CORS · 23 routes
│   ├── config.py            # Shared config + env var resolution
│   ├── llm_config.py        # 32-provider registry
│   ├── routers/
│   │   ├── processes.py     # Process CRUD + document management
│   │   ├── extraction.py    # AI knowledge extraction orchestrator
│   │   └── query.py         # Knowledge Q&A + dialog agent
│   └── services/
│       └── llm_client.py    # Factory: OpenAI / Anthropic / Bedrock / Codex
├── requirements.txt
frontend/
└── src/
    ├── app/
    ├── components/
    │   ├── ProcessList.tsx
    │   ├── ProcessDetail.tsx
    │   ├── SettingsDialog.tsx   # 32-provider config + connection test
    │   └── tabs/
    │       ├── DocumentTab.tsx
    │       ├── KnowledgeTab.tsx
    │       └── DialogueTab.tsx
    ├── lib/api.ts
    └── types/index.ts
```

---

## 🔧 Development

```bash
# Clone
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow

# Clone prompt templates
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill

# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

**URLs after startup:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🐳 Docker Deployment

```yaml
# docker-compose.yml (excerpt)
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./llm_config.yaml:/app/llm_config.yaml
      - ../business-flow-skill:/business-flow-skill
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

---

## 📄 License

Apache License 2.0 — free for commercial use, contributions welcome.

---

## 🙏 Acknowledgements

- [business-flow-skill](https://github.com/rockyfang2024/business-flow-skill) — Extraction prompt templates
- [FastAPI](https://fastapi.tiangolo.com/) · [Next.js](https://nextjs.org/) · [Anthropic](https://anthropic.com/) · [OpenAI](https://openai.com/)