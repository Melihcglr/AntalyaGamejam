from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class MonitorInfo:
    index: int  # 1-based kullanıcı ekranı
    left: int
    top: int
    width: int
    height: int
    is_primary: bool = False


def list_monitors() -> list[MonitorInfo]:
    if platform.system() != "Windows":
        return [MonitorInfo(index=1, left=0, top=0, width=1920, height=1080, is_primary=True)]
    return _list_monitors_win()


def move_window_to_monitor(
    *,
    monitor: int,
    title_contains: str = "",
    process_name: str = "",
    timeout_sec: float = 45.0,
    poll_sec: float = 0.7,
) -> tuple[bool, str]:
    """Pencereyi 1-based monitör numarasına taşı (Windows)."""
    if platform.system() != "Windows":
        return False, "Pencere taşıma yalnızca Windows'ta desteklenir."
    monitors = list_monitors()
    if monitor < 1 or monitor > len(monitors):
        return False, f"Ekran {monitor} yok. Mevcut: 1-{len(monitors)}"
    target = monitors[monitor - 1]
    deadline = time.time() + timeout_sec
    last_err = "Pencere bulunamadı."
    while time.time() < deadline:
        hwnd = _find_window(title_contains=title_contains, process_name=process_name)
        if hwnd:
            ok, msg = _place_window(hwnd, target)
            return ok, msg
        time.sleep(poll_sec)
    return False, last_err


def _list_monitors_win() -> list[MonitorInfo]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    monitors: list[MonitorInfo] = []

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )

    def _callback(hmon, _hdc, _lprect, _data):  # noqa: ANN001
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            monitors.append(
                MonitorInfo(
                    index=0,
                    left=int(r.left),
                    top=int(r.top),
                    width=int(r.right - r.left),
                    height=int(r.bottom - r.top),
                    is_primary=bool(info.dwFlags & 1),
                )
            )
        return True

    user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_callback), 0)
    # Primary önce, sonra sola göre
    monitors.sort(key=lambda m: (not m.is_primary, m.left, m.top))
    for i, m in enumerate(monitors, start=1):
        m.index = i
    if not monitors:
        monitors.append(MonitorInfo(1, 0, 0, 1920, 1080, True))
    return monitors


def _find_window(*, title_contains: str = "", process_name: str = "") -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches: list[int] = []
    title_q = title_contains.lower().strip()
    proc_q = process_name.lower().strip()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):  # noqa: ANN001
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _process_name(pid.value).lower()
        title_ok = (title_q in title.lower()) if title_q else False
        proc_ok = (proc_q in proc_name) if proc_q else False
        if title_q and proc_q:
            if title_ok or proc_ok:
                matches.append(int(hwnd))
        elif title_q and title_ok:
            matches.append(int(hwnd))
        elif proc_q and proc_ok:
            matches.append(int(hwnd))
        return True

    user32.EnumWindows(_enum, 0)
    return matches[0] if matches else None


def _process_name(pid: int) -> str:
    try:
        import psutil

        return psutil.Process(pid).name()
    except Exception:
        return ""


def _place_window(hwnd: int, monitor: MonitorInfo) -> tuple[bool, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    SW_SHOWMAXIMIZED = 3
    user32.ShowWindow(hwnd, SW_RESTORE)
    # Kenarlardan biraz içeride aç, sonra maximize
    margin = 20
    left = monitor.left + margin
    top = monitor.top + margin
    width = max(800, monitor.width - margin * 2)
    height = max(600, monitor.height - margin * 2)
    ok = user32.SetWindowPos(hwnd, 0, left, top, width, height, 0x0040)  # SWP_SHOWWINDOW
    if not ok:
        return False, "SetWindowPos başarısız."
    user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
    return True, f"Pencere ekran {monitor.index}'e taşındı."
