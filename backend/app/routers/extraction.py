"""
Extraction API — 调用 AI 从文档中抽取结构化知识

Uses the unified llm_client for multi-provider, multi-transport LLM calls.
Supports all 30 providers from hermes-agent's provider registry.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..config import BASE_DATA_DIR, resolve_api_key, resolve_base_url
from ..models.schemas import (
    ExtractionRequest,
    ExtractionStatus,
    LLMConfigOverride,
)
from ..services.llm_client import (
    create_llm_client,
    LLMCallFailed,
    LLMResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 内存中存储抽取状态（生产环境换 Redis）
_extraction_status: dict[str, ExtractionStatus] = {}


def _process_dir(process_id: str) -> Path:
    return BASE_DATA_DIR / process_id


def _parse_llm_override(llm: Optional[LLMConfigOverride], cfg: dict) -> tuple[str, str, Optional[str], Optional[str]]:
    """
    Resolve effective (provider, model, api_key, base_url) from override + config.
    Returns (provider, model, api_key, base_url).
    """
    model_cfg = cfg.get("model", {})

    # Provider
    provider = llm.provider if (llm and llm.provider) else model_cfg.get("provider", "openrouter")
    if provider == "auto":
        provider = "openrouter"

    # Model
    model = llm.model if (llm and llm.model) else model_cfg.get("default", "anthropic/claude-sonnet-4.6")
    # Strip provider prefix if embedded in model name
    if "/" in model and provider == "auto":
        parts = model.split("/", 1)
        provider = parts[0]
        model = parts[1]

    # API key: explicit > config > env
    api_key: Optional[str] = None
    if llm and llm.api_key:
        api_key = llm.api_key
    else:
        api_key = resolve_api_key(provider)

    # Base URL
    base_url: Optional[str] = None
    if llm and llm.base_url:
        base_url = llm.base_url
    else:
        base_url = resolve_base_url(provider, model_cfg.get("base_url", ""))

    return provider, model, api_key, base_url


def _run_extraction(
    process_id: str,
    document_id: Optional[str] = None,
    llm_override: Optional[LLMConfigOverride] = None,
) -> ExtractionStatus:
    """
    执行抽取流程：
      1. 读取文档内容
      2. 调用 LLM（via unified llm_client）生成 YAML
      3. 写入 processes/ 目录
    """
    # Load LLM config (already loaded at startup)
    from ..config import get_llm_config

    pdir = _process_dir(process_id)
    docs_dir = pdir / "documents"
    output_dir = pdir / "processes"

    # 收集文档内容
    if document_id:
        doc_files = [f for f in docs_dir.glob(f"{document_id}_*") if f.is_file() and f.suffix == ".md"]
    else:
        doc_files = list(docs_dir.glob("*.md"))

    if not doc_files:
        return ExtractionStatus(
            process_id=process_id,
            status="error",
            error="No documents found",
        )

    combined_content = "\n\n---\n\n".join(f.read_text(encoding="utf-8") for f in doc_files)

    # 读取 Prompt 模板
    prompt_template = (
        Path(__file__).parent.parent / "prompts" / "extraction-prompt.md"
    ).read_text(encoding="utf-8")

    full_prompt = prompt_template + "\n\n---\n\n## 原始业务文档\n\n" + combined_content

    # Resolve LLM config
    cfg = get_llm_config()
    provider, model, api_key, base_url = _parse_llm_override(llm_override, cfg)

    logger.info(f"[extraction] provider={provider} model={model} process_id={process_id}")

    # Build reasoning config
    reasoning_effort = None
    if llm_override and llm_override.reasoning_effort:
        reasoning_effort = llm_override.reasoning_effort
    else:
        reasoning_effort = cfg.get("agent", {}).get("reasoning_effort", "medium")

    # Create client
    try:
        client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )
    except Exception as exc:
        logger.error(f"Failed to create LLM client: {exc}")
        return ExtractionStatus(
            process_id=process_id,
            status="error",
            error=f"Failed to initialize LLM client: {exc}",
        )

    # Call LLM
    try:
        messages = [{"role": "user", "content": full_prompt}]
        temperature = 0.1
        max_tokens = None

        if llm_override:
            if llm_override.temperature is not None:
                temperature = llm_override.temperature
            if llm_override.max_tokens is not None:
                max_tokens = llm_override.max_tokens

        response: LLMResponse = client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw_output = response.content
    except LLMCallFailed as exc:
        logger.error(f"LLM call failed: {exc}")
        return ExtractionStatus(
            process_id=process_id,
            status="error",
            error=f"LLM call failed [{exc.provider}]: {exc.message}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during LLM call: {exc}")
        return ExtractionStatus(
            process_id=process_id,
            status="error",
            error=f"Unexpected error: {exc}",
        )

    # 解析 YAML
    yaml_blocks = re.findall(r"```yaml\s*(.*?)```", raw_output, re.DOTALL)
    if len(yaml_blocks) < 3:
        return ExtractionStatus(
            process_id=process_id,
            status="error",
            error=f"Failed to parse LLM output: expected 3 yaml blocks, got {len(yaml_blocks)}",
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # 写 main.yaml
    main_data = _safe_yaml_load(yaml_blocks[0])
    if "process" in main_data:
        main_data["process"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    else:
        main_data = {
            "process": {
                "name": pdir.name,
                "version": "1.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "steps": main_data.get("steps", []),
            }
        }
    _write_yaml(output_dir / "main.yaml", main_data)

    # 写 decision-tree.yaml
    dt_data = _safe_yaml_load(yaml_blocks[1])
    if "decision_tree" not in dt_data:
        dt_data = {"decision_tree": dt_data}
    _write_yaml(output_dir / "decision-tree.yaml", dt_data)

    # 写 exceptions.yaml
    ex_data = _safe_yaml_load(yaml_blocks[2])
    if "exceptions" not in ex_data:
        ex_data = {"exceptions": ex_data.get("exceptions", [])}
    _write_yaml(output_dir / "exceptions.yaml", ex_data)

    # 提取报告
    report_match = re.search(r"## 置信度报告\s*\n(.*?)(?=\n##|\Z)", raw_output, re.DOTALL)
    pending_match = re.search(r"## 待人工确认\s*\n(.*)", raw_output, re.DOTALL)

    confidence_report = report_match.group(1).strip() if report_match else ""
    pending_items = pending_match.group(1).strip() if pending_match else ""

    # 写 extraction-report.md
    report_lines = [
        "# AI 抽取报告",
        f"**业务流程**: {pdir.name}",
        f"**抽取日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Provider**: {provider}",
        f"**Model**: {model}",
        "",
        "## 置信度报告",
        confidence_report or "_（无）_",
        "",
        "## 待人工确认",
        pending_items or "_（无）_",
    ]
    (pdir / "extraction-report.md").write_text("\n".join(report_lines), encoding="utf-8")

    return ExtractionStatus(
        process_id=process_id,
        status="done",
        progress="抽取完成",
        confidence_report=confidence_report,
        pending_items=pending_items,
    )


def _safe_yaml_load(content: str):
    try:
        return __import__("yaml").safe_load(content) or {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: dict):
    import yaml
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


@router.get("/{process_id}/status", response_model=ExtractionStatus)
def get_extraction_status(process_id: str):
    """查询当前抽取状态。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    if process_id not in _extraction_status:
        # 已有抽取结果算 done
        has_processes = (pdir / "processes").exists()
        return ExtractionStatus(
            process_id=process_id,
            status="done" if has_processes else "idle",
        )
    return _extraction_status[process_id]


@router.post("/run", response_model=ExtractionStatus)
def run_extraction(body: ExtractionRequest):
    """
    触发 AI 文档抽取。

    document_id 可选，不传则使用该流程下所有已上传文档。

    llm override 可选，支持临时指定 provider/model/credentials，
    不传则使用全局 llm_config.yaml 中的配置。
    """
    pdir = _process_dir(body.process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    status = ExtractionStatus(process_id=body.process_id, status="running", progress="正在调用 AI 抽取...")
    _extraction_status[body.process_id] = status

    try:
        result = _run_extraction(
            process_id=body.process_id,
            document_id=body.document_id,
            llm_override=body.llm,
        )
        _extraction_status[body.process_id] = result
        return result
    except Exception as e:
        err = ExtractionStatus(process_id=body.process_id, status="error", error=str(e))
        _extraction_status[body.process_id] = err
        return err