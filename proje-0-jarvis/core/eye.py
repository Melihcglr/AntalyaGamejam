from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import mss
except ImportError:  # pragma: no cover
    mss = None  # type: ignore


class Eye:
    """Kamera ve ekran yakalama."""

    def __init__(self, capture_dir: Path | None = None):
        root = Path(__file__).resolve().parent.parent
        self.capture_dir = capture_dir or (root / "captures")
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def _stamp(self, prefix: str) -> Path:
        name = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        return self.capture_dir / name

    def snap_camera(self, camera_index: int = 0) -> Path:
        if cv2 is None:
            raise RuntimeError("opencv-python-headless kurulu değil.")
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError("Kamera açılamadı. Windows gizlilik ayarlarını kontrol et.")
        try:
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Kameradan kare alınamadı.")
            path = self._stamp("camera")
            cv2.imwrite(str(path), frame)
            return path
        finally:
            cap.release()

    def snap_screen(self, monitor: int = 1) -> Path:
        if mss is None:
            raise RuntimeError("mss kurulu değil.")
        with mss.mss() as sct:
            monitors = sct.monitors
            idx = monitor if monitor < len(monitors) else 1
            shot = sct.grab(monitors[idx])
            frame = np.array(shot)[:, :, :3]
            if cv2 is None:
                raise RuntimeError("opencv-python-headless kurulu değil.")
            path = self._stamp("screen")
            cv2.imwrite(str(path), frame)
            return path
