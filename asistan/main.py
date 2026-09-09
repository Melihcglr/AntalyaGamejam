from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from api_server import create_app
from core.assistant import Assistant
from core.config import Settings


def ensure_config() -> Settings:
    root = Path(__file__).resolve().parent
    config_path = root / "config.json"
    if not config_path.exists():
        settings = Settings.load(root / "config.example.json")
        settings.save(config_path)
        print(f"config.json oluşturuldu: {config_path}")
        print("OpenAI anahtarını config.json içine yazabilirsin (opsiyonel).")
    return Settings.load(config_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows Jarvis asistan")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--cli", action="store_true", help="Sadece metin CLI")
    parser.add_argument("--listen", action="store_true", help="CLI + mikrofon döngüsü")
    args = parser.parse_args()

    settings = ensure_config()
    bot = Assistant(settings)

    if args.cli or args.listen:
        print(f"{settings.assistant_name} hazır. Çıkmak için: çık / exit")
        if args.listen:
            try:
                bot.start_listening()
                print("Mikrofon dinleniyor...")
            except Exception as exc:
                print(f"Mikrofon açılamadı: {exc}")
                print("Metin moduna düşülüyor.")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.lower() in {"çık", "exit", "quit", "q"}:
                break
            result = bot.handle_text(line)
            print(result.get("speech"))
            r = result.get("result") or {}
            if r.get("message"):
                print(f"[{'ok' if r.get('ok') else 'hata'}] {r['message']}")
            if r.get("needs_confirm"):
                print(f"Onay token: {r.get('confirm_token')}")
        bot.stop_listening()
        return

    app = create_app(bot)
    host = args.host or settings.host
    port = args.port or settings.port
    print(f"Kontrol paneli: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
