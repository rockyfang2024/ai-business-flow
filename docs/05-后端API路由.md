# 05 · 后端 API 路由

> 核心实现：`backend/app/main.py` + `backend/app/routers/`

## 一、路由总览

项目共有 **23 条 API 路由**，分布在 4 个模块：

| 前缀 | 文件 | 路由数 | 职责 |
|------|------|--------|------|
| `/api/processes` | `routers/processes.py` | ~8 | 流程 CRUD + 文档管理 + 知识结构 |
| `/api/extraction` | `routers/extraction.py` | ~3 | AI 知识抽取编排器 |
| `/api/query` | `routers/query.py` | ~4 | 知识问答 + 对话梳理 + 历史 |
| `/api/config/llm` | `main.py` | 6 | LLM 配置读写 + 连接测试 |

---

## 二、Processes 路由 — `/api/processes`

> 文件：`backend/app/routers/processes.py`

### 2.1 路由列表

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| `GET` | `/` | `list[ProcessSummary]` | 列出所有业务流程 |
| `POST` | `/` | `Process` | 新建业务流程 |
| `GET` | `/{process_id}` | `Process` | 获取单个流程详情 |
| `DELETE` | `/{process_id}` | `{status}` | 删除业务流程 |
| `POST` | `/{process_id}/documents` | `{document_id}` | 上传文档 |
| `GET` | `/{process_id}/knowledge` | `KnowledgeFiles` | 获取知识文件列表 |
| `GET` | `/{process_id}/knowledge/{filename}` | 文件内容 | 读取指定知识文件 |

### 2.2 核心逻辑

**新建流程**（`POST /`）：
```python
# 创建目录结构
BASE_DATA_DIR / {process_id}/
├── documents/          # 上传的文档
├── processes/          # 抽取生成的 YAML
│   ├── main.yaml
│   ├── decision-tree.yaml
│   ├── exceptions.yaml
│   └── extraction-report.md
├── dialogue_history.json  # 对话历史
└── knowledge.json        # 知识结构（对话完成后生成）
```

**知识结构判断**（`has_knowledge`）：
```python
def has_knowledge(process_id: str) -> bool:
    pdir = BASE_DATA_DIR / process_id
    processes_dir = pdir / "processes"
    if not processes_dir.exists():
        return False
    # 存在任一知识文件即为"有知识"
    return any(processes_dir.glob("*.yaml"))
```

**`knowledge.json` 的作用**：对话式梳理完成后，对话 Agent 将 `extracted_data` 写入 `knowledge.json`。前端 KnowledgeTab 通过检查 `knowledge.json` 或 `processes/*.yaml` 是否存在来判断知识是否可用。

---

## 三、Extraction 路由 — `/api/extraction`

> 文件：`backend/app/routers/extraction.py`

### 3.1 路由列表

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| `GET` | `/{process_id}/status` | `ExtractionStatus` | 查询抽取状态 |
| `POST` | `/run` | `ExtractionStatus` | 触发 AI 文档抽取 |

### 3.2 抽取流程（`POST /run`）

```
用户提交 ExtractionRequest
        │
        ├── 1. 读取 documents/ 目录下所有 .md 文件
        ├── 2. 拼接 Prompt 模板 + 文档内容
        ├── 3. 加载 llm_config.yaml 配置
        ├── 4. create_llm_client() 创建对应 transport 的 Client
        ├── 5. 调用 LLM（temperature=0.1）
        ├── 6. 解析 YAML（从 LLM 输出中提取 ```yaml ``` 块）
        │
        ▼
生成 4 个文件：
  ├── processes/main.yaml            ← 主流程
  ├── processes/decision-tree.yaml  ← 决策树
  ├── processes/exceptions.yaml     ← 异常矩阵
  └── extraction-report.md           ← 置信度报告 + 待确认项
```

### 3.3 LLM Override 机制

```python
# ExtractionRequest 中可携带 llm override
class ExtractionRequest:
    process_id: str
    document_id: str | None = None
    llm: LLMConfigOverride | None = None  # 可选：临时覆盖全局配置

# LLMOverride 支持字段
class LLMConfigOverride:
    provider: str | None
    model: str | None
    api_key: str | None
    base_url: str | None
    temperature: float | None
    max_tokens: int | None
    reasoning_effort: str | None
```

这样可以在不改变全局配置的情况下，用不同的 Provider/Model 测试抽取效果。

### 3.4 YAML 解析逻辑

LLM 输出可能包含 3 个 YAML 块，解析使用正则：

```python
yaml_blocks = re.findall(r"```yaml\s*(.*?)```", raw_output, re.DOTALL)
# 期望：len(yaml_blocks) >= 3（main, decision-tree, exceptions）
```

---

## 四、Query 路由 — `/api/query`

> 文件：`backend/app/routers/query.py`

### 4.1 路由列表

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| `POST` | `/query` | `QueryResponse` | 基于知识文档的问答 |
| `POST` | `/dialogue` | `DialogueResponse` | 多轮对话式梳理 |
| `GET` | `/dialogue/{process_id}/history` | `{history, is_complete}` | 获取对话历史 |

### 4.2 知识问答（`POST /query`）

**前置条件**：该流程已有抽取结果（`processes/` 目录存在 YAML 文件）

```python
# 构建查询上下文
context = _load_skill_content(process_id)
# 包含：skill_md, main_yaml, decision_tree_yaml, exceptions_yaml, sla_yaml

# 构建 Prompt（ Few-shot 风格）
prompt = f"""你是一个业务知识问答助手...
## 用户问题
{question}

## 知识文档内容
### SKILL.md
{context['skill_md']}

### 主流程 (main.yaml)
```yaml
{context['main_yaml']}
```
...
"""
```

### 4.3 对话式梳理（`POST /dialogue`）

**特点**：无文档场景下，从零通过多轮对话构建业务流程知识。

```
初始系统提示（DIALOGUE_SYSTEM_PROMPT）：
  → "你是一个业务知识梳理助手..."
  → "首先请向用户介绍你的角色..."
  → "然后根据回答逐步提问..."

每次对话后检查：
  → 回复中是否包含 {"is_complete": true, "extracted_data": {...}}
  → 如果是：生成 YAML 文件 + 写 knowledge.json + 清理历史
  → 如果否：追加 user+assistant 消息到 dialogue_history.json
```

**关键变量**：
- `chat_history`：从 `dialogue_history.json` 加载的对话历史（支持 Tab 切换后继续）
- `is_complete`：LLM 在回复末尾通过 JSON 标记是否收集完毕
- `extracted_data`：包含 `main` / `decision_tree` / `exceptions` 三个结构

### 4.4 对话历史持久化机制

```
DialogueTab 组件挂载
        │
        ├── GET /api/query/dialogue/{processId}/history
        │       ← 读取 dialogue_history.json
        │       ← 返回 {history: [...], is_complete: bool}
        │
        ▼
用户发送消息
        │
        └── POST /api/query/dialogue
                ← 非完成：追加到 dialogue_history.json
                ← 完成后：写 YAML + 写 knowledge.json + 删除历史文件
```

---

## 五、LLM Config 路由 — `/api/config/llm`

> 文件：`backend/app/main.py`（直接注册在 app 上）

### 5.1 路由列表

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| `GET` | `/api/config/llm` | `LLMConfigResponse` | 获取当前配置 + 所有 Provider 列表 |
| `PATCH` | `/api/config/llm` | `{status, config}` | 部分更新配置 |
| `GET` | `/api/config/llm/providers` | `list[LLMProviderInfo]` | 获取所有 Provider 元信息 |
| `GET` | `/api/config/llm/providers/{name}` | `LLMProviderInfo` | 获取单个 Provider 详情 |
| `POST` | `/api/config/llm/test` | `{status, response}` | 测试 LLM 连接 |
| `GET` | `/api/config/llm/env-check` | `{providers: {...}}` | 检查环境变量状态 |

### 5.2 GET /api/config/llm

返回结构：

```python
class LLMConfigResponse(BaseModel):
    config: LLMConfigSchema        # 当前生效配置（来自 llm_config.yaml）
    available_providers: list[LLMProviderInfo]  # 所有 32 个 Provider 的元信息
```

前端 SettingsDialog 挂载时调用此接口，加载当前配置 + Provider 列表用于展示。

### 5.3 POST /api/config/llm/test — 连接测试

```python
class LLMConfigTestRequest(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

# 测试逻辑（优先级）
resolved_api_key = body.api_key or resolve_api_key(provider)
#               = 用户输入的 api_key
#               or llm_config.yaml 中的 api_key
#               or 环境变量 os.environ[env_var]

client = create_llm_client(provider, model, resolved_api_key, resolved_base_url)
response = client.chat(
    messages=[{"role": "user", "content": "Reply with exactly one word: ok"}],
    temperature=0.1,
    max_tokens=10,
)
```

### 5.4 GET /api/config/llm/env-check

返回每个 Provider 的环境变量状态：

```json
{
  "providers": {
    "openrouter": {"found": ["OPENROUTER_API_KEY"], "missing": []},
    "anthropic": {"found": [], "missing": ["ANTHROPIC_API_KEY"]},
    ...
  }
}
```

---

## 六、路由与前端组件对应关系

```
前端组件                    后端路由
──────────────────────────────────────────────────────
ProcessList              → GET/POST   /api/processes
ProcessList → 删除        → DELETE    /api/processes/{id}
ProcessDetail            → GET       /api/processes/{id}
DocumentTab              → POST      /api/processes/{id}/documents
KnowledgeTab            → GET       /api/processes/{id}/knowledge
KnowledgeTab → 读文件     → GET       /api/processes/{id}/knowledge/{filename}
DialogueTab              → POST      /api/query/dialogue
DialogueTab → 加载历史    → GET       /api/query/dialogue/{id}/history
QueryTab                 → POST      /api/query/query
SettingsDialog          → GET       /api/config/llm
SettingsDialog → 保存     → PATCH     /api/config/llm
SettingsDialog → 测试     → POST      /api/config/llm/test
```

---

## 七、文件存储结构

```
BASE_DATA_DIR/              ← 默认 ~/.business-flow-data/
├── {process_id}/
│   ├── documents/
│   │   ├── {uuid1}_filename.md
│   │   └── {uuid2}_another.md
│   ├── processes/
│   │   ├── main.yaml              ← AI 抽取生成
│   │   ├── decision-tree.yaml
│   │   ├── exceptions.yaml
│   │   ├── sla.yaml               ← 可能存在
│   │   └── extraction-report.md
│   ├── dialogue_history.json     ← 对话历史（文件持久化）
│   ├── knowledge.json            ← 对话完成后的结构化数据
│   └── SKILL.md                  ← 对话生成或用户上传
```

---

## 八、23 条 API 路由一览表

| # | 方法 | 路径 | 文件 |
|---|------|------|------|
| 1 | GET | `/health` | main.py |
| 2 | GET | `/api/config/llm` | main.py |
| 3 | PATCH | `/api/config/llm` | main.py |
| 4 | GET | `/api/config/llm/providers` | main.py |
| 5 | GET | `/api/config/llm/providers/{name}` | main.py |
| 6 | POST | `/api/config/llm/test` | main.py |
| 7 | GET | `/api/config/llm/env-check` | main.py |
| 8 | GET | `/api/processes` | processes.py |
| 9 | POST | `/api/processes` | processes.py |
| 10 | GET | `/api/processes/{process_id}` | processes.py |
| 11 | DELETE | `/api/processes/{process_id}` | processes.py |
| 12 | POST | `/api/processes/{process_id}/documents` | processes.py |
| 13 | GET | `/api/processes/{process_id}/knowledge` | processes.py |
| 14 | GET | `/api/processes/{process_id}/knowledge/{filename}` | processes.py |
| 15 | GET | `/api/extraction/{process_id}/status` | extraction.py |
| 16 | POST | `/api/extraction/run` | extraction.py |
| 17 | POST | `/api/query/query` | query.py |
| 18 | POST | `/api/query/dialogue` | query.py |
| 19 | GET | `/api/query/dialogue/{processId}/history` | query.py |