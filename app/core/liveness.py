"""基于 MediaPipe Face Landmarker (Tasks API) 的静默式活体检测

说明：
- 本项目使用 MediaPipe Tasks API 的 FaceLandmarker（而非旧的 `mp.solutions.face_mesh`）。
- 部分 mediapipe 版本中 `mp.solutions` 可能不可用，因此这里直接依赖 Tasks API。
- 模型文件默认不联网下载，需提前放置到本地；如需自动下载请显式开启：
  - 代码参数：`LivenessDetector(auto_download=True)`
  - 环境变量：`FACE_ATTENDANCE_MEDIAPIPE_AUTO_DOWNLOAD=1`
- 默认模型路径：`data/mediapipe/face_landmarker.task`
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import urllib.request

import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions

from config import BLINK_CONSEC_FRAMES, DATA_DIR, EAR_THRESHOLD

_FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
_DEFAULT_MODEL_PATH = Path(DATA_DIR) / "mediapipe" / "face_landmarker.task"
_ENV_AUTO_DOWNLOAD = "FACE_ATTENDANCE_MEDIAPIPE_AUTO_DOWNLOAD"

# 眼部关键点索引
_LEFT_EYE = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33, 160, 158, 133, 153, 144]


def _ear(landmarks, indices) -> float:
    """计算单眼 EAR (Eye Aspect Ratio)"""
    p = [np.array([landmarks[i].x, landmarks[i].y]) for i in indices]
    vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horizontal = np.linalg.norm(p[0] - p[3])
    if horizontal <= 1e-8:
        return 0.0
    return float(vertical / (2.0 * horizontal))


class LivenessDetector:
    """通过眨眼检测判定真人"""

    def __init__(
        self, model_path: str | Path | None = None, auto_download: bool | None = None
    ):
        self._model_path = (
            Path(model_path) if model_path is not None else _DEFAULT_MODEL_PATH
        )
        if auto_download is None:
            # 默认不联网下载，避免离线/受限网络环境下“隐式卡死或抛异常”。
            raw = os.environ.get(_ENV_AUTO_DOWNLOAD)
            self._auto_download = str(raw).strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }
        else:
            self._auto_download = bool(auto_download)
        self._landmarker: FaceLandmarker | None = None

    def _download_model_if_needed(self) -> bool:
        if self._model_path.exists():
            return self._model_path.is_file()
        if not self._auto_download:
            return False

        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._model_path.with_suffix(self._model_path.suffix + ".tmp")
        try:
            try:
                with (
                    urllib.request.urlopen(  # nosec - 固定 URL，且支持通过 auto_download 显式控制
                        _FACE_LANDMARKER_MODEL_URL,
                        timeout=30,
                    ) as resp,
                    open(tmp, "wb") as f,
                ):
                    shutil.copyfileobj(resp, f)
            except Exception:
                # 网络不可用/下载失败时应安全降级，而不是把异常抛给上层业务。
                return False

            try:
                if not tmp.exists() or tmp.stat().st_size <= 0:
                    return False
                tmp.replace(self._model_path)
                return self._model_path.exists()
            except Exception:
                return False
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

    def _ensure_landmarker(self) -> FaceLandmarker | None:
        if self._landmarker is not None:
            return self._landmarker
        if not self._download_model_if_needed():
            return None

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self._model_path)),
            # 官方 API：mp.tasks.vision.RunningMode（避免依赖内部模块路径变更）
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        try:
            self._landmarker = FaceLandmarker.create_from_options(options)
        except Exception:
            # 模型损坏/版本不兼容时安全降级，不阻断主流程。
            self._landmarker = None
        return self._landmarker

    def close(self):
        """释放 MediaPipe 资源（建议在应用退出/对象不再使用时调用）。"""
        landmarker = getattr(self, "_landmarker", None)
        if landmarker is not None:
            landmarker.close()
        self._landmarker = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        # __del__ 不保证一定被调用，这里仅做 best-effort 释放。
        try:
            self.close()
        except Exception:
            pass

    def check(self, frames: list[np.ndarray]) -> bool:
        """分析连续帧，检测到至少 1 次眨眼返回 True"""
        if not frames:
            return False
        landmarker = self._ensure_landmarker()
        if landmarker is None:
            # 模型缺失或初始化失败时，降级为 “未检测到活体”。
            return False

        below_count = 0  # 连续低于阈值的帧数
        blinks = 0

        for frame in frames:
            if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
                below_count = 0
                continue
            # 注意：frame[:, :, ::-1] 会产生负 stride 的 view，某些库不接受；这里强制 contiguous。
            if frame.dtype != np.uint8:
                frame = np.clip(frame, 0, 255).astype(np.uint8)
            rgb = np.ascontiguousarray(frame[:, :, ::-1])  # BGR → RGB
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_img)

            if not result.face_landmarks:
                below_count = 0
                continue

            lm = result.face_landmarks[0]
            avg_ear = (_ear(lm, _LEFT_EYE) + _ear(lm, _RIGHT_EYE)) / 2.0
            if not np.isfinite(avg_ear):
                below_count = 0
                continue

            if avg_ear < EAR_THRESHOLD:
                below_count += 1
            else:
                if below_count >= BLINK_CONSEC_FRAMES:
                    blinks += 1
                below_count = 0

        # 处理帧序列末尾的眨眼
        if below_count >= BLINK_CONSEC_FRAMES:
            blinks += 1

        return blinks >= 1
