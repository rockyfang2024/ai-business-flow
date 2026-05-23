"""
Query API + Dialogue API - 知识查询 & 对话式梳理

Uses the unified llm_client for multi-provider, multi-transport LLM calls.
Supports all 30 providers from hermes-agent's provider registry.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException

from ..config import BASE_DATA_DIR, get_llm_config, resolve_api_key, resolve_base_url
from ..models.schemas import (
    QueryRequest,
    QueryResponse,
    DialogueRequest,
    DialogueResponse,
    DialogueTurn,
    LLMConfigOverride,
)
from ..services.llm_client import (
    create_llm_client,
    chat_complete,
    LLMCallFailed,
    LLMResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 内存中存储对话历史（生产环境换持久存储）
_dialogue_history: dict[str, list[DialogueTurn]] = {}


def _process_dir(process_id: str) -> Path:
    return BASE_DATA_DIR / process_id


def _load_skill_content(process_id: str) -> dict:
    """加载指定流程的所有结构化文档内容。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    result = {
        "skill_md": "",
        "main_yaml": "",
        "decision_tree_yaml": "",
        "exceptions_yaml": "",
        "sla_yaml": "",
    }

    skill_md = pdir / "SKILL.md"
    if skill_md.exists():
        result["skill_md"] = skill_md.read_text(encoding="utf-8")

    processes_dir = pdir / "processes"
    if processes_dir.exists():
        for fname in ["main.yaml", "decision-tree.yaml", "exceptions.yaml", "sla.yaml"]:
            fpath = processes_dir / fname
            if fpath.exists():
                key = fname.replace("-", "_").replace(".yaml", "_yaml")
                result[key] = fpath.read_text(encoding="utf-8")

    return result


def _parse_llm_override(llm: Optional[LLMConfigOverride], cfg: dict) -> tuple[str, str, Optional[str], Optional[str]]:
    """Resolve effective (provider, model, api_key, base_url) from override + config."""
    model_cfg = cfg.get("model", {})

    provider = llm.provider if (llm and llm.provider) else model_cfg.get("provider", "openrouter")
    if provider == "auto":
        provider = "openrouter"

    model = llm.model if (llm and llm.model) else model_cfg.get("default", "anthropic/claude-sonnet-4.6")
    if "/" in model and provider == "openrouter":
        parts = model.split("/", 1)
        provider = parts[0]
        model = parts[1]

    api_key = None
    if llm and llm.api_key:
        api_key = llm.api_key
    else:
        api_key = resolve_api_key(provider)

    base_url: Optional[str] = None
    if llm and llm.base_url:
        base_url = llm.base_url
    else:
        base_url = resolve_base_url(provider, model_cfg.get("base_url", ""))

    return provider, model, api_key, base_url


def _build_query_prompt(question: str, context: dict) -> str:
    return f"""你是一个业务知识问答助手。你需要根据以下结构化知识文档，自主推理回答用户的问题。

## 用户问题
{question}

---

## 知识文档内容

### SKILL.md
{context.get('skill_md', '_（无）_')}

### 主流程 (main.yaml)
```yaml
{context.get('main_yaml', '_（无）_')}
```

### 决策树 (decision-tree.yaml)
```yaml
{context.get('decision_tree_yaml', '_（无）_')}
```

### 异常矩阵 (exceptions.yaml)
```yaml
{context.get('exceptions_yaml', '_（无）_')}
```

### SLA 指标 (sla.yaml)
```yaml
{context.get('sla_yaml', '_（无）_')}
```

---

## 回答要求

1. **基于文档推理**：只使用上述文档中明确提供的信息回答，不要推测
2. **直接回答**：用户想要的是直接答案，不是「请参考 XX 文档」
3. **结构化输出**：如果答案涉及步骤流程，使用编号列表
4. **标注来源**：如果某个信息点来自特定文档，在回答末尾注明「来源：main.yaml / exceptions.yaml 等」
5. **不确定时诚实说**：如果文档没有覆盖用户问题，明确告知并建议人工咨询
"""


# ──────────────────────────────────────────────────────────────
# Query Agent
# ──────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def query_knowledge(body: QueryRequest):
    """基于已有知识文档回答用户问题。"""
    pdir = _process_dir(body.process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    if not (pdir / "processes").exists():
        raise HTTPException(
            status_code=400,
            detail="No knowledge extracted yet. Please upload documents and run extraction first.",
        )

    context = _load_skill_content(body.process_id)
    prompt = _build_query_prompt(body.question, context)

    # Resolve LLM config
    cfg = get_llm_config()
    provider, model, api_key, base_url = _parse_llm_override(body.llm, cfg)

    logger.info(f"[query] provider={provider} model={model} process_id={body.process_id}")

    try:
        client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        response: LLMResponse = client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        answer = response.content
    except LLMCallFailed as exc:
        raise HTTPException(status_code=500, detail=f"LLM call failed [{exc.provider}]: {exc.message}")
    except Exception as e:
        logger.error(f"Query LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    sources = []
    if (pdir / "processes").exists():
        sources = [str(p) for p in (pdir / "processes").iterdir() if p.is_file() and p.suffix == ".yaml"]

    return QueryResponse(answer=answer, sources=sources)


# ──────────────────────────────────────────────────────────────
# Dialogue Agent（对话式梳理 - 无文档场景）
# ──────────────────────────────────────────────────────────────

DIALOGUE_SYSTEM_PROMPT = """你是一个业务知识梳理助手。你的任务是通过多轮对话，从用户那里收集业务流程的完整信息。

## 你的工作方式

1. **首先**，请向用户介绍你的角色：「我将帮助你梳理业务流程。请简单描述一下你想做的业务流程是什么？」
2. **然后**，根据用户的回答，逐步提问。优先问：
   - 流程的触发条件（谁/什么触发了这个流程？）
   - 流程的主要步骤（按顺序列出）
   - 每个步骤的涉及方（用户、系统、运营人员）
   - 每个步骤的输入和输出
   - 可能的异常情况及其处理方式
   - SLA 要求（如有时效要求）
3. **每次只问 1-2 个问题**，不要一次性问太多
4. **当你认为已收集足够信息**（主流程清晰、异常覆盖完整），告诉用户「我已经收集到足够信息，正在生成结构化文档...」
5. **当用户明确说「可以了」或「就这样」**，立即停止提问，开始生成

## 重要规则

- 用中文提问和回答
- 问题要具体、明确，避免模糊
- 如果用户提到技术细节（表名、字段名），记录下来
- 如果用户不确定某个信息，标记为「待确认」，不要强行要求
- **不要替用户做假设**，不确定就说「这个我不太确定，您可以稍后补充」

## 输出格式（当收集完毕时）

当你说「我已经收集到足够信息」时，请同时输出以下 JSON：
```json
{{"is_complete": true, "extracted_data": {{...完整的结构化抽取结果...}}}}
```

extracted_data 格式：
```yaml
main.yaml 内容（process + steps）
decision-tree.yaml 内容（decision_tree + nodes）
exceptions.yaml 内容（exceptions 列表）
```

请开始吧！"""


@router.post("/dialogue", response_model=DialogueResponse)
def dialogue梳理(body: DialogueRequest):
    """多轮对话式业务流程梳理（无需文档）。"""
    pdir = _process_dir(body.process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    # 初始化或追加对话历史
    history_key = body.process_id
    if history_key not in _dialogue_history:
        _dialogue_history[history_key] = []

    # 构建消息列表（DialogueTurn uses role: user|assistant）
    messages = [{"role": "system", "content": DIALOGUE_SYSTEM_PROMPT}]
    for turn in body.history:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": body.message})

    # Resolve LLM config
    cfg = get_llm_config()
    provider, model, api_key, base_url = _parse_llm_override(body.llm, cfg)

    logger.info(f"[dialogue] provider={provider} model={model} process_id={body.process_id}")

    # Resolve reasoning effort
    reasoning_effort = None
    if body.llm and body.llm.reasoning_effort:
        reasoning_effort = body.llm.reasoning_effort
    else:
        reasoning_effort = cfg.get("agent", {}).get("reasoning_effort")

    try:
        client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )
        response: LLMResponse = client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        raw_reply = response.content
    except LLMCallFailed as exc:
        raise HTTPException(status_code=500, detail=f"LLM call failed [{exc.provider}]: {exc.message}")
    except Exception as e:
        logger.error(f"Dialogue LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    # 检查是否收集完毕（检查 reply 中是否包含 is_complete: true）
    is_complete = False
    extracted_data = None

    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_reply, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            is_complete = parsed.get("is_complete", False)
            extracted_data = parsed.get("extracted_data")
        except Exception:
            pass

    # 如果收集完毕，将结果写入文件系统
    if is_complete and extracted_data:
        output_dir = pdir / "processes"
        output_dir.mkdir(parents=True, exist_ok=True)

        if "main" in extracted_data:
            _write_yaml(output_dir / "main.yaml", extracted_data["main"])
        if "decision_tree" in extracted_data:
            _write_yaml(output_dir / "decision-tree.yaml", extracted_data["decision_tree"])
        if "exceptions" in extracted_data:
            _write_yaml(output_dir / "exceptions.yaml", extracted_data["exceptions"])

        # 写 SKILL.md
        skill_md_content = f"# {pdir.name}\n\n用户通过对话梳理生成的业务流程文档。\n"
        (pdir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        # 清理历史
        _dialogue_history[history_key] = []

    return DialogueResponse(reply=raw_reply, is_complete=is_complete, extracted_data=extracted_data)


def _write_yaml(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)