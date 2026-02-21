import numpy as np
from insightface.app import FaceAnalysis

from config import FACE_DET_SIZE, FACE_MODEL_NAME


class FaceEngine:
    """人脸检测与编码引擎，封装 InsightFace"""

    def __init__(self):
        self._app = FaceAnalysis(
            name=FACE_MODEL_NAME, providers=["CPUExecutionProvider"]
        )
        self._app.prepare(ctx_id=0, det_size=FACE_DET_SIZE)

    def detect(self, image: np.ndarray) -> list:
        """检测图像中的所有人脸，返回 Face 对象列表"""
        return self._app.get(image)

    def encode(self, image: np.ndarray) -> np.ndarray | None:
        """检测第一张人脸并返回 L2 归一化的 512 维 embedding"""
        faces = self.detect(image)
        if not faces:
            return None
        emb = np.asarray(faces[0].embedding, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(emb))
        if not np.isfinite(norm) or norm <= 0.0:
            # 极端情况下避免除零/NaN，视为无效 embedding。
            return None
        return emb / norm
