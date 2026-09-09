from __future__ import annotations

import unittest

from core.brain import Brain
from core.config import Settings
from core.safety import RiskLevel, SafetyGuard


class OfflineAssistantTests(unittest.TestCase):
    def test_offline_notepad_plan(self) -> None:
        brain = Brain(Settings(openai_api_key=""))
        plan = brain.plan("not defteri aç")
        self.assertEqual(plan["action"]["type"], "open_app")
        self.assertEqual(plan["action"]["target"], "notepad")

    def test_blocked_shell(self) -> None:
        guard = SafetyGuard(["format", "shutdown"], require_confirm_for_risky=True)
        decision = guard.check_shell("shutdown /s /t 0")
        self.assertEqual(decision.level, RiskLevel.BLOCKED)

    def test_risky_needs_confirm(self) -> None:
        guard = SafetyGuard([], require_confirm_for_risky=True)
        decision = guard.check_shell("del C:\\temp\\x.txt")
        self.assertEqual(decision.level, RiskLevel.RISK)
        self.assertTrue(decision.needs_confirm)


if __name__ == "__main__":
    unittest.main()
