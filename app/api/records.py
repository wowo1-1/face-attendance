"""查询路由 — 考勤记录与学生列表"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.models.database import get_session
from app.models.schema import Attendance, Student

router = APIRouter(prefix="/api")


@router.get("/records")
async def get_records(
    course_id: int | None = Query(None),
    student_id: int | None = Query(None),
    day: date | None = Query(None, alias="date"),
    session: Session = Depends(get_session),
):
    stmt = select(Attendance)
    if course_id is not None:
        stmt = stmt.where(Attendance.course_id == course_id)
    if student_id is not None:
        stmt = stmt.where(Attendance.student_id == student_id)
    if day is not None:
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        stmt = stmt.where(Attendance.timestamp >= start, Attendance.timestamp < end)
    records = session.exec(stmt).all()
    return [r.model_dump() for r in records]


@router.get("/students")
async def get_students(session: Session = Depends(get_session)):
    students = session.exec(select(Student)).all()
    return [s.model_dump() for s in students]
