from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from .config import Settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


SYSTEM_PROMPT = """Sen Windows üzerinde çalışan kişisel bir asistansın (Jarvis tarzı).
Kullanıcı Türkçe konuşur. Kısa, net ve eyleme dönük cevap ver.

Sadece şu JSON şemasını döndür:
{
  "speech": "Kullanıcıya sesli söylenecek kısa Türkçe cevap",
  "action": {
    "type": "none|open_app|open_url|shell|type_text|camera|screen|describe_camera|describe_screen|status|list_apps|time|search|note_add|note_list|note_clear|volume|processes|open_path",
    "target": "hedef (uygulama adı, url, komut, arama, not veya yol)",
    "confirm_token": null
  }
}

Kurallar:
- Tehlikeli silme/format/kapatma isteme; shell için mümkün olduğunca kaçın.
- open_app target: notepad, explorer, chrome, edge, calculator, spotify, vscode gibi kısa anahtar.
- volume target: up|down|mute
- search target: arama metni
- note_add target: not metni
- open_path target: klasör/dosya yolu
- Bilmiyorsan action.type = none ve speech ile açıkla.
- JSON dışında hiçbir şey yazma.
"""


def strip_wake(text: str, wake_word: str, assistant_name: str) -> str:
    cleaned = text.strip()
    patterns = [
        rf"^\s*{re.escape(wake_word)}\s*[,:]?\s*",
        rf"^\s*hey\s+{re.escape(wake_word)}\s*[,:]?\s*",
        rf"^\s*{re.escape(assistant_name)}\s*[,:]?\s*",
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or text.strip()


class Brain:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if settings.openai_api_key and OpenAI is not None:
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
            )

    @property
    def ready(self) -> bool:
        return self._client is not None

    def plan(self, user_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        # Önce çevrimdışı kurallar — hızlı ve deterministik.
        offline = self._offline_plan(user_text)
        if offline["action"]["type"] != "none" or not self._client:
            return offline

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json_dumps(
                    {"utterance": user_text, "context": context or {}},
                ),
            },
        ]
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = __import__("json").loads(raw)
        except Exception:
            return {
                "speech": "Planı çözümleyemedim.",
                "action": {"type": "none", "target": "", "confirm_token": None},
            }
        action = data.get("action") or {}
        return {
            "speech": data.get("speech") or "Tamam.",
            "action": {
                "type": action.get("type") or "none",
                "target": action.get("target") or "",
                "confirm_token": action.get("confirm_token"),
            },
        }

    def describe_image(self, image_path: Path, prompt: str | None = None) -> str:
        if not self._client:
            return "Görüntü analizi için API anahtarı gerekli."
        data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        question = prompt or "Bu görüntüde ne var? Kısa Türkçe özetle."
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{data}"},
                        },
                    ],
                }
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip() or "Görüntü boş göründü."

    def _offline_plan(self, user_text: str) -> dict[str, Any]:
        text = user_text.lower().strip()

        note_match = re.search(r"(?:not al|hatırla|not et)\s*[:\-]?\s*(.+)$", text)
        if note_match:
            return plan("note_add", note_match.group(1).strip(), "Notu kaydettim.")

        if any(k in text for k in ("notlarımı göster", "notları listele", "notlar")):
            return plan("note_list", "", "Notlarına bakıyorum.")
        if any(k in text for k in ("notları sil", "notları temizle")):
            return plan("note_clear", "", "Notları temizliyorum.")

        if any(k in text for k in ("saat kaç", "tarih", "bugün günlerden")):
            return plan("time", "", "Zamanı söylüyorum.")

        search_match = re.search(r"(?:ara|google|bing)\s+(.+)$", text)
        if search_match:
            q = search_match.group(1).strip()
            return plan("search", q, f"{q} için arama açıyorum.")

        if "sesi kapat" in text or "sessiz" in text or "mute" in text:
            return plan("volume", "mute", "Sesi kapatıyorum.")
        if "sesi aç" in text or "ses artır" in text or "ses yükselt" in text:
            return plan("volume", "up", "Sesi yükseltiyorum.")
        if "ses kıs" in text or "ses azalt" in text:
            return plan("volume", "down", "Sesi kısayım.")

        if any(k in text for k in ("çalışan program", "süreçler", "process")):
            return plan("processes", "", "Çalışan süreçlere bakıyorum.")

        if "açıkl" in text and "ekran" in text:
            return plan("describe_screen", "", "Ekranı inceliyorum.")
        if "açıkl" in text and ("kamera" in text or "foto" in text):
            return plan("describe_camera", "", "Kameradaki görüntüyü inceliyorum.")

        path_match = re.search(r"(?:klasörü? aç|dosyayı? aç)\s+(.+)$", text)
        if path_match:
            return plan("open_path", path_match.group(1).strip(), "Yolu açıyorum.")

        mapping = [
            (("not defteri", "notepad"), "open_app", "notepad", "Not defterini açıyorum."),
            (("dosya gezgin", "explorer"), "open_app", "explorer", "Gezgini açıyorum."),
            (("hesap makinesi", "calculator", "calc"), "open_app", "calculator", "Hesap makinesini açıyorum."),
            (("chrome",), "open_app", "chrome", "Chrome'u açıyorum."),
            (("edge",), "open_app", "edge", "Edge'i açıyorum."),
            (("spotify",), "open_app", "spotify", "Spotify'ı açıyorum."),
            (("vscode", "visual studio code", "kod editör"), "open_app", "vscode", "VS Code'u açıyorum."),
            (("fotoğraf çek", "kameradan", "kamera aç", "kamera"), "camera", "", "Kameradan kare alıyorum."),
            (("ekran görüntüsü", "ekranı yakala", "ekranı kaydet"), "screen", "", "Ekran görüntüsü alıyorum."),
            (("durum", "sistem"), "status", "", "Sistem durumuna bakıyorum."),
            (("uygulamalar", "izinli uygulam"), "list_apps", "", "İzinli uygulamaları listeliyorum."),
            (("youtube",), "open_url", "https://www.youtube.com", "YouTube'u açıyorum."),
            (("gmail",), "open_url", "https://mail.google.com", "Gmail'i açıyorum."),
            (("hava durumu",), "search", "hava durumu", "Hava durumu aramasını açıyorum."),
        ]
        for keys, action_type, target, speech in mapping:
            if any(k in text for k in keys):
                return plan(action_type, target, speech)

        if "http://" in text or "https://" in text:
            for part in user_text.split():
                if part.startswith("http"):
                    return plan("open_url", part, "Sayfayı açıyorum.")

        site_match = re.search(r"(?:siteyi? aç|web['’]?i? aç)\s+(\S+)", text)
        if site_match:
            return plan("open_url", site_match.group(1), "Siteyi açıyorum.")

        if not self._client:
            return plan(
                "none",
                "",
                "Anladım ama bu komutu çevrimdışı bilmiyorum. "
                "Örnek: not defteri aç, saat kaç, ara python, not al süt al, kamera, ekranı açıkla.",
            )
        return plan("none", "", "")


def plan(action_type: str, target: str, speech: str) -> dict[str, Any]:
    return {
        "speech": speech,
        "action": {"type": action_type, "target": target, "confirm_token": None},
    }


def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


def local_time_speech(tz_name: str = "Europe/Istanbul") -> str:
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        now = datetime.now()
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return (
        f"Bugün {days[now.weekday()]}, {now.day}.{now.month}.{now.year}, "
        f"saat {now.hour:02d}:{now.minute:02d}."
    )


def search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"
