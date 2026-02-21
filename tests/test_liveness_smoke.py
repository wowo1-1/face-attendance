from __future__ import annotations

import numpy as np

from app.core.liveness import LivenessDetector


def test_liveness_detector_no_model_no_download_is_safe(tmp_path) -> None:
    # 不触发联网下载；缺少模型时应安全降级为 False 而不是抛异常。
    detector = LivenessDetector(
        model_path=tmp_path / "missing.task", auto_download=False
    )
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    assert detector.check([frame]) is False
