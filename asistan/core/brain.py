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
    "type": "none|open_app|open_url|shell|type_text|camera|screen|describe_camera|describe_screen|status|list_apps|time|search|note_add|note_list|note_clear|volume|processes|open_path|open_cursor|open_project|create_site|agent_prompt|list_projects",
    "target": "hedef (uygulama, url, arama, proje adı, site brief veya görev)",
    "monitor": null,
    "confirm_token": null
  }
}

Kurallar:
- "valorantı ekran 2 de aç" → open_app target=valorant, monitor=2
- "cursor aç" → open_cursor
- "asistan projesini cursor'da aç" → open_project target=asistan
- "bana restoran sitesi yap" / "şu tarz bir site yap: ..." → create_site
- "projeye şunu ekle/düzenle: ..." → agent_prompt (Cursor için görev notu)
- "bunu google'la araştır: ..." / "bana X araştır" → search
- Tehlikeli silme/format/kapatma isteme; shell için mümkün olduğunca kaçın.
- open_app target: notepad, explorer, chrome, edge, calculator, spotify, vscode, cursor, valorant, discord, steam
- volume target: up|down|mute
- JSON dışında hiçbir şey yazma.
"""

# anahtar -> konuşma aliasları
APP_ALIASES: dict[str, tuple[str, ...]] = {
    "valorant": ("valorant", "valo"),
    "notepad": ("not defteri", "notepad"),
    "explorer": ("dosya gezgin", "explorer", "gezgin"),
    "calculator": ("hesap makinesi", "calculator", "calc"),
    "chrome": ("chrome", "google chrome"),
    "edge": ("edge", "microsoft edge"),
    "spotify": ("spotify",),
    "vscode": ("vscode", "visual studio code", "kod editör"),
    "cursor": ("cursor", "kürsör", "cursor ide"),
    "discord": ("discord",),
    "steam": ("steam",),
    "cmd": ("cmd", "komut istemi"),
}


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


def extract_monitor(text: str) -> int | None:
    patterns = [
        r"(?:ekran|monitör|monitor)\s*(?:numara(?:sı)?\s*)?(\d+)",
        r"(\d+)\s*(?:\.|inci|nci|uncu|üncü)?\s*(?:ekran|monitör|monitor)",
        r"(?:ekran|monitör|monitor)\s*(\d+)\s*(?:de|da|te|ta)?",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def extract_google_query(text: str) -> str | None:
    raw = text.strip()
    patterns = [
        r"(?:google['’`]?\s*l[ae]|google['’`]?\s*ile|google['’`]?\s*da|google['’`]?\s*de)\s+(?:araştır(?:ma)?|ara(?!ştır))\s*[:\-]?\s*(.+)$",
        r"(?:araştır(?:ma)?|ara(?!ştır))\s+(?:şunu\s+)?(?:google['’`]?\s*l[ae]|google['’`]?\s*ile|google['’`]?\s*da|google['’`]?\s*de)\s*[:\-]?\s*(.+)$",
        r"bana\s+(.+?)\s+(?:google['’`]?\s*l[ae]\s+)?(?:araştır(?:ma)?|ara(?!ştır))(?:\s+google['’`]?\s*l[ae])?$",
        r"(.+?)\s+(?:konusunda|hakkında)\s+(?:google['’`]?\s*(?:l[ae]|ile|da|de)\s+)?(?:araştır(?:ma)?|ara(?!ştır))\b",
        r"(?:şunu|bunu)\s+(?:google['’`]?\s*l[ae]|google['’`]?\s*ile)\s+(?:araştır(?:ma)?|ara(?!ştır))\s*[:\-]?\s*(.+)$",
        r"(?:şunu|bunu)\s+(?:araştır(?:ma)?|ara(?!ştır))\s*[:\-]?\s*(.+)$",
        r"google\s+(?:ile\s+)?(?:araştır(?:ma)?|ara(?!ştır))\s*[:\-]?\s*(.+)$",
        r"\b(?:ara|google|bing)\s+(.+)$",
    ]
    for pat in patterns:
        m = re.search(pat, raw, flags=re.IGNORECASE)
        if m:
            q = m.group(1).strip(" .,:;!?")
            if not q or len(q) < 2:
                continue
            # Uygulama aç komutunu arama sanma
            if match_open_app(q) or match_open_app(raw):
                opened = match_open_app(raw)
                if opened:
                    continue
            return q
    return None


def match_coding_intent(text: str) -> dict[str, Any] | None:
    """Site/proje/Cursor düzenleme niyetleri."""
    lowered = text.strip().lower()

    if any(k in lowered for k in ("projeleri listele", "kayıtlı projeler", "projelerim")):
        return plan("list_projects", "", "Projeleri listeliyorum.")

    m = re.search(
        r"(.+?)\s*(?:projesini|klasörünü)?\s*(?:cursor|kürsör)\s*(?:['’]?da|['’]?de|ile)?\s*aç",
        lowered,
    )
    if m:
        proj = m.group(1).strip(" '\"")
        proj = re.sub(r"^(?:bana|şu|bu)\s+", "", proj).strip()
        if proj and proj not in {"cursor", "kürsör"} and "site" not in proj:
            return plan("open_project", proj, f"{proj} projesini Cursor'da açıyorum.")

    if re.search(r"\b(?:cursor|kürsör)\b", lowered) and re.search(
        r"(?<![a-zçğıöşü])aç(?![a-zçğıöşü])", lowered
    ):
        return plan("open_cursor", "", "Cursor'u açıyorum.")

    site_patterns = [
        r"(?:bana\s+)?(?:şu\s+tarz(?:da)?\s+)?(?:bir\s+)?(?:internet\s+)?(?:web\s+)?sitesi?\s+yap\s*[:\-]?\s*(.+)$",
        r"(?:bana\s+)?(.+?)\s+sitesi?\s+yap",
        r"(?:yeni\s+)?(?:web\s+)?site\s+oluştur\s*[:\-]?\s*(.+)$",
        r"(?:landing\s+page|açılış\s+sayfası)\s+yap\s*[:\-]?\s*(.+)$",
    ]
    for pat in site_patterns:
        sm = re.search(pat, lowered)
        if sm:
            brief = sm.group(1).strip(" .,:;!?")
            if len(brief) >= 2:
                return plan(
                    "create_site",
                    brief,
                    f"'{brief}' sitesini hazırlayıp Cursor'da açıyorum.",
                )

    edit_patterns = [
        r"(?:şu\s+)?(?:projeyi|projeye|dosyayı|koda)\s+(?:şunu\s+)?(?:düzenle|ekle|değiştir|güncelle)\s*[:\-]?\s*(.+)$",
        r"(.+?)\s+(?:projesine|projesinde)\s+(?:şunu\s+)?(?:ekle|düzenle|yap)\s*[:\-]?\s*(.+)$",
        r"(?:cursor(?:['’]?da)?|kürsör(?:['’]?de)?)\s+(?:şunu\s+)?(?:yap|düzenle|yaz)\s*[:\-]?\s*(.+)$",
        r"agent(?:['’]?a)?\s+(?:şunu\s+)?(?:söyle|yaz|ver)\s*[:\-]?\s*(.+)$",
    ]
    for pat in edit_patterns:
        em = re.search(pat, lowered)
        if em:
            if em.lastindex and em.lastindex >= 2:
                target = f"{em.group(1).strip()}::{em.group(2).strip()}"
            else:
                target = em.group(em.lastindex or 1).strip()
            if len(target) >= 3:
                return plan(
                    "agent_prompt",
                    target,
                    "Cursor için görev notunu yazıp projeyi açıyorum.",
                )
    return None


def match_open_app(text: str) -> tuple[str, int | None] | None:
    """Uygulama aç komutunu ve isteğe bağlı ekran numarasını yakala."""
    lowered = text.lower().strip()
    monitor = extract_monitor(lowered)
    # monitör ifadesini temizle ki alias eşleşsin
    cleaned = re.sub(
        r"(?:ekran|monitör|monitor)\s*(?:numara(?:sı)?\s*)?\d+(?:\s*(?:de|da|te|ta))?",
        " ",
        lowered,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\d+\s*(?:\.|inci|nci|uncu|üncü)?\s*(?:ekran|monitör|monitor)(?:\s*(?:de|da|te|ta))?",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    open_words = re.search(
        r"(?<![a-zçğıöşü])(aç|başlat|çalıştır|açıver|açsana)(?![a-zçğıöşü])",
        cleaned,
    )
    if not open_words and monitor is None:
        return None
    if not open_words and monitor is not None:
        # "valorant ekran 2" gibi kısa form — alias şart
        pass
    for key, aliases in APP_ALIASES.items():
        for alias in aliases:
            # Türkçe ek: valorantı, valorant'ı
            if re.search(rf"\b{re.escape(alias)}(?:['’]?[ıiuü])?\b", cleaned):
                return key, monitor
            if alias in cleaned:
                return key, monitor
    return None


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
        offline = self._offline_plan(user_text)
        if offline["action"]["type"] != "none" or not self._client:
            return offline

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json_dumps({"utterance": user_text, "context": context or {}}),
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
            return plan("none", "", "Planı çözümleyemedim.")
        action = data.get("action") or {}
        monitor = action.get("monitor")
        try:
            monitor_i = int(monitor) if monitor is not None else None
        except (TypeError, ValueError):
            monitor_i = None
        return {
            "speech": data.get("speech") or "Tamam.",
            "action": {
                "type": action.get("type") or "none",
                "target": action.get("target") or "",
                "monitor": monitor_i,
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

        coding = match_coding_intent(text)
        if coding:
            return coding

        # Uygulama + ekran (Valorant vb.) — aramadan ÖNCE
        opened = match_open_app(text)
        if opened:
            app_key, monitor = opened
            # "açıkl" içeren ekran cümlelerini ele
            if "açıkl" in text and "ekran" in text and app_key not in text:
                pass
            else:
                speech = f"{app_key} açıyorum."
                if monitor is not None:
                    speech = f"{app_key} ekran {monitor}'de açıyorum."
                return plan("open_app", app_key, speech, monitor=monitor)

        query = extract_google_query(text)
        if query:
            return plan("search", query, f"Google'da araştırıyorum: {query}")

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
                "Örnek: valorantı ekran 2 de aç, google'la araştır ..., not defteri aç.",
            )
        return plan("none", "", "")


def plan(
    action_type: str,
    target: str,
    speech: str,
    monitor: int | None = None,
) -> dict[str, Any]:
    return {
        "speech": speech,
        "action": {
            "type": action_type,
            "target": target,
            "monitor": monitor,
            "confirm_token": None,
        },
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
