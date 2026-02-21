from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    """学生表"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    student_id: str = Field(unique=True, index=True)
    face_embedding_id: int = Field(description="对应 FAISS 索引 ID")
    created_at: datetime = Field(default_factory=datetime.now)


class Course(SQLModel, table=True):
    """课程表"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    teacher: str
    schedule: Optional[str] = None


class Attendance(SQLModel, table=True):
    """考勤记录表"""

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    course_id: int = Field(foreign_key="course.id")
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = Field(description="present/absent/late")
    confidence: float = Field(description="人脸识别置信度")
