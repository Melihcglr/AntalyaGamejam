from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.assistant import Assistant
from core.brain import Brain, strip_wake
from core.config import Settings
from core.memory import Memory
from core.safety import RiskLevel, SafetyGuard


class OfflineAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = Settings(
            openai_api_key="",
            allowed_apps={"notepad": "notepad.exe", "chrome": "chrome.exe"},
            blocked_commands=["format", "shutdown"],
            require_confirm_for_risky=True,
            speak_responses=False,
            require_wake_word=False,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _bot(self) -> Assistant:
        bot = Assistant(self.settings)
        bot.memory = Memory.load(self.root / "memory.json")
        return bot

    def test_offline_notepad_plan(self) -> None:
        brain = Brain(self.settings)
        plan = brain.plan("not defteri aç")
        self.assertEqual(plan["action"]["type"], "open_app")
        self.assertEqual(plan["action"]["target"], "notepad")

    def test_time_and_search(self) -> None:
        brain = Brain(self.settings)
        self.assertEqual(brain.plan("saat kaç")["action"]["type"], "time")
        search = brain.plan("ara fastapi tutorial")
        self.assertEqual(search["action"]["type"], "search")
        self.assertIn("fastapi", search["action"]["target"])

    def test_notes_flow(self) -> None:
        bot = self._bot()
        r1 = bot.handle_text("not al süt al")
        self.assertTrue(r1["result"]["ok"])
        r2 = bot.handle_text("notlarımı göster")
        self.assertIn("süt al", r2["speech"])
        r3 = bot.handle_text("notları temizle")
        self.assertTrue(r3["result"]["ok"])

    def test_status_action(self) -> None:
        bot = self._bot()
        result = bot.handle_text("sistem durumu")
        self.assertTrue(result["result"]["ok"])
        self.assertIn("CPU", result["speech"])

    def test_blocked_shell(self) -> None:
        guard = SafetyGuard(["format", "shutdown"], require_confirm_for_risky=True)
        decision = guard.check_shell("shutdown /s /t 0")
        self.assertEqual(decision.level, RiskLevel.BLOCKED)

    def test_risky_needs_confirm(self) -> None:
        guard = SafetyGuard([], require_confirm_for_risky=True)
        decision = guard.check_shell("del C:\\temp\\x.txt")
        self.assertEqual(decision.level, RiskLevel.RISK)
        self.assertTrue(decision.needs_confirm)

    def test_strip_wake(self) -> None:
        self.assertEqual(strip_wake("Jarvis, saat kaç", "jarvis", "Jarvis"), "saat kaç")
        self.assertEqual(strip_wake("hey jarvis not al ekmek", "jarvis", "Jarvis"), "not al ekmek")

    def test_wake_word_gate(self) -> None:
        self.settings.require_wake_word = True
        bot = self._bot()
        bot._on_heard("saat kaç")
        self.assertEqual(len([i for i in bot.log.items if i["kind"] == "action"]), 0)
        bot._on_heard("jarvis saat kaç")
        self.assertTrue(any(i["kind"] == "action" for i in bot.log.items))

    def test_describe_without_api(self) -> None:
        brain = Brain(self.settings)
        plan = brain.plan("ekranı açıkla")
        self.assertEqual(plan["action"]["type"], "describe_screen")


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from api_server import create_app
        except ImportError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"API bağımlılığı yok: {exc}") from exc

        settings = Settings(
            openai_api_key="",
            speak_responses=False,
            allowed_apps={"notepad": "notepad.exe"},
        )
        bot = Assistant(settings)
        bot.memory = Memory.load(Path(tempfile.mkdtemp()) / "memory.json")
        cls.client = TestClient(create_app(bot))

    def test_status_and_command(self) -> None:
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertIn("name", status.json())

        cmd = self.client.post("/api/command", json={"text": "saat kaç"})
        self.assertEqual(cmd.status_code, 200)
        body = cmd.json()
        self.assertEqual(body["action"]["type"], "time")
        self.assertTrue(body["result"]["ok"])

    def test_settings_patch(self) -> None:
        res = self.client.patch("/api/settings", json={"require_wake_word": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["settings"]["require_wake_word"])
        status = self.client.get("/api/status").json()
        self.assertTrue(status["require_wake_word"])


if __name__ == "__main__":
    unittest.main()
