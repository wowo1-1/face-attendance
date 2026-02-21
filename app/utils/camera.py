"""摄像头封装模块"""

import cv2
import numpy as np


class Camera:
    """OpenCV 摄像头封装"""

    def __init__(self, index: int = 0):
        self.cap = cv2.VideoCapture(index)

    def capture(self) -> np.ndarray | None:
        """采集单帧，失败返回 None"""
        cap = getattr(self, "cap", None)
        if cap is None:
            return None
        if hasattr(cap, "isOpened") and not cap.isOpened():
            return None
        ok, frame = cap.read()
        return frame if ok else None

    def release(self):
        """释放摄像头"""
        cap = getattr(self, "cap", None)
        if cap is not None:
            cap.release()
        self.cap = None

    def close(self):
        """release() 的别名，便于与其它资源对象一致使用。"""
        self.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    def __del__(self):
        # best-effort 释放
        try:
            self.release()
        except Exception:
            pass
