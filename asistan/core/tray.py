from __future__ import annotations

"""Windows sistem tepsisi (pystray). Linux/test ortamında no-op."""

import threading
import webbrowser
from typing import Callable


def run_tray(
    *,
    name: str = "Jarvis",
    port: int = 8787,
    on_quit: Callable[[], None] | None = None,
    on_listen_toggle: Callable[[], None] | None = None,
    on_mute_toggle: Callable[[], None] | None = None,
) -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Tray için: pip install pystray Pillow"
        ) from exc

    def _icon_image() -> Image.Image:
        img = Image.new("RGB", (64, 64), (12, 18, 28))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, 56, 56), fill=(0, 180, 200))
        draw.rectangle((28, 18, 36, 46), fill=(12, 18, 28))
        return img

    def open_panel(icon: pystray.Icon, item: pystray.MenuItem) -> None:  # noqa: ARG001
        webbrowser.open(f"http://127.0.0.1:{port}")

    def quit_app(icon: pystray.Icon, item: pystray.MenuItem) -> None:  # noqa: ARG001
        icon.stop()
        if on_quit:
            on_quit()

    menu_items = [
        pystray.MenuItem("Kontrol paneli", open_panel, default=True),
    ]
    if on_listen_toggle:
        menu_items.append(pystray.MenuItem("Dinleme aç/kapat", lambda i, it: on_listen_toggle()))
    if on_mute_toggle:
        menu_items.append(pystray.MenuItem("Mikrofon mute", lambda i, it: on_mute_toggle()))
    menu_items.append(pystray.MenuItem("Çıkış", quit_app))

    icon = pystray.Icon("jarvis", _icon_image(), name, pystray.Menu(*menu_items))
    icon.run()


def start_tray_thread(**kwargs) -> threading.Thread:
    t = threading.Thread(target=run_tray, kwargs=kwargs, name="jarvis-tray", daemon=True)
    t.start()
    return t
