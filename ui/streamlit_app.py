"""课堂人脸考勤系统 - Streamlit 前端"""

from __future__ import annotations

import json
import os
from datetime import date as Date
from typing import Any
from urllib.parse import urlparse

import requests
import streamlit as st

API_BASE_DEFAULT = os.environ.get("FACE_ATTENDANCE_API_BASE", "http://localhost:8000")
DEFAULT_TIMEOUT_SECONDS = 15

st.set_page_config(page_title="人脸考勤系统", layout="centered")


def _normalize_api_base(raw: str) -> str:
    """规范化 API base URL（容错输入），返回不带末尾 `/` 的形式。

    支持用户输入:
    - http://localhost:8000
    - http://localhost:8000/
    - localhost:8000  (自动补齐 http://)
    - http://localhost:8000/api  (部署在子路径时也可用)
    """
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    return value.rstrip("/")


def _validate_api_base(base: str) -> str | None:
    """返回错误信息（字符串），或 None 表示校验通过。"""
    if not base:
        return "后端地址为空"
    try:
        parsed = urlparse(base)
    except ValueError:
        return "后端地址无法解析"
    if parsed.scheme not in {"http", "https"}:
        return "后端地址必须以 http:// 或 https:// 开头"
    if not parsed.netloc:
        return "后端地址缺少 host:port（例如 http://localhost:8000）"
    return None


with st.sidebar:
    st.header("设置")
    api_base_raw = st.text_input(
        "后端地址",
        value=API_BASE_DEFAULT,
        help="例如 http://localhost:8000（可通过环境变量 FACE_ATTENDANCE_API_BASE 预设）",
    )
    api_base = _normalize_api_base(api_base_raw)
    api_base_error = _validate_api_base(api_base)
    if api_base_error:
        st.error(api_base_error)
    elif api_base != api_base_raw.strip().rstrip("/"):
        st.caption(f"将使用：`{api_base}`")
    timeout_seconds = st.number_input(
        "请求超时（秒）",
        min_value=3,
        max_value=120,
        value=DEFAULT_TIMEOUT_SECONDS,
        step=1,
    )
    st.divider()
    page = st.radio("功能导航", ["学生注册", "考勤签到", "考勤记录"])


def _make_file_payload(photo: Any) -> tuple[str, bytes, str]:
    """将 Streamlit 的 UploadedFile 转为 requests `files=` 需要的三元组。"""
    filename = getattr(photo, "name", None) or "photo.jpg"
    content_type = getattr(photo, "type", None) or "application/octet-stream"
    data = photo.getvalue()
    return filename, data, content_type


def _api_url(route: str) -> str:
    """构造完整 URL，并兼容 base 里是否已包含 /api。"""
    if api_base_error:
        raise ValueError(api_base_error)
    if not route.startswith("/"):
        route = f"/{route}"
    # 避免用户 base 已带 /api 时出现 /api/api/...
    if api_base.endswith("/api") and route.startswith("/api/"):
        return api_base + route[len("/api") :]
    return f"{api_base}{route}"


def _try_parse_json(resp: requests.Response) -> Any | None:
    try:
        return resp.json()
    except ValueError:
        return None


def _format_payload(payload: Any) -> str:
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return str(payload)


def _show_http_error(action: str, resp: requests.Response) -> None:
    st.error(f"{action}失败：HTTP {resp.status_code}")
    if resp.status_code == 422:
        st.info("HTTP 422 通常表示参数校验失败：请检查字段名/类型是否与后端一致。")
    payload = _try_parse_json(resp)
    if payload is not None:
        with st.expander("错误详情（JSON）"):
            st.code(_format_payload(payload), language="json")
    else:
        text = (resp.text or "").strip()
        if text:
            with st.expander("错误详情（Text）"):
                st.code(text, language="text")


def _requests_timeout() -> float:
    # Streamlit number_input 可能返回 int/float，这里统一转成 float 给 requests
    return float(timeout_seconds)


def _show_request_exception(action: str, exc: Exception) -> None:
    # requests 的错误类型比较多，统一入口能让 UI 错误展示更一致
    st.error(f"{action}请求失败：{exc}")
    st.caption(f"当前后端地址：`{api_base or '(空)'}`")


def _extract_attend_fields(result: Any) -> dict[str, Any]:
    """兼容不同后端版本的返回字段，抽取可展示信息。"""
    if not isinstance(result, dict):
        return {"raw": result}

    student = result.get("student") if isinstance(result.get("student"), dict) else {}

    name = result.get("name") or student.get("name")
    student_number = result.get("student_id") or student.get("student_id")
    student_db_id = result.get("id") or student.get("id")
    course_id = result.get("course_id") or student.get("course_id")

    # 置信度/相似度字段名称可能随实现变化
    confidence = (
        result.get("confidence")
        if result.get("confidence") is not None
        else result.get("similarity")
        if result.get("similarity") is not None
        else result.get("score")
    )

    return {
        "name": name,
        "student_number": student_number,
        "student_db_id": student_db_id,
        "course_id": course_id,
        "confidence": confidence,
        "message": result.get("message"),
        "raw": result,
    }


def register_page():
    """学生注册页面"""
    st.header("学生注册")
    name = st.text_input("姓名")
    student_id = st.text_input("学号")
    photo_camera = st.camera_input("拍照", key="register_camera")
    photo_upload = st.file_uploader(
        "或上传照片", type=["jpg", "png", "jpeg"], key="register_upload"
    )
    photo = photo_camera or photo_upload

    if st.button("注册"):
        name_clean = name.strip()
        student_id_clean = student_id.strip()
        if not name_clean:
            st.warning("请输入姓名")
            return
        if not student_id_clean:
            st.warning("请输入学号")
            return
        if not photo:
            st.warning("请拍照或上传照片")
            return
        try:
            filename, data, content_type = _make_file_payload(photo)
            with st.spinner("正在注册..."):
                resp = requests.post(
                    _api_url("/api/register"),
                    data={"name": name_clean, "student_id": student_id_clean},
                    files={"file": (filename, data, content_type)},
                    timeout=_requests_timeout(),
                )
            if resp.ok:
                payload = _try_parse_json(resp)
                if payload is None:
                    st.success("注册成功（后端返回非 JSON）")
                    with st.expander("返回内容（Text）"):
                        st.code((resp.text or "").strip(), language="text")
                else:
                    st.success("注册成功")
                    with st.expander("返回内容（JSON）"):
                        st.code(_format_payload(payload), language="json")
            else:
                _show_http_error("注册", resp)
        except requests.Timeout:
            st.error("注册请求超时：请检查后端是否卡住，或在侧边栏增大超时时间。")
        except requests.ConnectionError as e:
            _show_request_exception("注册", e)
        except ValueError as e:
            st.error(f"注册失败：{e}")
        except requests.RequestException as e:
            _show_request_exception("注册", e)


def attend_page():
    """考勤签到页面"""
    st.header("考勤签到")
    course_id = st.number_input("课程 ID", min_value=1, step=1)
    photo_camera = st.camera_input("拍照", key="attend_camera")
    photo_upload = st.file_uploader(
        "或上传照片", type=["jpg", "png", "jpeg"], key="attend_upload"
    )
    photo = photo_camera or photo_upload

    if st.button("签到"):
        if not photo:
            st.warning("请拍照或上传照片")
            return
        try:
            filename, data, content_type = _make_file_payload(photo)
            with st.spinner("正在签到..."):
                resp = requests.post(
                    _api_url("/api/attend"),
                    # 兼容两种后端实现：
                    # - `course_id: int` (未标注) => FastAPI 默认按 Query 参数解析
                    # - `course_id: int = Form(...)` => 需要在 multipart form 里传
                    params={"course_id": int(course_id)},
                    data={"course_id": int(course_id)},
                    files={"file": (filename, data, content_type)},
                    timeout=_requests_timeout(),
                )
            if resp.ok:
                payload = _try_parse_json(resp)
                if payload is None:
                    st.success("签到成功（后端返回非 JSON）")
                    with st.expander("返回内容（Text）"):
                        st.code((resp.text or "").strip(), language="text")
                    return

                fields = _extract_attend_fields(payload)
                name = fields.get("name")
                student_number = fields.get("student_number")
                student_db_id = fields.get("student_db_id")

                if name:
                    st.success(f"签到成功：{name}")
                else:
                    st.success("签到成功")

                # 尽量把“学生号”和“数据库 ID”都兼容展示出来
                meta_parts: list[str] = []
                if student_number is not None:
                    meta_parts.append(f"student_id={student_number}")
                if student_db_id is not None:
                    meta_parts.append(f"id={student_db_id}")
                if meta_parts:
                    st.caption("，".join(meta_parts))

                confidence_raw = fields.get("confidence")
                try:
                    confidence = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence = None

                if confidence is None:
                    if confidence_raw is not None:
                        st.metric("置信度", str(confidence_raw))
                else:
                    # 如果是 cosine similarity（0~1）就显示百分比；否则显示原始值
                    if 0.0 <= confidence <= 1.0:
                        st.metric("置信度", f"{confidence:.2%}")
                    else:
                        st.metric("置信度", f"{confidence:.4f}")

                with st.expander("返回内容（JSON）"):
                    st.code(_format_payload(fields.get("raw")), language="json")
            else:
                _show_http_error("签到", resp)
        except requests.Timeout:
            st.error("签到请求超时：请检查后端是否卡住，或在侧边栏增大超时时间。")
        except requests.ConnectionError as e:
            _show_request_exception("签到", e)
        except ValueError as e:
            st.error(f"签到失败：{e}")
        except requests.RequestException as e:
            _show_request_exception("签到", e)


def records_page():
    """考勤记录查询页面"""
    st.header("考勤记录")
    col1, col2, col3 = st.columns(3)
    course_id_raw = col1.text_input("课程 ID（可选）", key="records_course_id")
    student_id_raw = col2.text_input("学生数据库 ID（可选）", key="records_student_id")
    use_date = col3.checkbox("按日期过滤", value=False, key="records_use_date")
    selected_date = None
    if use_date:
        # Streamlit 不支持 `date_input(value=None)`；用开关实现“可选日期”
        selected_date = col3.date_input(
            "日期",
            value=Date.today(),
            max_value=Date.today(),
            key="records_date",
        )

    if st.button("查询"):
        params: dict[str, Any] = {}
        if course_id_raw.strip():
            try:
                params["course_id"] = int(course_id_raw.strip())
            except ValueError:
                st.error("课程 ID 必须是整数")
                return
        if student_id_raw.strip():
            try:
                params["student_id"] = int(student_id_raw.strip())
            except ValueError:
                st.error("学生数据库 ID 必须是整数")
                return
        if selected_date:
            params["date"] = selected_date.isoformat()
        try:
            with st.spinner("正在查询..."):
                resp = requests.get(
                    _api_url("/api/records"),
                    params=params,
                    timeout=min(_requests_timeout(), 60.0),
                )
            if resp.ok:
                payload = _try_parse_json(resp)
                if payload is None:
                    st.warning("查询成功，但后端返回非 JSON")
                    with st.expander("返回内容（Text）"):
                        st.code((resp.text or "").strip(), language="text")
                elif payload:
                    st.dataframe(payload, use_container_width=True)
                else:
                    st.info("暂无记录")
            else:
                _show_http_error("查询", resp)
        except requests.Timeout:
            st.error("查询请求超时：请检查后端是否卡住，或在侧边栏增大超时时间。")
        except requests.ConnectionError as e:
            _show_request_exception("查询", e)
        except ValueError as e:
            st.error(f"查询失败：{e}")
        except requests.RequestException as e:
            _show_request_exception("查询", e)


# 路由到对应页面
{"学生注册": register_page, "考勤签到": attend_page, "考勤记录": records_page}[page]()
