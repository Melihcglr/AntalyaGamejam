from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.assistant import Assistant
from core.auth import ApiTokenMiddleware, generate_token
from core.config import Settings


class CommandIn(BaseModel):
    text: str = Field(min_length=1)
    confirm_token: str | None = None


class SettingsPatch(BaseModel):
    require_wake_word: bool | None = None
    speak_responses: bool | None = None
    wake_word: str | None = None
    openai_api_key: str | None = None
    api_token: str | None = None
    push_to_talk: bool | None = None
    stt_backend: str | None = None
    stt_model_path: str | None = None
    esp_mdns_name: str | None = None
    esp_http_port: int | None = None


class MuteIn(BaseModel):
    muted: bool = True


class PttIn(BaseModel):
    active: bool = False


def create_app(assistant: Assistant | None = None) -> FastAPI:
    settings = Settings.load()
    bot = assistant or Assistant(settings)
    app = FastAPI(title=f"{bot.settings.assistant_name} Kontrol", version="0.3.0")
    root = Path(__file__).resolve().parent
    ui_dir = root / "ui"
    captures = root / "captures"
    captures.mkdir(exist_ok=True)

    app.add_middleware(ApiTokenMiddleware, token_getter=lambda: bot.settings.api_token)

    app.mount("/static", StaticFiles(directory=ui_dir), name="static")
    app.mount("/captures", StaticFiles(directory=captures), name="captures")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "role": "pc-jarvis",
            "name": bot.settings.assistant_name,
            "listening": bot.listening,
            "auth_required": bool(bot.settings.api_token),
        }

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return bot.status()

    @app.post("/api/command")
    def command(body: CommandIn) -> dict[str, Any]:
        try:
            return bot.handle_text(body.text, confirm_token=body.confirm_token)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Komut işlenemedi: {exc}") from exc

    @app.post("/api/listen/start")
    def listen_start() -> dict[str, Any]:
        try:
            bot.start_listening()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"ok": True, "listening": True}

    @app.post("/api/listen/stop")
    def listen_stop() -> dict[str, Any]:
        bot.stop_listening()
        return {"ok": True, "listening": False}

    @app.post("/api/listen/mute")
    def listen_mute(body: MuteIn | None = None) -> dict[str, Any]:
        muted = True if body is None else body.muted
        result = bot.set_mic_muted(muted)
        return {"ok": result.ok, "muted": muted, "message": result.message}

    @app.post("/api/listen/ptt")
    def listen_ptt(body: PttIn) -> dict[str, Any]:
        result = bot.set_ptt_active(body.active)
        if not result.ok:
            raise HTTPException(status_code=400, detail=result.message)
        return {"ok": True, "active": body.active, "message": result.message}

    @app.post("/api/token/generate")
    def token_generate() -> dict[str, Any]:
        token = generate_token()
        bot.settings.api_token = token
        # ESP cihaz token'larını senkronla (boş olanlar)
        for spec in bot.settings.devices.values():
            if not spec.token:
                spec.token = token
        bot.settings.save()
        bot.iot = type(bot.iot)(bot.settings.devices)
        return {"ok": True, "api_token": token}

    @app.post("/api/camera")
    def camera() -> dict[str, Any]:
        return bot.handle_text("kameradan fotoğraf çek")

    @app.post("/api/screen")
    def screen() -> dict[str, Any]:
        return bot.handle_text("ekran görüntüsü al")

    @app.post("/api/describe/screen")
    def describe_screen() -> dict[str, Any]:
        return bot.handle_text("ekranı açıkla")

    @app.get("/api/devices")
    def devices() -> dict[str, Any]:
        return bot.iot.list_devices().data or {}

    @app.post("/api/network/scan")
    def network_scan(jarvis_only: bool = False) -> dict[str, Any]:
        text = "esp bul" if jarvis_only else "ağı tara"
        return bot.handle_text(text)

    @app.post("/api/network/adopt")
    def network_adopt() -> dict[str, Any]:
        return bot.handle_text("bulunan cihazları bağla")

    @app.post("/api/device/{name}")
    def device_set(name: str, state: str = "toggle") -> dict[str, Any]:
        return bot.handle_text(
            f"{name} {'aç' if state == 'on' else 'kapat' if state == 'off' else 'değiştir'}"
        )

    @app.get("/api/scenes")
    def scenes() -> dict[str, Any]:
        return bot.scenes.list_scenes().data or {}

    @app.post("/api/scene/{name}")
    def scene_run(name: str) -> dict[str, Any]:
        return bot.handle_text(f"{name} modu")

    @app.get("/api/notes")
    def notes() -> dict[str, Any]:
        return {"notes": bot.memory.list_notes(50)}

    @app.patch("/api/settings")
    def patch_settings(body: SettingsPatch) -> dict[str, Any]:
        data = body.model_dump(exclude_none=True)
        for key, value in data.items():
            setattr(bot.settings, key, value)
        bot.settings.save()
        if "openai_api_key" in data:
            bot.brain = type(bot.brain)(bot.settings)
        if "push_to_talk" in data and bot.ear:
            bot.ear.set_push_to_talk(bool(data["push_to_talk"]))
        if any(k in data for k in ("stt_backend", "stt_model_path")):
            # Sonraki ensure_voice yenilesin
            bot.ear = None
        return {"ok": True, "settings": bot.settings.model_dump()}

    app.state.assistant = bot
    return app
