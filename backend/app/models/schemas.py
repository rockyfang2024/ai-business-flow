"""
Pydantic models for Business Flow Skill Web
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ──────────────────────────────────────────────────────────────
# Process（业务流程）
# ──────────────────────────────────────────────────────────────

class ProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="业务流程名称")
    description: Optional[str] = Field(None, max_length=500, description="业务流程描述")


class ProcessInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    skill_path: str  # 文件系统路径
    has_knowledge: bool = False  # 是否已有抽取出的知识文档


class ProcessListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    updated_at: datetime
    has_knowledge: bool


# ──────────────────────────────────────────────────────────────
# Document（文档）
# ──────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    path: str


class DocumentItem(BaseModel):
    id: str
    filename: str
    size: int
    uploaded_at: datetime


# ──────────────────────────────────────────────────────────────
# Extraction（抽取）
# ──────────────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    process_id: str
    document_id: Optional[str] = None  # 可选，指定文档 ID；不指定则用全部已上传文档
    llm_provider: Optional[str] = Field(default="openai")
    llm_model: Optional[str] = Field(default="gpt-4o")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)


class ExtractionStatus(BaseModel):
    process_id: str
    status: str  # idle | running | done | error
    progress: Optional[str] = None
    confidence_report: Optional[str] = None
    pending_items: Optional[str] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Query（查询）
# ──────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    process_id: str
    question: str = Field(..., min_length=1)
    llm_provider: Optional[str] = Field(default="openai")
    llm_model: Optional[str] = Field(default="gpt-4o")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Dialogue（对话式梳理 - 多轮）
# ──────────────────────────────────────────────────────────────

class DialogueTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class DialogueRequest(BaseModel):
    process_id: str
    message: str
    history: list[DialogueTurn] = Field(default_factory=list)
    llm_provider: Optional[str] = Field(default="openai")
    llm_model: Optional[str] = Field(default="gpt-4o")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)


class DialogueResponse(BaseModel):
    reply: str
    is_complete: bool = False  # True = AI 已收集完所有必要信息，可以生成 YAML
    extracted_data: Optional[dict] = None  # 当 is_complete=True 时，返回已抽取的数据