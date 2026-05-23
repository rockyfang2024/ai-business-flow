"""
Extraction API - 调用 AI 从文档中抽取结构化知识
"""

import json
import re
import subprocess
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pathlib import Path

from ..config import BASE_DATA_DIR
from ..models.schemas import ExtractionRequest, ExtractionStatus

router = APIRouter()

# 内存中存储抽取状态（生产环境换 Redis）
_extraction_status: dict[str, ExtractionStatus] = {}


def _process_dir(process_id: str) -> Path:
    return BASE_DATA_DIR / process_id


def _run_extraction(process_id: str, document_id: str | None = None,
                    llm_provider: str = "openai", llm_model: str = "gpt-4o",
                    api_key: str | None = None, base_url: str | None = None) -> ExtractionStatus:
    """
    执行抽取流程：
    1. 读取文档内容
    2. 调用 OpenAI API 生成 YAML
    3. 写入 processes/ 目录
    """
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

    # 调用 LLM 抽取（复用 extraction-prompt.md）
    prompt_template = (
        Path(__file__).parent.parent.parent.parent
        / "business-flow-skill"
        / "references"
        / "extraction-prompt.md"
    ).read_text(encoding="utf-8")

    full_prompt = prompt_template + "\n\n---\n\n## 原始业务文档\n\n" + combined_content

    # 调用 LLM
    from openai import OpenAI
    extra_kwargs = {}
    if api_key:
        extra_kwargs["api_key"] = api_key
    if base_url:
        extra_kwargs["base_url"] = base_url
    client = OpenAI(**extra_kwargs)
    response = client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.1,
    )
    raw_output = response.choices[0].message.content

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
    import yaml
    try:
        return yaml.safe_load(content) or {}
    except yaml.YAMLError:
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
    """
    pdir = _process_dir(body.process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    status = ExtractionStatus(process_id=body.process_id, status="running", progress="正在调用 AI 抽取...")
    _extraction_status[body.process_id] = status

    try:
        result = _run_extraction(
        body.process_id,
        body.document_id,
        llm_provider=body.llm_provider or "openai",
        llm_model=body.llm_model or "gpt-4o",
        api_key=body.api_key,
        base_url=body.base_url,
    )
        _extraction_status[body.process_id] = result
        return result
    except Exception as e:
        err = ExtractionStatus(process_id=body.process_id, status="error", error=str(e))
        _extraction_status[body.process_id] = err
        return err