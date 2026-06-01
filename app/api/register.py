"""注册路由 — 学生人脸注册"""

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlmodel import Session
from sqlmodel import select

from app.models.database import get_session
from app.models.schema import Student

router = APIRouter(prefix="/api")


@router.post("/capture")
async def capture_photo():
    """从本地摄像头拍摄一张照片（不依赖浏览器 API）"""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise HTTPException(500, "无法打开摄像头，请检查摄像头是否已连接")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise HTTPException(500, "拍照失败，请重试")
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    student_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    # 读取上传图片
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "无法解析图片")

    # 检查学号是否已注册
    if session.exec(select(Student).where(Student.student_id == student_id)).first():
        raise HTTPException(409, "该学号已注册")

    # 提取人脸 embedding
    embedding = request.app.state.face_engine.encode(img)
    if embedding is None:
        raise HTTPException(400, "未检测到人脸")

    # 注册顺序：先写 DB 拿到 student.id，再 add 到 FAISS，避免回写 VectorDB 私有字段 _id_map。
    #
    # 这里使用 flush() 获取自增主键，但不提前 commit，这样 FAISS add 失败时可以 rollback 数据库插入。
    student = Student(name=name, student_id=student_id, face_embedding_id=-1)
    session.add(student)
    session.flush()
    if student.id is None:
        session.rollback()
        raise HTTPException(500, "注册失败：无法生成学生 ID")

    vdb = request.app.state.vector_db
    try:
        fid = vdb.add(embedding, student.id)
    except Exception as e:
        session.rollback()
        raise HTTPException(500, "向量库写入失败") from e

    student.face_embedding_id = fid
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # best-effort: DB 写入失败时撤销向量库变更，避免 DB 与索引不一致
        try:
            vdb.remove(student.id)
            vdb.save()
        except Exception:
            pass
        raise HTTPException(500, "数据库写入失败") from e

    session.refresh(student)

    # best-effort：持久化索引（主流程成功后保存失败不应让客户端误判“注册失败”）
    try:
        vdb.save()
    except Exception:
        pass

    return {
        "message": "注册成功",
        "student": {"id": student.id, "name": name, "student_id": student_id},
    }
