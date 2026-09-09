from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.assistant import Assistant
from core.brain import Brain, strip_wake
from core.config import Settings
from core.hands import ActionResult
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

    def test_valorant_on_monitor_two(self) -> None:
        brain = Brain(self.settings)
        for phrase in (
            "valorantı ekran 2 de aç",
            "valorant'ı 2. ekranda aç",
            "ekran 2 de valorant aç",
            "valo monitör 2 başlat",
        ):
            plan = brain.plan(phrase)
            self.assertEqual(plan["action"]["type"], "open_app", phrase)
            self.assertEqual(plan["action"]["target"], "valorant", phrase)
            self.assertEqual(plan["action"]["monitor"], 2, phrase)

    def test_google_research_phrases(self) -> None:
        brain = Brain(self.settings)
        cases = [
            ("google'la araştır valorant ayarları", "valorant ayarları"),
            ("bana python asyncio araştır", "python asyncio"),
            ("şunu google ile araştır: konya hava", "konya hava"),
            ("fastapi hakkında google'da araştır", "fastapi"),
        ]
        for phrase, needle in cases:
            plan = brain.plan(phrase)
            self.assertEqual(plan["action"]["type"], "search", phrase)
            self.assertIn(needle.split()[0], plan["action"]["target"], phrase)

    def test_describe_not_confused_with_open(self) -> None:
        brain = Brain(self.settings)
        plan = brain.plan("ekranı açıkla")
        self.assertEqual(plan["action"]["type"], "describe_screen")

    def test_cursor_and_site_intents(self) -> None:
        brain = Brain(self.settings)
        self.assertEqual(brain.plan("cursor aç")["action"]["type"], "open_cursor")
        self.assertEqual(
            brain.plan("asistan projesini cursor'da aç")["action"]["type"],
            "open_project",
        )
        site = brain.plan("bana konya restoran sitesi yap")
        self.assertEqual(site["action"]["type"], "create_site")
        self.assertIn("konya", site["action"]["target"])
        edit = brain.plan("projeye şunu ekle: hakkımızda sayfası ekle")
        self.assertEqual(edit["action"]["type"], "agent_prompt")

    def test_create_site_writes_files(self) -> None:
        self.settings.workspace_root = str(self.root / "ws")
        self.settings.speak_responses = False
        bot = self._bot()
        result = bot.handle_text("şu tarz bir internet sitesi yap: ortalik bar")
        self.assertEqual(result["action"]["type"], "create_site")
        self.assertTrue(result["result"]["ok"])
        site = Path(result["result"]["data"]["path"])
        self.assertTrue((site / "index.html").exists())
        self.assertTrue((site / "styles.css").exists())

    def test_home_intents(self) -> None:
        from core.iot_models import DeviceSpec, SceneSpec, SceneStep

        self.settings.devices = {
            "isik": DeviceSpec(
                name="Oda ışığı",
                aliases=["ışık", "lamba"],
                base_url="http://127.0.0.1:9",
            )
        }
        self.settings.scenes = {
            "oyun": SceneSpec(
                name="Oyun modu",
                aliases=["oyun modu", "game mode"],
                steps=[
                    SceneStep(type="device", target="isik", state="off"),
                    SceneStep(type="open_app", target="notepad"),
                ],
            )
        }
        brain = Brain(self.settings)
        light = brain.plan("ışığı kapat")
        self.assertEqual(light["action"]["type"], "device")
        self.assertEqual(light["action"]["target"], "isik")
        self.assertEqual(light["action"]["state"], "off")
        scene = brain.plan("oyun modu")
        self.assertEqual(scene["action"]["type"], "scene")
        self.assertEqual(scene["action"]["target"], "oyun")
        wake = brain.plan("bilgisayar aç")
        self.assertEqual(wake["action"]["type"], "pc_wake")

    def test_wol_mac(self) -> None:
        from core.wol import normalize_mac, send_wol

        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF").hex(), "aabbccddeeff")
        bad = send_wol("not-a-mac")
        self.assertFalse(bad.ok)

    def test_network_scan_intents(self) -> None:
        brain = Brain(self.settings)
        self.assertEqual(brain.plan("ağı tara")["action"]["type"], "network_scan")
        self.assertEqual(brain.plan("esp bul")["action"]["target"], "jarvis")
        self.assertEqual(brain.plan("bulunan cihazları bağla")["action"]["type"], "network_adopt")

    def test_classify_requires_jarvis_marker(self) -> None:
        from core.netscan import _classify

        # Yalnızca "relay" / genel HTTP → jarvis sayılmamalı
        self.assertEqual(_classify("relay ok", {"device": "relay"})[0], "http")
        self.assertEqual(_classify("hello", None)[0], "http")
        self.assertEqual(
            _classify('{"device":"jarvis-relay"}', {"device": "jarvis-relay"})[0],
            "jarvis_relay",
        )
        self.assertEqual(
            _classify("esp-hub ready", {"role": "esp-hub"})[0],
            "jarvis_hub",
        )

    def test_adopt_discovered(self) -> None:
        from core.iot_models import DeviceSpec
        from core.netscan import adopt_discovered

        # Sadece hub → hem hub hem isik (aynı URL)
        hub_only = [{"kind": "jarvis_hub", "base_url": "http://192.168.1.50:8788"}]
        updated, added = adopt_discovered(hub_only, {}, jarvis_only=True)
        self.assertEqual(set(added), {"hub", "isik"})
        self.assertEqual(updated["hub"].base_url, "http://192.168.1.50:8788")
        self.assertEqual(updated["isik"].base_url, "http://192.168.1.50:8788")
        self.assertIn("ışık", updated["isik"].aliases)
        self.assertEqual(updated["isik"].status_path, "/relay/status")
        self.assertIsInstance(updated["isik"], DeviceSpec)
        again, added2 = adopt_discovered(hub_only, updated, jarvis_only=True)
        self.assertEqual(added2, [])
        self.assertEqual(len(again), 2)

        # Ayrı röle → espN
        with_relay = hub_only + [
            {"kind": "jarvis_relay", "base_url": "http://192.168.1.51:8788"},
            {"kind": "http", "base_url": "http://192.168.1.52"},
        ]
        updated2, added3 = adopt_discovered(with_relay, {}, jarvis_only=True)
        self.assertIn("esp1", added3)
        self.assertNotIn("http1", added3)

    def test_scene_runs_steps(self) -> None:
        from unittest.mock import patch

        from core.iot_models import DeviceSpec, SceneSpec, SceneStep

        self.settings.devices = {
            "isik": DeviceSpec(name="Işık", aliases=["ışık"], base_url="http://127.0.0.1:9")
        }
        self.settings.scenes = {
            "oyun": SceneSpec(
                aliases=["oyun modu"],
                steps=[
                    SceneStep(type="device", target="isik", state="off"),
                    SceneStep(type="open_app", target="notepad"),
                ],
            )
        }
        self.settings.allowed_apps = {"notepad": "notepad.exe"}
        self.settings.speak_responses = False
        bot = self._bot()
        with patch.object(bot.iot, "set_state", return_value=ActionResult(True, "kapandı")):
            with patch.object(bot.hands, "open_app", return_value=ActionResult(True, "notepad")):
                result = bot.handle_text("oyun modu")
        self.assertEqual(result["action"]["type"], "scene")
        self.assertTrue(result["result"]["ok"])
        self.assertEqual(len(result["result"]["data"]["results"]), 2)

    def test_notes_flow(self) -> None:
        bot = self._bot()
        r1 = bot.handle_text("not al süt al")
        self.assertTrue(r1["result"]["ok"])
        r2 = bot.handle_text("notlarımı göster")
        self.assertIn("süt al", r2["speech"])
        # silme, listeden önce eşleşmeli
        clear_plan = Brain(self.settings).plan("notları sil")
        self.assertEqual(clear_plan["action"]["type"], "note_clear")
        r3 = bot.handle_text("notları temizle")
        self.assertTrue(r3["result"]["ok"])
        self.assertEqual(Brain(self.settings).plan("notlarımı göster")["action"]["type"], "note_list")

    def test_confirm_token_binds_command(self) -> None:
        guard = SafetyGuard([], require_confirm_for_risky=True)
        from core.hands import Hands

        hands = Hands({"notepad": "notepad.exe"}, guard)
        first = hands.run_shell("del C:\\temp\\a.txt")
        self.assertTrue(first.needs_confirm)
        token = first.confirm_token
        # Aynı token ile farklı komut reddedilmeli
        second = hands.run_shell("del C:\\temp\\b.txt", confirm_token=token)
        self.assertFalse(second.ok)
        self.assertIn("bu komut için değil", second.message.lower())

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
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ok"])
        self.assertEqual(health.json()["role"], "pc-jarvis")

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
