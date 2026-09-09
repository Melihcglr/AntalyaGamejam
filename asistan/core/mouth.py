from __future__ import annotations

import threading

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None  # type: ignore


class Mouth:
    """Windows SAPI üzerinden TTS."""

    def __init__(self, rate: int = 175, volume: float = 1.0, prefer_turkish: bool = True):
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 kurulu değil. pip install pyttsx3")
        self._lock = threading.Lock()
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        if prefer_turkish:
            self._pick_turkish_voice()

    def _pick_turkish_voice(self) -> None:
        for voice in self.engine.getProperty("voices"):
            blob = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
            if "tr" in blob or "turkish" in blob or "türk" in blob:
                self.engine.setProperty("voice", voice.id)
                return

    def say(self, text: str, wait: bool = True) -> None:
        if not text.strip():
            return
        with self._lock:
            self.engine.say(text)
            if wait:
                self.engine.runAndWait()

    def say_async(self, text: str) -> None:
        threading.Thread(target=self.say, args=(text,), daemon=True).start()
