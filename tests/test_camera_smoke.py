from __future__ import annotations

import app.utils.camera as camera_mod


class _DummyCap:
    def __init__(self):
        self.released = False

    def isOpened(self) -> bool:
        return False

    def read(self):
        return False, None

    def release(self) -> None:
        self.released = True


def test_camera_capture_release_are_safe(monkeypatch) -> None:
    monkeypatch.setattr(camera_mod.cv2, "VideoCapture", lambda _index: _DummyCap())
    cam = camera_mod.Camera(index=123)
    assert cam.capture() is None
    cam.release()
    # second release should be safe
    cam.release()
