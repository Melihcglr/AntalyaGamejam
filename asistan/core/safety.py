from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    RISK = "risk"
    BLOCKED = "blocked"


@dataclass
class SafetyDecision:
    level: RiskLevel
    reason: str
    needs_confirm: bool = False


class SafetyGuard:
    def __init__(self, blocked_commands: list[str], require_confirm_for_risky: bool = True):
        self.blocked_commands = [c.lower() for c in blocked_commands]
        self.require_confirm = require_confirm_for_risky
        self._pending_token: str | None = None
        self._pending_action: str | None = None

    def check_shell(self, command: str) -> SafetyDecision:
        lowered = command.lower()
        for blocked in self.blocked_commands:
            if blocked in lowered:
                return SafetyDecision(RiskLevel.BLOCKED, f"Engellenen kalıp: {blocked}")
        risky_markers = ("del ", "rmdir", "taskkill", "net user", "powershell -", "reg add")
        if any(m in lowered for m in risky_markers):
            return SafetyDecision(
                RiskLevel.RISK,
                "Riskli kabuk komutu",
                needs_confirm=self.require_confirm,
            )
        return SafetyDecision(RiskLevel.SAFE, "İzin verildi")

    def check_app(self, app_key: str, allowed: dict[str, str]) -> SafetyDecision:
        if app_key.lower() not in {k.lower() for k in allowed}:
            return SafetyDecision(RiskLevel.BLOCKED, f"Uygulama listede yok: {app_key}")
        return SafetyDecision(RiskLevel.SAFE, "İzin verildi")

    def arm_confirm(self, token: str, action: str) -> None:
        self._pending_token = token
        self._pending_action = action

    def consume_confirm(self, token: str) -> bool:
        ok = self._pending_token is not None and token == self._pending_token
        if ok:
            self._pending_token = None
            self._pending_action = None
        return ok

    @property
    def pending_action(self) -> str | None:
        return self._pending_action
