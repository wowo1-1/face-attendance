# 课堂人脸考勤系统

基于摄像头人脸识别 + 向量检索 + 活体检测的智能课堂考勤系统。

## 功能特性

- **人脸注册**：通过摄像头或上传照片注册学生人脸信息
- **智能考勤**：人脸识别自动签到，支持相似度阈值控制
- **活体检测**：静默式眨眼检测，防止照片/视频攻击
- **向量检索**：FAISS 高效人脸向量匹配
- **考勤查询**：按课程、学生、日期多维度查询

## 技术栈

| 模块 | 技术 |
|------|------|
| 人脸检测/编码 | InsightFace (buffalo_l) |
| 向量检索 | FAISS (IndexIDMap2 + IndexFlatIP) |
| 活体检测 | MediaPipe Face Landmarker (Tasks API) |
| 后端 | FastAPI + SQLModel + SQLite |
| 前端 | Streamlit |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端
uvicorn main:app --reload

# 启动前端（新终端）
streamlit run ui/streamlit_app.py
```

后端 API 文档：http://localhost:8000/docs

## 活体检测模型文件（MediaPipe）

本项目的活体检测使用 MediaPipe Tasks 的 FaceLandmarker，需要本地模型文件：

- 默认路径：`data/mediapipe/face_landmarker.task`
- 默认行为：不自动联网下载（避免离线/受限网络环境下“隐式卡死或抛异常”）
- 如需自动下载：设置环境变量 `FACE_ATTENDANCE_MEDIAPIPE_AUTO_DOWNLOAD=1`

## 开发与测试

```bash
# 安装运行依赖
pip install -r requirements.txt

# 安装开发/测试依赖
pip install -r requirements-dev.txt

# (可选) 使用 lockfile 复现同一套依赖版本（可能与平台/架构相关）
pip install -r requirements.lock

# 运行测试（不需要摄像头）
pytest -q

# 代码检查/格式化
ruff check .
ruff format .
```

## 项目结构

```
├── main.py                  # FastAPI 入口
├── config.py                # 全局配置
├── app/
│   ├── core/
│   │   ├── face_engine.py   # 人脸检测与编码
│   │   ├── vector_db.py     # FAISS 向量检索
│   │   └── liveness.py      # 活体检测
│   ├── api/
│   │   ├── register.py      # 注册接口
│   │   ├── attend.py        # 考勤接口
│   │   └── records.py       # 查询接口
│   └── models/
│       ├── schema.py        # 数据模型
│       └── database.py      # 数据库连接
└── ui/
    └── streamlit_app.py     # Streamlit 前端
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/register | 注册学生人脸 |
| POST | /api/attend | 人脸识别签到 |
| GET | /api/records | 查询考勤记录 |
| GET | /api/students | 学生列表 |

---

# Classroom Face Attendance System

A smart classroom attendance system based on camera face recognition + vector search + liveness detection.

## Features

- **Face Registration**: Register student faces via camera or photo upload
- **Smart Attendance**: Automatic check-in via face recognition with similarity threshold
- **Liveness Detection**: Silent blink detection to prevent photo/video spoofing
- **Vector Search**: Efficient face vector matching with FAISS
- **Attendance Query**: Multi-dimensional query by course, student, and date

## Tech Stack

| Module | Technology |
|--------|-----------|
| Face Detection/Encoding | InsightFace (buffalo_l) |
| Vector Search | FAISS (IndexIDMap2 + IndexFlatIP) |
| Liveness Detection | MediaPipe Face Landmarker (Tasks API) |
| Backend | FastAPI + SQLModel + SQLite |
| Frontend | Streamlit |

## Quick Start

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# In a new terminal
streamlit run ui/streamlit_app.py
```

API docs: http://localhost:8000/docs

## MediaPipe Model File (Liveness)

The liveness detector uses MediaPipe Tasks FaceLandmarker and expects a local model file:

- Default path: `data/mediapipe/face_landmarker.task`
- Default: no implicit network download
- To enable auto download: set `FACE_ATTENDANCE_MEDIAPIPE_AUTO_DOWNLOAD=1`

## Dev & Test

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt

# (Optional) Install the locked dependency set (may be platform-specific)
pip install -r requirements.lock

pytest -q

ruff check .
ruff format .
```
