from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.assistant import Assistant
from core.config import Settings


class CommandIn(BaseModel):
    text: str = Field(min_length=1)
    confirm_token: str | None = None


class SettingsPatch(BaseModel):
    require_wake_word: bool | None = None
    speak_responses: bool | None = None
    wake_word: str | None = None
    openai_api_key: str | None = None


def create_app(assistant: Assistant | None = None) -> FastAPI:
    settings = Settings.load()
    bot = assistant or Assistant(settings)
    app = FastAPI(title=f"{settings.assistant_name} Kontrol", version="0.2.0")
    root = Path(__file__).resolve().parent
    ui_dir = root / "ui"
    captures = root / "captures"
    captures.mkdir(exist_ok=True)

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
        return {"ok": True, "settings": bot.settings.model_dump()}

    app.state.assistant = bot
    return app
