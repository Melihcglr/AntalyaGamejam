from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .brain import Brain, local_time_speech, search_url, strip_wake
from .coder import Coder
from .config import Settings
from .device_health import check_devices
from .ear import Ear
from .eye import Eye
from .hands import ActionResult, Hands
from .iot import IoTHub
from .memory import Memory
from .mouth import Mouth
from .netscan import adopt_discovered, scan_network
from .safety import SafetyGuard
from .scenes import SceneRunner
from .wol import send_wol


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
        self.hands = Hands(
            self.settings.allowed_apps,
            self.safety,
            window_move_timeout_sec=self.settings.window_move_timeout_sec,
        )
        self.coder = Coder(self.settings, self.hands.allowed_apps)
        self.iot = IoTHub(self.settings.devices)
        self.scenes = SceneRunner(self.settings.scenes)
        self.eye = Eye()
        self.memory = Memory.load()
        self.ear: Ear | None = None
        self.mouth: Mouth | None = None
        self.listening = False
        self.log = EventLog()
        self._lock = threading.Lock()
        self._last_scan: list[dict[str, Any]] = []
        self._mic_muted = False

    def ensure_voice(self) -> None:
        if self.ear is None:
            self.ear = Ear(
                language=self.settings.language,
                stt_backend=self.settings.stt_backend,
                stt_model_path=self.settings.stt_model_path,
                push_to_talk=self.settings.push_to_talk,
            )
        else:
            self.ear.set_push_to_talk(self.settings.push_to_talk)
            self.ear.stt_backend = self.settings.stt_backend
            self.ear.stt_model_path = self.settings.stt_model_path
        self.ear.set_muted(self._mic_muted)
        if self.mouth is None and self.settings.speak_responses:
            self.mouth = Mouth(
                on_speak_start=self._on_speak_start,
                on_speak_end=self._on_speak_end,
            )

    def _on_speak_start(self) -> None:
        if self.ear:
            self.ear.pause_for_speech()

    def _on_speak_end(self) -> None:
        if self.ear:
            self.ear.resume_after_speech()

    def set_mic_muted(self, muted: bool) -> ActionResult:
        self._mic_muted = bool(muted)
        if self.ear:
            self.ear.set_muted(self._mic_muted)
        self.log.add("system", "Mikrofon kapatıldı." if muted else "Mikrofon açıldı.")
        return ActionResult(True, "Mikrofon kapatıldı." if muted else "Mikrofon açıldı.")

    def set_push_to_talk(self, enabled: bool) -> ActionResult:
        self.settings.push_to_talk = enabled
        self.settings.save()
        if self.ear:
            self.ear.set_push_to_talk(enabled)
        msg = "Push-to-talk açıldı." if enabled else "Push-to-talk kapatıldı."
        self.log.add("system", msg)
        return ActionResult(True, msg)

    def set_ptt_active(self, active: bool) -> ActionResult:
        if not self.settings.push_to_talk:
            return ActionResult(False, "Push-to-talk kapalı.")
        if self.ear:
            self.ear.set_ptt_active(active)
        return ActionResult(True, "PTT basılı." if active else "PTT bırakıldı.")

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
                "scene",
                "device",
                "device_status",
                "list_devices",
                "list_scenes",
                "network_scan",
                "network_adopt",
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
            monitor = action.get("monitor")
            try:
                monitor_i = int(monitor) if monitor is not None else None
            except (TypeError, ValueError):
                monitor_i = None
            return self.hands.open_app(target, monitor=monitor_i)
        if kind == "open_cursor":
            return self.coder.open_in_cursor(monitor=action.get("monitor"))
        if kind == "open_project":
            return self.coder.open_in_cursor(project=target or None)
        if kind == "create_site":
            return self.coder.create_site(target)
        if kind == "agent_prompt":
            project = None
            prompt = target
            if "::" in target:
                project, prompt = target.split("::", 1)
            return self.coder.write_agent_prompt(prompt, project=project)
        if kind == "list_projects":
            return self.coder.list_projects()
        if kind == "device":
            return self.iot.set_state(target, action.get("state") or "toggle")
        if kind == "device_status":
            return self.iot.status(target or None)
        if kind == "list_devices":
            return self.iot.list_devices()
        if kind == "network_scan":
            jarvis_only = (target or "").lower() in {"jarvis", "esp"}
            result = scan_network(jarvis_only=jarvis_only)
            if result.ok and result.data:
                self._last_scan = list(result.data.get("devices") or [])
            return result
        if kind == "network_adopt":
            source = self._last_scan
            if not source:
                # Önce hızlı Jarvis taraması
                scanned = scan_network(jarvis_only=True)
                source = list((scanned.data or {}).get("devices") or [])
                self._last_scan = source
            updated, added = adopt_discovered(source, self.settings.devices, jarvis_only=True)
            if not added:
                return ActionResult(
                    False,
                    "Eklenecek yeni Jarvis ESP bulunamadı. Önce 'ağı tara' / 'esp bul' de.",
                    data={"discovered": source},
                )
            self.settings.devices = updated
            self.settings.save()
            self.iot = IoTHub(self.settings.devices)
            self.brain = Brain(self.settings)
            return ActionResult(
                True,
                f"{len(added)} cihaz bağlandı: {', '.join(added)}.",
                data={"added": added, "devices": {k: v.model_dump() for k, v in updated.items()}},
            )
        if kind == "scene":
            return self.scenes.run(target, execute=self._execute)
        if kind == "list_scenes":
            return self.scenes.list_scenes()
        if kind == "pc_wake":
            mac = self.settings.pc_mac.strip()
            if not mac:
                return ActionResult(
                    False,
                    "pc_mac ayarlı değil. config.json içine MAC yaz veya ESP hub üzerinden WOL kullan.",
                )
            return send_wol(mac, broadcast=self.settings.wol_broadcast)
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
        if kind == "mic_mute":
            return self.set_mic_muted(True)
        if kind == "mic_unmute":
            return self.set_mic_muted(False)
        if kind == "push_to_talk":
            enabled = (action.get("state") or target or "on").lower() in {
                "on",
                "aç",
                "ac",
                "1",
                "true",
                "enable",
            }
            if (action.get("state") or target or "").lower() in {
                "off",
                "kapat",
                "0",
                "false",
                "disable",
            }:
                enabled = False
            return self.set_push_to_talk(enabled)
        if kind == "device_health":
            report = check_devices(
                self.settings.devices,
                mdns_name=self.settings.esp_mdns_name,
                preferred_port=self.settings.esp_http_port,
            )
            warnings = report.get("warnings") or []
            if not warnings:
                return ActionResult(True, "Cihazlar erişilebilir.", data=report)
            return ActionResult(
                True,
                "Cihaz uyarısı: " + " | ".join(warnings),
                data=report,
            )
        return ActionResult(False, f"Bilinmeyen eylem: {kind}")

    def status(self) -> dict[str, Any]:
        mic_muted = bool(self._mic_muted or (self.ear and self.ear.muted))
        stt_engine = self.ear.engine_name if self.ear else self.settings.stt_backend
        health = check_devices(
            self.settings.devices,
            mdns_name=self.settings.esp_mdns_name,
            preferred_port=self.settings.esp_http_port,
        )
        return {
            "name": self.settings.assistant_name,
            "listening": self.listening,
            "brain_ready": self.brain.ready,
            "require_wake_word": self.settings.require_wake_word,
            "wake_word": self.settings.wake_word,
            "pending_action": self.safety.pending_action,
            "allowed_apps": sorted(self.settings.allowed_apps),
            "notes_count": len(self.memory.notes),
            "devices": list(self.settings.devices),
            "scenes": list(self.settings.scenes),
            "last_scan_count": len(self._last_scan),
            "window_moves": list(self.hands.window_move_log[-5:]),
            "log": self.log.items[-30:],
            "mic_muted": mic_muted,
            "push_to_talk": self.settings.push_to_talk,
            "stt_engine": stt_engine,
            "api_token_required": bool(self.settings.api_token),
            "device_health": health,
            "device_warnings": health.get("warnings") or [],
        }
