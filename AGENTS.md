# Agent 协作规范

## Team 结构

| Agent | 职责 | 模块 |
|-------|------|------|
| team-lead | 任务分配、代码审查、集成协调 | 全局 |
| agent-ai | 人脸编码、向量检索、活体检测 | `app/core/`, `app/utils/` |
| agent-api | FastAPI 路由、数据模型、业务逻辑 | `app/api/`, `app/models/` |
| agent-ui | Streamlit 前端界面 | `ui/` |

## 协作规则
1. 每个 agent 只修改自己负责的模块目录
2. 共享接口通过 `app/models/schema.py` 定义，修改需 team-lead 审批
3. 完成任务后更新 `.ai/handoff.md` 并标记 task completed
4. 遇到跨模块依赖时，通过 SendMessage 通知相关 agent

## 开发阶段
- **P1**: agent-ai 完成 face_engine + vector_db，agent-api 完成 schema + DB 初始化（并行）
- **P2**: agent-ai 完成 liveness + camera，agent-api 完成路由，agent-ui 开始页面（并行）
- **P3**: 集成联调（协作）
