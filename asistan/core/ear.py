from __future__ import annotations

import queue
import threading
from typing import Callable

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None  # type: ignore


class Ear:
    """Mikrofon dinleyici (Windows: PyAudio + SpeechRecognition)."""

    def __init__(self, language: str = "tr-TR"):
        if sr is None:
            raise RuntimeError("SpeechRecognition kurulu değil. pip install SpeechRecognition PyAudio")
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue[str] = queue.Queue()

    def listen_once(self, timeout: float = 5.0, phrase_time_limit: float = 12.0) -> str:
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = self.recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            raise RuntimeError(f"STT servisi hatası: {exc}") from exc

    def start_loop(self, on_text: Callable[[str], None] | None = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def worker() -> None:
            while not self._stop.is_set():
                try:
                    text = self.listen_once()
                except Exception as exc:  # mikrofon timeout vs.
                    if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                        continue
                    self._queue.put(f"[kulak-hata] {exc}")
                    continue
                if not text:
                    continue
                self._queue.put(text)
                if on_text:
                    on_text(text)

        self._thread = threading.Thread(target=worker, name="ear-loop", daemon=True)
        self._thread.start()

    def stop_loop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def pop_text(self, block: bool = False, timeout: float | None = None) -> str | None:
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
