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


def create_app(assistant: Assistant | None = None) -> FastAPI:
    settings = Settings.load()
    bot = assistant or Assistant(settings)
    app = FastAPI(title=f"{settings.assistant_name} Kontrol", version="0.1.0")
    ui_dir = Path(__file__).resolve().parent / "ui"
    captures = Path(__file__).resolve().parent / "captures"
    captures.mkdir(exist_ok=True)

    app.mount("/static", StaticFiles(directory=ui_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return bot.status()

    @app.post("/api/command")
    def command(body: CommandIn) -> dict[str, Any]:
        return bot.handle_text(body.text, confirm_token=body.confirm_token)

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

    app.state.assistant = bot
    return app
