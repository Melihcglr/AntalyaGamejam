from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .iot_models import DeviceSpec, SceneSpec, SceneStep  # noqa: F401


class AppSpec(BaseModel):
    path: str
    args: list[str] = Field(default_factory=list)
    window_title: str = ""
    process_name: str = ""

    @classmethod
    def from_value(cls, value: str | dict[str, Any] | "AppSpec") -> "AppSpec":
        if isinstance(value, AppSpec):
            return value
        if isinstance(value, str):
            return cls(path=value)
        return cls.model_validate(value)


class Settings(BaseModel):
    assistant_name: str = "Jarvis"
    wake_word: str = "jarvis"
    require_wake_word: bool = False
    language: str = "tr-TR"
    timezone: str = "Europe/Istanbul"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    host: str = "0.0.0.0"
    port: int = 8787
    require_confirm_for_risky: bool = True
    speak_responses: bool = True
    allowed_apps: dict[str, AppSpec] = Field(default_factory=dict)
    blocked_commands: list[str] = Field(default_factory=list)
    window_move_timeout_sec: float = 45.0
    workspace_root: str = str(Path.home() / "JarvisWorkspace")
    cursor_cli: str = "cursor"
    projects: dict[str, str] = Field(default_factory=dict)
    devices: dict[str, DeviceSpec] = Field(default_factory=dict)
    scenes: dict[str, SceneSpec] = Field(default_factory=dict)
    # ESP hub / WOL
    pc_mac: str = ""
    wol_broadcast: str = "255.255.255.255"
    esp_hub_url: str = ""  # örn. http://192.168.1.50:8788
    # Güvenlik / ses / keşif
    api_token: str = ""  # boşsa auth kapalı; doluysa Bearer / X-Jarvis-Token
    stt_backend: str = "auto"  # auto | google | vosk
    stt_model_path: str = ""  # Vosk model klasörü (ör. ~/vosk-model-tr)
    push_to_talk: bool = False
    esp_mdns_name: str = "jarvis-hub.local"
    esp_http_port: int = 8788

    @field_validator("allowed_apps", mode="before")
    @classmethod
    def normalize_apps(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, Any] = {}
        for key, raw in value.items():
            out[str(key).lower()] = AppSpec.from_value(raw).model_dump()
        return out

    @field_validator("devices", mode="before")
    @classmethod
    def normalize_devices(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {str(k).lower(): v for k, v in value.items()}

    @field_validator("scenes", mode="before")
    @classmethod
    def normalize_scenes(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {str(k).lower(): v for k, v in value.items()}

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        root = Path(__file__).resolve().parent.parent
        config_path = path or (root / "config.json")
        if not config_path.exists():
            example = root / "config.example.json"
            data: dict[str, Any] = {}
            if example.exists():
                data = json.loads(example.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        return cls.model_validate(json.loads(config_path.read_text(encoding="utf-8")))

    def save(self, path: Path | None = None) -> None:
        root = Path(__file__).resolve().parent.parent
        config_path = path or (root / "config.json")
        payload = self.model_dump()
        # JSON’da uygulamaları okunaklı tut
        apps = {}
        for key, spec in self.allowed_apps.items():
            if spec.args or spec.window_title or spec.process_name:
                apps[key] = spec.model_dump()
            else:
                apps[key] = spec.path
        payload["allowed_apps"] = apps
        payload["devices"] = {k: v.model_dump() for k, v in self.devices.items()}
        payload["scenes"] = {k: v.model_dump() for k, v in self.scenes.items()}
        config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
