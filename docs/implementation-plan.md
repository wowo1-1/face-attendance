# 课堂人脸考勤系统 - 实施计划

## 项目信息
- **位置**: `$HOME/Documents/Code/face-attendance/`
- **规模**: 小型（<100人，1-2间教室）
- **技术栈**: Python 全栈（FastAPI + Streamlit + InsightFace + FAISS）

## Agent Team 启动命令

```bash
cd $HOME/Documents/Code/face-attendance

# 1. 创建 Team
# team-lead 创建团队并分配任务

# 2. 启动 3 个并行 agent
# agent-ai:  负责 app/core/ 和 app/utils/
# agent-api: 负责 app/api/ 和 app/models/
# agent-ui:  负责 ui/
```

---

## P1: 基础模块（并行）

### Task 1.1 — agent-api: 数据模型 + 数据库
**文件**: `app/models/schema.py`, `app/models/database.py`

定义 SQLModel 模型：
- `Student`: id, name, student_id, face_embedding_id, created_at
- `Course`: id, name, teacher, schedule
- `Attendance`: id, student_id, course_id, timestamp, status, confidence

初始化 SQLite 数据库连接。

### Task 1.2 — agent-ai: 人脸引擎
**文件**: `app/core/face_engine.py`

封装 InsightFace：
- `FaceEngine.detect(image) -> list[Face]` — 检测人脸
- `FaceEngine.encode(image, face) -> np.ndarray` — 提取 512 维 embedding
- 使用 `buffalo_l` 模型，`CPUExecutionProvider`

### Task 1.3 — agent-ai: 向量数据库
**文件**: `app/core/vector_db.py`

封装 FAISS：
- `VectorDB.add(embedding, student_id)` — 添加向量
- `VectorDB.search(embedding, top_k=1) -> (ids, scores)` — 检索
- `VectorDB.remove(student_id)` — 删除
- `VectorDB.save() / load()` — 持久化到 `data/faces.index`
- 使用 `IndexFlatIP`（内积），embedding 需 L2 归一化

---

## P2: 功能模块（并行）

### Task 2.1 — agent-ai: 活体检测
**文件**: `app/core/liveness.py`

基于 MediaPipe FaceMesh 的静默式活体检测：
- 计算 EAR (Eye Aspect Ratio)，阈值 0.21
- 检测连续 3 帧眨眼 → 判定为真人
- `LivenessDetector.check(frames) -> bool`

### Task 2.2 — agent-ai: 摄像头封装
**文件**: `app/utils/camera.py`

OpenCV 摄像头管理：
- `Camera.capture() -> np.ndarray` — 单帧采集
- `Camera.stream() -> Generator` — 连续帧流
- 支持 USB 摄像头（index=0）

### Task 2.3 — agent-api: API 路由
**文件**: `app/api/register.py`, `app/api/attend.py`, `app/api/records.py`

路由定义：
- `POST /api/register` — 上传照片 + 学生信息，注册人脸
- `POST /api/attend` — 上传照片，识别并记录考勤
- `GET /api/records` — 查询考勤记录（按课程/日期/学生）
- `GET /api/students` — 学生列表

### Task 2.4 — agent-api: 应用入口
**文件**: `main.py`, `config.py`

FastAPI 应用初始化、CORS、生命周期管理。
全局配置（阈值、路径、模型参数）。

### Task 2.5 — agent-ui: Streamlit 前端
**文件**: `ui/streamlit_app.py`

页面：
- 学生注册（摄像头拍照 + 填写信息）
- 实时考勤（摄像头识别 + 结果展示）
- 考勤记录查询（表格 + 筛选）

---

## P3: 集成联调

### Task 3.1 — team-lead: 全流程测试
- 注册流程：拍照 → 活体检测 → 编码 → 存储
- 考勤流程：拍照 → 活体检测 → 编码 → 检索 → 记录
- 查询流程：按条件查询考勤记录

### Task 3.2 — team-lead: README + 文档
- 中英双语 README
- 安装说明、使用方法、架构图

---

## 依赖清单

```
# requirements.txt
fastapi>=0.115.0
uvicorn>=0.30.0
sqlmodel>=0.0.22
insightface>=0.7.3
onnxruntime>=1.19.0
faiss-cpu>=1.8.0
mediapipe>=0.10.14
opencv-python>=4.10.0
numpy>=1.26.0
streamlit>=1.38.0
python-multipart>=0.0.9
```
