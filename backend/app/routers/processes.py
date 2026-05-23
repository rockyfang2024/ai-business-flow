"""
Process CRUD API - 业务流程的增删改查
"""

import shutil
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pathlib import Path

from ..config import BASE_DATA_DIR
from ..models.schemas import ProcessCreate, ProcessInfo, ProcessListItem, DocumentItem

router = APIRouter()


def _process_dir(process_id: str) -> Path:
    return BASE_DATA_DIR / process_id


def _processes_list() -> list[ProcessListItem]:
    """扫描 data/ 目录，返回所有业务流程列表。"""
    results = []
    if not BASE_DATA_DIR.exists():
        return results
    for pid_dir in BASE_DATA_DIR.iterdir():
        if not pid_dir.is_dir():
            continue
        skill_md = pid_dir / "SKILL.md"
        process_yaml = pid_dir / "process.yaml"
        meta_file = pid_dir / ".meta.json"

        import json
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
            except Exception:
                pass

        # 判断是否有已抽取的知识
        has_knowledge = (
            skill_md.exists()
            or process_yaml.exists()
            or (pid_dir / "processes").exists()
        )

        results.append(ProcessListItem(
            id=pid_dir.name,
            name=meta.get("name", pid_dir.name),
            description=meta.get("description"),
            updated_at=datetime.fromisoformat(meta.get("updated_at", datetime.now().isoformat())),
            has_knowledge=has_knowledge,
        ))
    results.sort(key=lambda x: x.updated_at, reverse=True)
    return results


@router.get("", response_model=list[ProcessListItem])
def list_processes():
    """返回所有业务流程列表。"""
    return _processes_list()


@router.post("", response_model=ProcessInfo)
def create_process(body: ProcessCreate):
    """创建新的业务流程。"""
    process_id = str(uuid.uuid4())[:8]
    pdir = _process_dir(process_id)
    pdir.mkdir(parents=True, exist_ok=True)

    import json
    meta = {
        "name": body.name,
        "description": body.description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    (pdir / ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    return ProcessInfo(
        id=process_id,
        name=body.name,
        description=body.description,
        created_at=datetime.fromisoformat(meta["created_at"]),
        updated_at=datetime.fromisoformat(meta["updated_at"]),
        skill_path=str(pdir),
        has_knowledge=False,
    )


@router.get("/{process_id}", response_model=ProcessInfo)
def get_process(process_id: str):
    """获取指定业务流程详情。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    import json
    meta = {}
    meta_file = pdir / ".meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())

    has_knowledge = (pdir / "processes").exists() or (pdir / "SKILL.md").exists()

    return ProcessInfo(
        id=process_id,
        name=meta.get("name", process_id),
        description=meta.get("description"),
        created_at=datetime.fromisoformat(meta.get("created_at", datetime.now().isoformat())),
        updated_at=datetime.fromisoformat(meta.get("updated_at", datetime.now().isoformat())),
        skill_path=str(pdir),
        has_knowledge=has_knowledge,
    )


@router.delete("/{process_id}")
def delete_process(process_id: str):
    """删除指定业务流程（同时删除文件系统中的所有文件）。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    shutil.rmtree(pdir)
    return {"deleted": process_id}


# ──────────────────────────────────────────────────────────────
# Documents（文档管理）
# ──────────────────────────────────────────────────────────────

@router.get("/{process_id}/documents", response_model=list[DocumentItem])
def list_documents(process_id: str):
    """列出已上传的文档。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    docs_dir = pdir / "documents"
    if not docs_dir.exists():
        return []

    import json

    results = []
    for f in docs_dir.iterdir():
        if f.is_file():
            meta_file = f.with_suffix(".meta.json")
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                except Exception:
                    pass
            results.append(DocumentItem(
                id=f.stem,
                filename=f.name,
                size=f.stat().st_size,
                uploaded_at=datetime.fromisoformat(meta.get("uploaded_at", datetime.now().isoformat())),
            ))
    results.sort(key=lambda x: x.uploaded_at, reverse=True)
    return results


@router.post("/{process_id}/documents/upload")
def upload_document(process_id: str, filename: str, content: str):
    """
    上传 Markdown 文档内容。
    content: base64 编码的文件内容（简化处理，直接传原始文本）
    """
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    docs_dir = pdir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    import json
    doc_id = str(uuid.uuid4())[:8]
    safe_name = "".join(c if c.isalnum() or c in ".-_ " else "_" for c in filename)
    file_path = docs_dir / f"{doc_id}_{safe_name}"
    file_path.write_text(content, encoding="utf-8")

    # 写 meta
    meta = {
        "id": doc_id,
        "filename": safe_name,
        "uploaded_at": datetime.now().isoformat(),
    }
    (file_path.with_suffix(".meta.json")).write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    return {
        "id": doc_id,
        "filename": safe_name,
        "size": len(content.encode("utf-8")),
        "path": str(file_path),
    }


@router.post("/{process_id}/documents/upload-path")
def upload_document_from_path(process_id: str, path: str):
    """从服务器本地路径复制文档到业务流程目录。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    src = Path(path)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=400, detail="File not found")

    docs_dir = pdir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    import json
    doc_id = str(uuid.uuid4())[:8]
    file_name = f"{doc_id}_{src.name}"
    dest = docs_dir / file_name
    shutil.copy2(src, dest)

    meta = {
        "id": doc_id,
        "filename": src.name,
        "uploaded_at": datetime.now().isoformat(),
    }
    (dest.with_suffix(".meta.json")).write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    return {
        "id": doc_id,
        "filename": src.name,
        "size": dest.stat().st_size,
        "path": str(dest),
    }


# ──────────────────────────────────────────────────────────────
# Knowledge（知识结构）
# ──────────────────────────────────────────────────────────────

@router.get("/{process_id}/knowledge")
def get_knowledge(process_id: str):
    """返回该业务流程的所有结构化知识文档内容。"""
    pdir = _process_dir(process_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Process not found")

    result = {
        "skill_md": "",
        "main_yaml": "",
        "decision_tree_yaml": "",
        "exceptions_yaml": "",
        "sla_yaml": "",
        "extraction_report": "",
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

    report = pdir / "extraction-report.md"
    if report.exists():
        result["extraction_report"] = report.read_text(encoding="utf-8")

    return result