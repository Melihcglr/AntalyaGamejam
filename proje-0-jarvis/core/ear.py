from __future__ import annotations

import io
import json
import queue
import threading
import wave
from pathlib import Path
from typing import Callable

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None  # type: ignore

try:
    import vosk  # type: ignore
except ImportError:  # pragma: no cover
    vosk = None  # type: ignore


class Ear:
    """Mikrofon dinleyici — mute / PTT / konuşurken pause + yerel STT (Vosk)."""

    def __init__(
        self,
        language: str = "tr-TR",
        *,
        stt_backend: str = "auto",
        stt_model_path: str = "",
        push_to_talk: bool = False,
    ):
        if sr is None:
            raise RuntimeError(
                "SpeechRecognition kurulu değil. pip install SpeechRecognition PyAudio"
            )
        self.language = language
        self.stt_backend = (stt_backend or "auto").lower()
        self.stt_model_path = (stt_model_path or "").strip()
        self.push_to_talk = bool(push_to_talk)
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self._stop = threading.Event()
        self._muted = threading.Event()
        self._paused = threading.Event()
        self._ptt_active = threading.Event()
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue[str] = queue.Queue()
        self._vosk_model = None
        self._engine_name = "google"

    @property
    def muted(self) -> bool:
        return self._muted.is_set()

    @property
    def speaking_paused(self) -> bool:
        return self._paused.is_set()

    @property
    def engine_name(self) -> str:
        return self._engine_name

    def set_muted(self, muted: bool) -> None:
        if muted:
            self._muted.set()
        else:
            self._muted.clear()

    def set_push_to_talk(self, enabled: bool) -> None:
        self.push_to_talk = bool(enabled)
        if not self.push_to_talk:
            self._ptt_active.clear()

    def set_ptt_active(self, active: bool) -> None:
        if active:
            self._ptt_active.set()
        else:
            self._ptt_active.clear()

    def pause_for_speech(self) -> None:
        self._paused.set()

    def resume_after_speech(self) -> None:
        self._paused.clear()

    def _should_capture(self) -> bool:
        if self._muted.is_set() or self._paused.is_set():
            return False
        if self.push_to_talk and not self._ptt_active.is_set():
            return False
        return True

    def _ensure_vosk(self) -> bool:
        if self._vosk_model is not None:
            return True
        if vosk is None or not self.stt_model_path:
            return False
        path = Path(self.stt_model_path).expanduser()
        if not path.exists():
            return False
        self._vosk_model = vosk.Model(str(path))
        return True

    def _want_vosk(self) -> bool:
        if self.stt_backend == "vosk":
            return True
        if self.stt_backend == "auto":
            return bool(self.stt_model_path) and Path(self.stt_model_path).expanduser().exists()
        return False

    def _recognize_vosk(self, audio) -> str:
        if not self._ensure_vosk():
            raise RuntimeError("Vosk model yok veya vosk kurulu değil")
        raw = audio.get_wav_data()
        with wave.open(io.BytesIO(raw), "rb") as wf:
            rec = vosk.KaldiRecognizer(self._vosk_model, wf.getframerate())
            rec.SetWords(False)
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)
            result = json.loads(rec.FinalResult() or "{}")
        return str(result.get("text") or "").strip()

    def listen_once(self, timeout: float = 5.0, phrase_time_limit: float = 12.0) -> str:
        if not self._should_capture():
            return ""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = self.recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        if not self._should_capture():
            return ""

        if self._want_vosk():
            try:
                text = self._recognize_vosk(audio)
                self._engine_name = "vosk"
                return text
            except Exception as exc:
                if self.stt_backend == "vosk":
                    raise RuntimeError(f"Vosk STT hatası: {exc}") from exc

        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            self._engine_name = "google"
            return text
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
                if not self._should_capture():
                    self._stop.wait(0.15)
                    continue
                try:
                    text = self.listen_once()
                except Exception as exc:
                    msg = str(exc).lower()
                    if "timed out" in msg or "timeout" in msg:
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
