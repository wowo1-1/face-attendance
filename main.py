"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import attend, records, register
from app.core.face_engine import FaceEngine
from app.core.vector_db import VectorDB
from app.models.database import init_db
from config import FAISS_ID_MAP_PATH, FAISS_INDEX_PATH

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化数据库、人脸引擎、向量库
    init_db()
    app.state.face_engine = FaceEngine()
    app.state.vector_db = VectorDB()
    index_path = Path(FAISS_INDEX_PATH)
    id_map_path = Path(FAISS_ID_MAP_PATH)
    if index_path.exists() and id_map_path.exists():
        try:
            app.state.vector_db.load()
        except Exception:
            # 任意加载异常都不应阻断服务启动（否则一次坏文件会让系统完全不可用）
            logger.exception("FAISS 索引加载失败，将以空索引启动")
            # 尽量把坏文件挪走，避免空索引 save 时覆盖导致“不可恢复的数据丢失”
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            try:
                index_path.rename(
                    index_path.with_name(f"{index_path.name}.broken.{ts}")
                )
                id_map_path.rename(
                    id_map_path.with_name(f"{id_map_path.name}.broken.{ts}")
                )
            except Exception:
                logger.exception("备份损坏的 FAISS 文件失败（将继续以空索引启动）")
            app.state.vector_db = VectorDB()
    elif index_path.exists() and not id_map_path.exists():
        # index 与映射文件不一致，直接忽略，避免 search 读到错映射
        logger.warning("检测到 %s 但缺少 %s，将以空索引启动", index_path, id_map_path)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            index_path.rename(index_path.with_name(f"{index_path.name}.orphan.{ts}"))
        except Exception:
            logger.exception("备份孤儿 FAISS index 失败（将继续以空索引启动）")
        app.state.vector_db = VectorDB()

    try:
        yield
    finally:
        # 关闭：持久化向量库（best-effort，避免 shutdown 阶段异常导致进程卡死）
        vdb = getattr(app.state, "vector_db", None)
        if vdb is not None:
            try:
                vdb.save()
            except Exception:
                logger.exception("FAISS 索引保存失败")


app = FastAPI(title="课堂人脸考勤系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(register.router)
app.include_router(attend.router)
app.include_router(records.router)
