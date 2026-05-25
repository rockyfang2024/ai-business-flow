# AI Business Flow 文档中心

> 项目技术文档，代码与设计对照阅读。

## 📚 文档目录

| 文档 | 内容 |
|------|------|
| **[01 - 系统总体设计](./01-系统总体设计.md)** | 系统架构、数据流向、模块关系 |
| **[02 - LLM 配置系统](./02-LLM配置系统.md)** | 32 Provider 注册表、YAML 配置加载、环境变量解析 |
| **[03 - 统一 LLM 客户端](./03-统一LLM客户端.md)** | 四大 transport 机制、工厂类、API Key 解析 |
| **[04 - 前端配置界面](./04-前端配置界面.md)** | SettingsDialog 设计、分组下拉、连接测试 |
| **[05 - 后端 API 路由](./05-后端API路由.md)** | 各 router 职责、23 条路由说明 |
| **[06 - 对话历史持久化](./06-对话历史持久化.md)** | dialogue_history.json 机制、has_knowledge 判断 |
| **[07 - Docker 部署](./07-Docker部署.md)** | 容器化架构、healthcheck、数据持久化 |
| **[08 - 项目实施检查清单](./06-项目实施检查清单.md)** | 功能点完成度核查、产品文档 vs 代码对照、待实现清单 |

## 🔗 关联文件

| 模块 | 核心文件 |
|------|----------|
| Provider 注册表 | `backend/app/llm_config.py` |
| 配置加载 | `backend/app/config.py` |
| 统一 LLM Client | `backend/app/services/llm_client.py` |
| Pydantic Schemas | `backend/app/models/schemas.py` |
| 前端配置 UI | `frontend/src/components/SettingsDialog.tsx` |
| 对话历史 | `backend/app/routers/query.py` |
| 知识结构 | `backend/app/routers/processes.py` |
| 容器编排 | `docker-compose.yml` |

## 📝 更新记录

- 2025-05-25 — 初始化文档结构