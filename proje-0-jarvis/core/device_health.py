from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from .iot_models import DeviceSpec


def resolve_host(hostname: str, timeout: float = 2.0) -> str | None:
    """mDNS / DNS çözümle; başarısızsa None."""
    host = hostname.strip().rstrip(".")
    if not host:
        return None
    try:
        socket.setdefaulttimeout(timeout)
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        if infos:
            return infos[0][4][0]
    except OSError:
        return None
    finally:
        socket.setdefaulttimeout(None)
    return None


def probe_url(url: str, timeout: float = 1.2) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            res = client.get(url.rstrip("/") + "/health")
            if res.status_code == 200:
                return True, "ok"
            # bazı rölelerde /health yok — kök dene
            res2 = client.get(url.rstrip("/") + "/")
            if res2.status_code == 200:
                return True, "ok-root"
            return False, f"HTTP {res.status_code}"
    except Exception as exc:
        return False, str(exc)[:120]


def check_devices(
    devices: dict[str, DeviceSpec],
    *,
    mdns_name: str = "",
    preferred_port: int = 8788,
) -> dict[str, Any]:
    """Kayıtlı cihazları yokla; düşenlerde mDNS ile IP öner."""
    items: dict[str, Any] = {}
    warnings: list[str] = []
    mdns_ip = resolve_host(mdns_name) if mdns_name else None

    for key, spec in devices.items():
        base = (spec.base_url or "").rstrip("/")
        ok, detail = probe_url(base) if base else (False, "base_url yok")
        entry: dict[str, Any] = {
            "ok": ok,
            "base_url": base,
            "detail": detail,
            "suggested_url": None,
        }
        if not ok and mdns_ip:
            suggested = f"http://{mdns_ip}:{preferred_port}"
            ok2, detail2 = probe_url(suggested)
            if ok2:
                entry["suggested_url"] = suggested
                warnings.append(
                    f"{key}: {base} yanıt vermiyor; {mdns_name} → {suggested} çalışıyor. "
                    "config'te base_url güncelle veya 'esp bul' de."
                )
            else:
                warnings.append(f"{key}: erişilemiyor ({detail})")
        elif not ok:
            warnings.append(f"{key}: erişilemiyor ({detail})")
        items[key] = entry

    return {
        "devices": items,
        "warnings": warnings,
        "mdns_name": mdns_name or None,
        "mdns_ip": mdns_ip,
    }


def hostname_from_url(url: str) -> str | None:
    try:
        return urlparse(url).hostname
    except Exception:
        return None
