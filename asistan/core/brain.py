from __future__ import annotations

import json
from typing import Any

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
    "type": "none|open_app|open_url|shell|type_text|camera|screen|status|list_apps",
    "target": "hedef (uygulama adı, url, komut veya metin)",
    "confirm_token": null
  }
}

Kurallar:
- Tehlikeli silme/format/kapatma isteme; shell için mümkün olduğunca kaçın.
- open_app target: notepad, explorer, chrome, edge, calculator gibi kısa anahtar.
- Bilmiyorsan action.type = none ve speech ile açıkla.
- JSON dışında hiçbir şey yazma.
"""


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
        if not self._client:
            return self._offline_plan(user_text)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"utterance": user_text, "context": context or {}},
                    ensure_ascii=False,
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
            data = json.loads(raw)
        except json.JSONDecodeError:
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

    def _offline_plan(self, user_text: str) -> dict[str, Any]:
        text = user_text.lower().strip()
        mapping = [
            (("not defteri", "notepad"), "open_app", "notepad", "Not defterini açıyorum."),
            (("dosya gezgin", "explorer"), "open_app", "explorer", "Gezgini açıyorum."),
            (("hesap makinesi", "calculator"), "open_app", "calculator", "Hesap makinesini açıyorum."),
            (("chrome",), "open_app", "chrome", "Chrome'u açıyorum."),
            (("edge",), "open_app", "edge", "Edge'i açıyorum."),
            (("fotoğraf çek", "kameradan", "kamera"), "camera", "", "Kameradan kare alıyorum."),
            (("ekran görüntüsü", "ekranı yakala"), "screen", "", "Ekran görüntüsü alıyorum."),
            (("durum", "sistem"), "status", "", "Sistem durumuna bakıyorum."),
            (("uygulamalar", "listele"), "list_apps", "", "İzinli uygulamaları listeliyorum."),
        ]
        for keys, action_type, target, speech in mapping:
            if any(k in text for k in keys):
                return {
                    "speech": speech,
                    "action": {"type": action_type, "target": target, "confirm_token": None},
                }
        if text.startswith("aç http") or "http://" in text or "https://" in text:
            for part in user_text.split():
                if part.startswith("http"):
                    return {
                        "speech": "Sayfayı açıyorum.",
                        "action": {"type": "open_url", "target": part, "confirm_token": None},
                    }
        return {
            "speech": (
                "API anahtarı yok; çevrimdışı moddayım. "
                "Şunları deneyebilirsin: not defteri aç, kamera, ekran görüntüsü, sistem durumu."
            ),
            "action": {"type": "none", "target": "", "confirm_token": None},
        }
