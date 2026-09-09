from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .brain import Brain, local_time_speech, search_url, strip_wake
from .config import Settings
from .ear import Ear
from .eye import Eye
from .hands import ActionResult, Hands
from .memory import Memory
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
        self.memory = Memory.load()
        self.ear: Ear | None = None
        self.mouth: Mouth | None = None
        self.listening = False
        self.log = EventLog()
        self._lock = threading.Lock()

    def ensure_voice(self) -> None:
        if self.ear is None:
            self.ear = Ear(language=self.settings.language)
        if self.mouth is None and self.settings.speak_responses:
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

    def _wake_matched(self, text: str) -> bool:
        lowered = text.lower()
        wake = self.settings.wake_word.lower()
        name = self.settings.assistant_name.lower()
        return wake in lowered or name in lowered or lowered.startswith("hey " + wake)

    def _on_heard(self, text: str) -> None:
        matched = self._wake_matched(text)
        self.log.add("heard", text, wake_matched=matched)
        if self.settings.require_wake_word and not matched:
            return
        command = strip_wake(text, self.settings.wake_word, self.settings.assistant_name)
        self.handle_text(command)

    def handle_text(self, text: str, confirm_token: str | None = None) -> dict[str, Any]:
        with self._lock:
            self.memory.remember_turn("user", text)
            plan = self.brain.plan(
                text,
                context={
                    "assistant": self.settings.assistant_name,
                    "allowed_apps": list(self.settings.allowed_apps),
                    "pending": self.safety.pending_action,
                    "memory": self.memory.context_blob(),
                },
            )
            speech = plan.get("speech") or ""
            action = plan.get("action") or {}
            if confirm_token:
                action["confirm_token"] = confirm_token
            result = self._execute(action)

            # Eylem çıktısını konuşmaya ekle (saat, durum vb.)
            if result.ok and action.get("type") in {
                "status",
                "time",
                "processes",
                "note_list",
                "describe_camera",
                "describe_screen",
            }:
                speech = result.message or speech
            elif not result.ok and result.message:
                speech = f"{speech} {result.message}".strip() if speech else result.message

            self.memory.remember_turn("assistant", speech or result.message)
            if speech and self.mouth and self.settings.speak_responses:
                try:
                    self.mouth.say_async(speech)
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
        if kind == "open_path":
            return self.hands.open_path(target)
        if kind == "shell":
            return self.hands.run_shell(target, confirm_token=token)
        if kind == "type_text":
            return self.hands.type_text(target)
        if kind == "volume":
            return self.hands.volume(target)
        if kind == "search":
            return self.hands.open_url(search_url(target))
        if kind == "time":
            msg = local_time_speech(self.settings.timezone)
            return ActionResult(True, msg)
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
        if kind == "describe_camera":
            try:
                path = self.eye.snap_camera()
                desc = self.brain.describe_image(path)
                return ActionResult(True, desc, data={"path": str(path)})
            except Exception as exc:
                return ActionResult(False, str(exc))
        if kind == "describe_screen":
            try:
                path = self.eye.snap_screen()
                desc = self.brain.describe_image(path)
                return ActionResult(True, desc, data={"path": str(path)})
            except Exception as exc:
                return ActionResult(False, str(exc))
        if kind == "status":
            return self.hands.system_status()
        if kind == "processes":
            return self.hands.list_processes()
        if kind == "list_apps":
            return self.hands.list_allowed_apps()
        if kind == "note_add":
            note = self.memory.add_note(target)
            return ActionResult(True, f"Not kaydedildi: {note['text']}", data=note)
        if kind == "note_list":
            notes = self.memory.list_notes()
            if not notes:
                return ActionResult(True, "Kayıtlı not yok.", data={"notes": []})
            joined = "; ".join(n["text"] for n in notes)
            return ActionResult(True, f"Notların: {joined}", data={"notes": notes})
        if kind == "note_clear":
            n = self.memory.clear_notes()
            return ActionResult(True, f"{n} not silindi.")
        return ActionResult(False, f"Bilinmeyen eylem: {kind}")

    def status(self) -> dict[str, Any]:
        return {
            "name": self.settings.assistant_name,
            "listening": self.listening,
            "brain_ready": self.brain.ready,
            "require_wake_word": self.settings.require_wake_word,
            "wake_word": self.settings.wake_word,
            "pending_action": self.safety.pending_action,
            "allowed_apps": sorted(self.settings.allowed_apps),
            "notes_count": len(self.memory.notes),
            "log": self.log.items[-30:],
        }
