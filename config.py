from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库
DATABASE_URL = f"sqlite:///{DATA_DIR / 'attendance.db'}"

# FAISS 索引路径
FAISS_INDEX_PATH = str(DATA_DIR / "faces.index")
FAISS_ID_MAP_PATH = str(DATA_DIR / "id_map.json")

# InsightFace 模型
FACE_MODEL_NAME = "buffalo_l"
FACE_DET_SIZE = (640, 640)

# 人脸识别阈值 (cosine similarity)
FACE_SIMILARITY_THRESHOLD = 0.45

# 活体检测
EAR_THRESHOLD = 0.21
BLINK_CONSEC_FRAMES = 3
