# 业务知识抽取 Prompt

你是一个业务分析师。请从以下业务文档中抽取出结构化的业务流程知识，以 JSON 格式输出。

## 输出格式

```json
{
  "process_name": "流程名称",
  "process_description": "一句话描述",
  "main_steps": [
    {
      "step_id": 1,
      "step_name": "步骤名称",
      "description": "步骤描述",
      "next_step": 2
    }
  ],
  "decision_points": [
    {
      "decision_id": 1,
      "condition": "条件描述",
      "true_branch": "条件为真时的步骤",
      "false_branch": "条件为假时的步骤"
    }
  ],
  "exception_handling": [
    {
      "exception_type": "异常类型",
      "handling_method": "处理方法"
    }
  ],
  "flowchart": "```mermaid\nflowchart TD\n    A[开始] --> B[步骤1]\n```"
}
```

## 要求

1. **main_steps**: 列出所有主要步骤，包含步骤ID、名称、描述和下一步
2. **decision_points**: 识别所有决策分支，包含条件、真假分支
3. **exception_handling**: 识别异常处理流程
4. **flowchart**: 用 Mermaid 格式生成流程图（TD=Top-Down 布局）

## 业务文档

---