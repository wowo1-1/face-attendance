"""考勤路由 — 人脸识别签到"""

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlmodel import Session, select

from app.models.database import get_session
from app.models.schema import Attendance, Student
from config import FACE_SIMILARITY_THRESHOLD

router = APIRouter(prefix="/api")


@router.post("/attend")
async def attend(
    request: Request,
    course_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    # 读取图片并提取 embedding
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "无法解析图片")

    embedding = request.app.state.face_engine.encode(img)
    if embedding is None:
        raise HTTPException(400, "未检测到人脸")

    # FAISS 检索
    student_ids, scores = request.app.state.vector_db.search(embedding, top_k=1)
    if not student_ids or not scores or float(scores[0]) < FACE_SIMILARITY_THRESHOLD:
        raise HTTPException(404, "未识别到匹配学生")

    student_pk = int(student_ids[0])
    student = session.exec(select(Student).where(Student.id == student_pk)).first()
    if student is None:
        raise HTTPException(
            404, f"识别到学生 ID={student_pk} 但数据库无记录，请重新注册"
        )

    # 记录考勤
    record = Attendance(
        student_id=student_pk,
        course_id=course_id,
        status="present",
        confidence=round(float(scores[0]), 4),
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return {
        "message": "签到成功",
        "id": student.id,
        "name": student.name,
        "student_id": student.student_id,
        "course_id": course_id,
        "confidence": record.confidence,
    }
