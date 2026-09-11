from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Memory:
    """Kısa süreli diyalog + kalıcı notlar."""

    path: Path
    history: list[dict[str, str]] = field(default_factory=list)
    notes: list[dict[str, str]] = field(default_factory=list)
    max_history: int = 40

    @classmethod
    def load(cls, path: Path | None = None) -> "Memory":
        root = Path(__file__).resolve().parent.parent
        mem_path = path or (root / "data" / "memory.json")
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        inst = cls(path=mem_path)
        if mem_path.exists():
            raw = json.loads(mem_path.read_text(encoding="utf-8"))
            inst.history = list(raw.get("history") or [])
            inst.notes = list(raw.get("notes") or [])
        return inst

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"history": self.history[-self.max_history :], "notes": self.notes},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def remember_turn(self, role: str, text: str) -> None:
        self.history.append(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "role": role,
                "text": text,
            }
        )
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]
        self.save()

    def add_note(self, text: str) -> dict[str, str]:
        note = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "text": text.strip(),
        }
        self.notes.append(note)
        self.save()
        return note

    def list_notes(self, limit: int = 10) -> list[dict[str, str]]:
        return self.notes[-limit:]

    def clear_notes(self) -> int:
        n = len(self.notes)
        self.notes = []
        self.save()
        return n

    def context_blob(self) -> dict[str, Any]:
        return {
            "recent_history": self.history[-8:],
            "notes": self.notes[-5:],
        }
