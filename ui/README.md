# Streamlit 前端（UI）

## 中文

本目录包含课堂人脸考勤系统的 Streamlit 前端：通过 HTTP 调用后端 FastAPI，完成学生注册、考勤签到、考勤记录查询。

### 前置条件

- Python 3.10+
- 已安装项目依赖（位于仓库根目录 `requirements.txt`）
- 后端服务可访问（默认 `http://localhost:8000`）

### 安装与启动

在仓库根目录执行：

```bash
# 0) (推荐) 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 1) 安装依赖
python -m pip install -r requirements.txt

# 2) 启动后端（新终端）
uvicorn main:app --reload

# 3) 启动前端（再开一个新终端）
streamlit run ui/streamlit_app.py
```

### 后端地址与超时配置

- 默认后端地址：`http://localhost:8000`
- 后端地址输入更“容错”：
  - 可以直接填 `localhost:8000`（UI 会自动补齐 `http://`）
  - 也可以填 `http://localhost:8000/api`（如果你的后端部署在子路径；UI 会避免拼出 `/api/api/...`）
- 你可以通过两种方式覆盖：
  - UI 侧边栏 `设置 -> 后端地址`
  - 环境变量 `FACE_ATTENDANCE_API_BASE`

示例（macOS / zsh）：

```bash
export FACE_ATTENDANCE_API_BASE="http://127.0.0.1:8000"
streamlit run ui/streamlit_app.py
```

侧边栏的 `请求超时（秒）` 会影响注册/签到/查询的 requests 超时设置（用于避免卡死无反馈）。

### 功能与接口对齐（关键）

1. 学生注册
   - 调用：`POST /api/register`
   - 表单字段：`name`、`student_id`
   - 文件字段名：`file`（multipart/form-data）

2. 考勤签到
   - 调用：`POST /api/attend`
   - `course_id`：后端实现可能是 Query 参数或 multipart 表单字段（取决于后端是否使用 `Form(...)` 标注）
     UI 为了兼容两种实现，会同时发送 query + form（值相同）
   - 文件字段名：`file`（multipart/form-data）
   - 返回字段：至少包含 `confidence`；可能包含 `student_id`，也可能包含 `name`
     UI 会优先展示 `name`（若存在），否则展示 `student_id`

3. 考勤记录查询
   - 调用：`GET /api/records`
   - 可选 Query 参数：`course_id`（整数）、`student_id`（整数）、`date`（`YYYY-MM-DD`）
   - UI 中的“按日期过滤”用于实现日期可选；Streamlit 不支持 `date_input(value=None)`

### 输入/输出示例

- 图片输入：支持 `jpg/png/jpeg`（拍照或上传均可）
- 考勤签到成功时 UI 展示：
  - `student_id=<学号>`（如果后端返回）
  - `id=<数据库主键>`（如果后端返回）
  - `置信度=<confidence>`（0~1 显示百分比；否则显示原始数值）

### 常见问题排查

- 前端提示“无法连接后端服务”
  - 确认后端已启动：`uvicorn main:app --reload`
  - 确认地址正确：浏览器打开 `http://localhost:8000/docs`
  - 如果后端不在本机，改侧边栏“后端地址”或设置 `FACE_ATTENDANCE_API_BASE`
  - 如果你只填了 `localhost:8000`：UI 会自动补齐为 `http://localhost:8000`

- 前端提示“请求超时”
  - 先看后端是否卡住（CPU/GPU 占用、模型加载）
  - 临时增大侧边栏超时（例如 30-60 秒）

- 返回 `HTTP 422`（参数校验失败）
  - 检查课程 ID / 学生 ID 是否为整数
  - 如果只在“签到”接口触发 422，通常是后端对 `course_id` 的来源（Query vs Form）要求不同
    UI 已同时发送 query + form；若仍失败，请检查后端是否改了参数名或路由

- 摄像头不可用/权限问题
  - 直接使用“上传照片”路径，不依赖摄像头


## English

This folder contains the Streamlit UI for the classroom face attendance system. The UI talks to the FastAPI backend over HTTP to support registration, attendance check-in, and records query.

### Prerequisites

- Python 3.10+
- Dependencies installed (repo root `requirements.txt`)
- Backend service reachable (default `http://localhost:8000`)

### Install & Run

From the repo root:

```bash
# 0) (Recommended) Create & activate a virtualenv
python -m venv .venv
source .venv/bin/activate

# 1) Install deps
python -m pip install -r requirements.txt

# 2) Start backend (new terminal)
uvicorn main:app --reload

# 3) Start UI (another terminal)
streamlit run ui/streamlit_app.py
```

### Backend Base URL & Timeout

- Default backend base URL: `http://localhost:8000`
- The backend base URL input is more forgiving:
  - You may enter `localhost:8000` (UI will auto prefix `http://`)
  - You may enter `http://localhost:8000/api` (if your backend is mounted under a sub-path; UI will avoid `/api/api/...`)
- You can override it via:
  - Sidebar `Settings -> Backend URL`
  - Environment variable `FACE_ATTENDANCE_API_BASE`

Example (macOS / zsh):

```bash
export FACE_ATTENDANCE_API_BASE="http://127.0.0.1:8000"
streamlit run ui/streamlit_app.py
```

The sidebar `Request timeout (seconds)` controls the requests timeout for register/check-in/query, so the UI fails fast instead of hanging silently.

### UI <-> Backend Contract (Important)

1. Register student
   - `POST /api/register`
   - Form fields: `name`, `student_id`
   - File field name: `file` (multipart/form-data)

2. Attendance check-in
   - `POST /api/attend`
   - `course_id`: backend may accept it either as a query parameter or as a multipart form field (depending on whether it uses `Form(...)`)
     For compatibility, the UI sends both query + form (same value)
   - File field name: `file` (multipart/form-data)
   - Response fields: at least `confidence`; may include `student_id` and/or `name`
     UI prefers `name` when present, otherwise it shows `student_id`

3. Records query
   - `GET /api/records`
   - Optional query params: `course_id` (int), `student_id` (int), `date` (`YYYY-MM-DD`)
   - The "filter by date" toggle is used to make date optional; Streamlit does not support `date_input(value=None)`

### I/O Examples

- Image input: `jpg/png/jpeg` (either camera capture or file upload)
- On successful check-in, UI shows:
  - `student_id=<student number>` (if provided by backend)
  - `id=<DB primary key>` (if provided by backend)
  - `confidence=<confidence>` (0~1 rendered as percentage, otherwise shown as raw number)

### Troubleshooting

- UI says "Cannot connect to backend"
  - Ensure backend is running: `uvicorn main:app --reload`
  - Check `http://localhost:8000/docs`
  - If backend is remote, update the sidebar backend URL or set `FACE_ATTENDANCE_API_BASE`
  - If you entered `localhost:8000`, the UI will auto convert it to `http://localhost:8000`

- UI says "Request timed out"
  - Backend may be stuck (model loading / CPU/GPU pressure)
  - Increase sidebar timeout (e.g. 30-60 seconds) temporarily

- Getting `HTTP 422` (validation error)
  - Ensure course_id / student_id are integers
  - If 422 happens only for `/api/attend`, the backend may require `course_id` from a different place (Query vs Form)
    The UI sends both; if it still fails, check whether the backend changed param names or routes

- Camera permissions / not available
  - Use the file upload path; camera is optional
