from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeviceSpec(BaseModel):
    name: str = ""
    aliases: list[str] = Field(default_factory=list)
    base_url: str
    on_path: str = "/relay/on"
    off_path: str = "/relay/off"
    toggle_path: str = "/relay/toggle"
    status_path: str = "/relay/status"
    method: str = "GET"
    token: str = ""
    timeout_sec: float = 3.0


class SceneStep(BaseModel):
    type: str
    target: str = ""
    state: str = ""  # device: on|off|toggle
    monitor: int | None = None
    confirm_token: str | None = None


class SceneSpec(BaseModel):
    name: str = ""
    aliases: list[str] = Field(default_factory=list)
    steps: list[SceneStep] = Field(default_factory=list)
