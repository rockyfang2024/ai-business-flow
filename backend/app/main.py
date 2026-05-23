"""
Business Flow Skill Web - FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from routers import processes, extraction, query

# ──────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────

app = FastAPI(title="Business Flow Skill API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# 数据目录配置
# ──────────────────────────────────────────────────────────────

BASE_DATA_DIR = Path(__file__).parent.parent.parent / "data"
BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
# 注册路由
# ──────────────────────────────────────────────────────────────

app.include_router(processes.router, prefix="/api/processes", tags=["processes"])
app.include_router(extraction.router, prefix="/api/extraction", tags=["extraction"])
app.include_router(query.router, prefix="/api/query", tags=["query"])


@app.get("/health")
def health():
    return {"status": "ok"}