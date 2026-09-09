from __future__ import annotations

import os
import platform
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from .config import AppSpec
from .display import list_monitors, move_window_to_monitor
from .safety import RiskLevel, SafetyGuard

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None  # type: ignore


@dataclass
class ActionResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None
    needs_confirm: bool = False
    confirm_token: str | None = None


class Hands:
    """Sistem eylemleri — yalnızca izinli ve denetlenmiş işlemler."""

    def __init__(
        self,
        allowed_apps: dict[str, str | AppSpec | dict[str, Any]],
        safety: SafetyGuard,
        window_move_timeout_sec: float = 45.0,
    ):
        self.allowed_apps: dict[str, AppSpec] = {
            k.lower(): AppSpec.from_value(v) for k, v in allowed_apps.items()
        }
        self.safety = safety
        self.window_move_timeout_sec = window_move_timeout_sec
        if pyautogui is not None:
            pyautogui.FAILSAFE = True

    def open_app(self, app_key: str, monitor: int | None = None) -> ActionResult:
        key = app_key.lower().strip()
        decision = self.safety.check_app(key, self.allowed_apps)
        if decision.level == RiskLevel.BLOCKED:
            return ActionResult(False, decision.reason)
        spec = self.allowed_apps[key]
        try:
            self._launch(spec)
        except Exception as exc:
            return ActionResult(False, f"Açılamadı: {exc}")

        msg = f"{key} açıldı."
        data: dict[str, Any] = {"app": key, "path": spec.path}
        if monitor is not None:
            data["monitor"] = monitor
            # Pencere geç gelebilir (Valorant/Riot); arka planda taşı.
            threading.Thread(
                target=self._move_later,
                args=(spec, monitor),
                daemon=True,
                name=f"move-{key}-m{monitor}",
            ).start()
            msg = f"{key} açıldı; ekran {monitor}'e taşınıyor."
        return ActionResult(True, msg, data=data)

    def _launch(self, spec: AppSpec) -> None:
        path = spec.path
        args = list(spec.args)
        if hasattr(os, "startfile") and not args:
            os.startfile(path)  # type: ignore[attr-defined]
            return
        cmd = [path, *args]
        subprocess.Popen(cmd, shell=False)

    def _move_later(self, spec: AppSpec, monitor: int) -> None:
        title = spec.window_title or Path(spec.path).stem
        move_window_to_monitor(
            monitor=monitor,
            title_contains=title,
            process_name=spec.process_name,
            timeout_sec=self.window_move_timeout_sec,
        )

    def open_url(self, url: str) -> ActionResult:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return ActionResult(True, f"Tarayıcıda açıldı: {url}")

    def open_path(self, raw_path: str) -> ActionResult:
        path = Path(raw_path.strip().strip('"')).expanduser()
        if not path.exists():
            return ActionResult(False, f"Yol bulunamadı: {path}")
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return ActionResult(True, f"Açıldı: {path}", data={"path": str(path)})
        except Exception as exc:
            return ActionResult(False, str(exc))

    def type_text(self, text: str) -> ActionResult:
        if pyautogui is None:
            return ActionResult(False, "pyautogui kurulu değil.")
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.write(text, interval=0.02)
        return ActionResult(True, "Metin yazıldı.")

    def volume(self, target: str) -> ActionResult:
        mode = (target or "").lower().strip()
        if pyautogui is None:
            return ActionResult(False, "Ses kontrolü için pyautogui gerekli.")
        if mode == "mute":
            pyautogui.press("volumemute")
            return ActionResult(True, "Ses kapatıldı/açıldı (mute).")
        if mode == "up":
            for _ in range(4):
                pyautogui.press("volumeup")
            return ActionResult(True, "Ses yükseltildi.")
        if mode == "down":
            for _ in range(4):
                pyautogui.press("volumedown")
            return ActionResult(True, "Ses kısılı.")
        return ActionResult(False, "volume target: up|down|mute")

    def run_shell(self, command: str, confirm_token: str | None = None) -> ActionResult:
        decision = self.safety.check_shell(command)
        if decision.level == RiskLevel.BLOCKED:
            return ActionResult(False, decision.reason)
        if decision.needs_confirm:
            if not confirm_token or not self.safety.consume_confirm(confirm_token):
                token = f"risk-{abs(hash(command)) % 10_000_000}"
                self.safety.arm_confirm(token, command)
                return ActionResult(
                    False,
                    f"Riskli komut onay bekliyor: {command}",
                    needs_confirm=True,
                    confirm_token=token,
                )
        try:
            if platform.system() == "Windows":
                cmd = ["powershell", "-NoProfile", "-Command", command]
            else:
                cmd = ["bash", "-lc", command]
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            out = (completed.stdout or "").strip()
            err = (completed.stderr or "").strip()
            if completed.returncode != 0:
                return ActionResult(False, err or f"Çıkış kodu {completed.returncode}")
            return ActionResult(True, out or "Komut tamamlandı.")
        except Exception as exc:
            return ActionResult(False, str(exc))

    def system_status(self) -> ActionResult:
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        root = Path.home().anchor or ("C:\\" if platform.system() == "Windows" else "/")
        disk = psutil.disk_usage(root)
        monitors = list_monitors()
        data = {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
            "monitors": [
                {
                    "index": m.index,
                    "width": m.width,
                    "height": m.height,
                    "primary": m.is_primary,
                }
                for m in monitors
            ],
            "platform": platform.platform(),
        }
        msg = (
            f"CPU %{cpu:.0f}, bellek %{mem.percent:.0f}, "
            f"disk %{disk.percent:.0f}, ekran sayısı {len(monitors)}."
        )
        return ActionResult(True, msg, data=data)

    def list_processes(self, limit: int = 8) -> ActionResult:
        rows: list[dict[str, Any]] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                rows.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "cpu": info.get("cpu_percent") or 0.0,
                        "mem": info.get("memory_percent") or 0.0,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        rows.sort(key=lambda r: (r["cpu"], r["mem"]), reverse=True)
        top = rows[:limit]
        names = ", ".join(f"{r['name']}(%{r['cpu']:.0f})" for r in top[:5]) or "yok"
        return ActionResult(True, f"Öne çıkan süreçler: {names}", data={"processes": top})

    def list_allowed_apps(self) -> ActionResult:
        return ActionResult(True, "İzinli uygulamalar", data={"apps": sorted(self.allowed_apps)})
