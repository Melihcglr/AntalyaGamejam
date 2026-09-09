from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .brain import Brain
from .config import Settings
from .ear import Ear
from .eye import Eye
from .hands import ActionResult, Hands
from .mouth import Mouth
from .safety import SafetyGuard


@dataclass
class EventLog:
    items: list[dict[str, Any]] = field(default_factory=list)

    def add(self, kind: str, message: str, **extra: Any) -> None:
        self.items.append(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "kind": kind,
                "message": message,
                **extra,
            }
        )
        if len(self.items) > 200:
            self.items = self.items[-200:]


class Assistant:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.safety = SafetyGuard(
            self.settings.blocked_commands,
            self.settings.require_confirm_for_risky,
        )
        self.brain = Brain(self.settings)
        self.hands = Hands(self.settings.allowed_apps, self.safety)
        self.eye = Eye()
        self.ear: Ear | None = None
        self.mouth: Mouth | None = None
        self.listening = False
        self.log = EventLog()
        self._lock = threading.Lock()

    def ensure_voice(self) -> None:
        if self.ear is None:
            self.ear = Ear(language=self.settings.language)
        if self.mouth is None:
            self.mouth = Mouth()

    def start_listening(self) -> None:
        self.ensure_voice()
        assert self.ear is not None
        if self.listening:
            return
        self.listening = True
        self.ear.start_loop(on_text=self._on_heard)
        self.log.add("system", "Dinleme başladı.")

    def stop_listening(self) -> None:
        if self.ear:
            self.ear.stop_loop()
        self.listening = False
        self.log.add("system", "Dinleme durdu.")

    def _on_heard(self, text: str) -> None:
        wake = self.settings.wake_word.lower()
        lowered = text.lower()
        if wake and wake not in lowered and not lowered.startswith(self.settings.assistant_name.lower()):
            # Wake word yoksa yine de komut kabul et (MVP); sadece logla.
            self.log.add("heard", text, wake_matched=False)
        else:
            self.log.add("heard", text, wake_matched=True)
        self.handle_text(text)

    def handle_text(self, text: str, confirm_token: str | None = None) -> dict[str, Any]:
        with self._lock:
            plan = self.brain.plan(
                text,
                context={
                    "assistant": self.settings.assistant_name,
                    "allowed_apps": list(self.settings.allowed_apps),
                    "pending": self.safety.pending_action,
                },
            )
            speech = plan.get("speech") or ""
            action = plan.get("action") or {}
            if confirm_token:
                action["confirm_token"] = confirm_token
            result = self._execute(action)
            if speech and self.mouth:
                try:
                    self.mouth.say_async(speech if result.ok or not result.message else f"{speech} {result.message}")
                except Exception as exc:
                    self.log.add("tts-error", str(exc))
            payload = {
                "input": text,
                "speech": speech,
                "action": action,
                "result": {
                    "ok": result.ok,
                    "message": result.message,
                    "data": result.data,
                    "needs_confirm": result.needs_confirm,
                    "confirm_token": result.confirm_token,
                },
            }
            self.log.add("action", result.message, ok=result.ok, action=action.get("type"))
            return payload

    def _execute(self, action: dict[str, Any]) -> ActionResult:
        kind = (action.get("type") or "none").lower()
        target = action.get("target") or ""
        token = action.get("confirm_token")

        if kind in ("none", "", "chat"):
            return ActionResult(True, "Sözlü yanıt.")
        if kind == "open_app":
            return self.hands.open_app(target)
        if kind == "open_url":
            return self.hands.open_url(target)
        if kind == "shell":
            return self.hands.run_shell(target, confirm_token=token)
        if kind == "type_text":
            return self.hands.type_text(target)
        if kind == "camera":
            try:
                path = self.eye.snap_camera()
                return ActionResult(True, f"Kamera kaydı: {path}", data={"path": str(path)})
            except Exception as exc:
                return ActionResult(False, str(exc))
        if kind == "screen":
            try:
                path = self.eye.snap_screen()
                return ActionResult(True, f"Ekran kaydı: {path}", data={"path": str(path)})
            except Exception as exc:
                return ActionResult(False, str(exc))
        if kind == "status":
            return self.hands.system_status()
        if kind == "list_apps":
            return self.hands.list_allowed_apps()
        return ActionResult(False, f"Bilinmeyen eylem: {kind}")

    def status(self) -> dict[str, Any]:
        return {
            "name": self.settings.assistant_name,
            "listening": self.listening,
            "brain_ready": self.brain.ready,
            "pending_action": self.safety.pending_action,
            "allowed_apps": list(self.settings.allowed_apps),
            "log": self.log.items[-30:],
        }
