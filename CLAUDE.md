# 课堂人脸考勤系统 - 项目指令

## 项目概述
基于摄像头人脸识别 + FAISS 向量检索 + 活体检测的课堂考勤系统。
毕设/学习项目，小规模部署（<100人，1-2间教室）。

## 技术栈
- **AI/CV**: InsightFace (buffalo_l), MediaPipe FaceMesh, FAISS
- **后端**: FastAPI + SQLModel + SQLite
- **前端**: Streamlit
- **摄像头**: OpenCV VideoCapture

## 开发规范
- 代码注释优先中文，技术术语保留英文
- 始终使用中文回复
- Python 3.10+，类型注解
- 使用 ruff 格式化代码
- 动态任务状态写入 `.ai/handoff.md`

## 模块边界
- `app/core/` — AI 模块，不依赖 FastAPI
- `app/api/` — HTTP 路由，调用 core 层
- `app/models/` — 数据模型，被 api 和 core 共享
- `ui/` — Streamlit 前端，通过 HTTP 调用后端

## 关键阈值
- 人脸相似度阈值: 0.45 (cosine similarity)
- 活体检测 EAR 阈值: 0.21
- 连续眨眼帧数: 3
