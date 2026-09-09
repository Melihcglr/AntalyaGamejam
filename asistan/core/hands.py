from __future__ import annotations

import os
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

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

    def __init__(self, allowed_apps: dict[str, str], safety: SafetyGuard):
        self.allowed_apps = allowed_apps
        self.safety = safety
        if pyautogui is not None:
            pyautogui.FAILSAFE = True

    def open_app(self, app_key: str) -> ActionResult:
        decision = self.safety.check_app(app_key, self.allowed_apps)
        if decision.level == RiskLevel.BLOCKED:
            return ActionResult(False, decision.reason)
        exe = self.allowed_apps.get(app_key) or self.allowed_apps.get(app_key.lower())
        assert exe
        try:
            os.startfile(exe)  # type: ignore[attr-defined]
            return ActionResult(True, f"{app_key} açıldı.")
        except AttributeError:
            subprocess.Popen([exe], shell=False)
            return ActionResult(True, f"{app_key} başlatıldı.")
        except Exception as exc:
            return ActionResult(False, f"Açılamadı: {exc}")

    def open_url(self, url: str) -> ActionResult:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return ActionResult(True, f"Tarayıcıda açıldı: {url}")

    def type_text(self, text: str) -> ActionResult:
        if pyautogui is None:
            return ActionResult(False, "pyautogui kurulu değil.")
        pyautogui.typewrite(text, interval=0.02)
        return ActionResult(True, "Metin yazıldı.")

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
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
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
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(Path.home().anchor or "C:\\")
        data = {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
        }
        msg = (
            f"CPU %{cpu:.0f}, bellek %{mem.percent:.0f}, "
            f"disk %{disk.percent:.0f}."
        )
        return ActionResult(True, msg, data=data)

    def list_allowed_apps(self) -> ActionResult:
        return ActionResult(True, "İzinli uygulamalar", data={"apps": list(self.allowed_apps)})
