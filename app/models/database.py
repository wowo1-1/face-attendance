from sqlmodel import Session, SQLModel, create_engine

from config import DATABASE_URL

# SQLite 需要 check_same_thread=False 以支持多线程访问
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db():
    """创建所有表"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖注入：提供数据库 session"""
    with Session(engine) as session:
        yield session
