from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Settings(BaseModel):
    assistant_name: str = "Jarvis"
    wake_word: str = "jarvis"
    require_wake_word: bool = False
    language: str = "tr-TR"
    timezone: str = "Europe/Istanbul"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = 8787
    require_confirm_for_risky: bool = True
    speak_responses: bool = True
    allowed_apps: dict[str, str] = Field(default_factory=dict)
    blocked_commands: list[str] = Field(default_factory=list)

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
        config_path.write_text(
            json.dumps(self.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
