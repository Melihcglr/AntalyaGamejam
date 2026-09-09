from __future__ import annotations

import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import httpx

from .hands import ActionResult
from .iot_models import DeviceSpec  # noqa: TC001


# Jarvis ESP uçları
PROBE_PATHS = ("/health", "/", "/relay/status", "/api/health")
JARVIS_MARKERS = (
    "jarvis",
    "esp-hub",
    "esp_hub",
    "jarvis-relay",
    "jarvis_hub",
    "jarvis-relay",
    "pc_online",
    "pc-jarvis",
    "pc_online",
)


def local_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def guess_subnet(cidr: str | None = None) -> ipaddress.IPv4Network:
    if cidr:
        return ipaddress.ip_network(cidr, strict=False)
    ip = local_ipv4()
    if not ip:
        raise RuntimeError("Yerel IP bulunamadı; subnet ver (örn. 192.168.1.0/24).")
    return ipaddress.ip_network(f"{ip}/24", strict=False)


def _probe_host(ip: str, port: int, timeout: float) -> dict[str, Any] | None:
    base = f"http://{ip}:{port}"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            for path in PROBE_PATHS:
                try:
                    res = client.get(base + path)
                except Exception:
                    continue
                if res.status_code != 200:
                    continue
                text = (res.text or "")[:800]
                low = text.lower()
                kind = "http"
                role = ""
                try:
                    data = res.json()
                    blob = str(data).lower()
                    if any(m in blob for m in JARVIS_MARKERS) or any(m in low for m in JARVIS_MARKERS):
                        kind = "jarvis_esp"
                    role = str(data.get("role") or data.get("device") or "")
                    if "hub" in role.lower() or "esp-hub" in blob:
                        kind = "jarvis_hub"
                    elif "relay" in role.lower() or "relay" in blob:
                        kind = "jarvis_relay"
                except Exception:
                    if any(m in low for m in JARVIS_MARKERS):
                        kind = "jarvis_esp"
                return {
                    "ip": ip,
                    "port": port,
                    "base_url": base,
                    "path": path,
                    "kind": kind,
                    "role": role,
                    "snippet": text[:160],
                }
    except Exception:
        return None
    return None


def scan_network(
    *,
    cidr: str | None = None,
    ports: list[int] | None = None,
    timeout: float = 0.35,
    workers: int = 64,
    jarvis_only: bool = False,
) -> ActionResult:
    """LAN'da HTTP cihaz ara; Jarvis ESP hub/relay'i önceliklendir."""
    started = time.time()
    try:
        network = guess_subnet(cidr)
    except Exception as exc:
        return ActionResult(False, str(exc))

    ports = ports or [80]
    hosts = [str(h) for h in network.hosts()]
    found: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_probe_host, ip, port, timeout): (ip, port)
            for ip in hosts
            for port in ports
        }
        for fut in as_completed(futures):
            try:
                hit = fut.result()
            except Exception:
                continue
            if not hit:
                continue
            if jarvis_only and not str(hit.get("kind", "")).startswith("jarvis"):
                continue
            found.append(hit)

    found.sort(key=lambda x: (0 if str(x["kind"]).startswith("jarvis") else 1, x["ip"]))
    elapsed = round(time.time() - started, 2)
    jarvis_n = sum(1 for f in found if str(f["kind"]).startswith("jarvis"))
    msg = (
        f"Tarama bitti: {len(found)} HTTP cihaz "
        f"({jarvis_n} Jarvis ESP), {elapsed}s — {network}."
    )
    return ActionResult(
        True,
        msg,
        data={
            "subnet": str(network),
            "elapsed_sec": elapsed,
            "count": len(found),
            "jarvis_count": jarvis_n,
            "devices": found,
        },
    )


def adopt_discovered(
    discovered: list[dict[str, Any]],
    existing: dict[str, DeviceSpec],
    *,
    jarvis_only: bool = True,
) -> tuple[dict[str, DeviceSpec], list[str]]:
    """Bulunan cihazları DeviceSpec olarak ekle; yeni anahtar listesi döner."""
    updated = dict(existing)
    added: list[str] = []
    used_urls = {v.base_url.rstrip("/") for v in updated.values()}

    hub_i = relay_i = other_i = 0
    for item in discovered:
        kind = str(item.get("kind") or "")
        if jarvis_only and not kind.startswith("jarvis"):
            continue
        base = str(item.get("base_url") or "").rstrip("/")
        if not base or base in used_urls:
            continue
        if kind == "jarvis_hub":
            hub_i += 1
            key = "hub" if hub_i == 1 else f"hub{hub_i}"
            name = "ESP Hub"
            aliases = ["hub", "esp hub", "merkez"]
        elif kind in {"jarvis_relay", "jarvis_esp"}:
            relay_i += 1
            key = "isik" if relay_i == 1 and "isik" not in updated else f"esp{relay_i}"
            if key in updated:
                key = f"esp{relay_i}"
            name = f"ESP Röle {relay_i}"
            aliases = ["ışık", "isik", "lamba"] if key == "isik" else [key, f"esp {relay_i}"]
        else:
            other_i += 1
            key = f"http{other_i}"
            name = f"HTTP cihaz {other_i}"
            aliases = [key]

        # Anahtar çakışmasını çöz
        base_key = key
        n = 2
        while key in updated:
            key = f"{base_key}{n}"
            n += 1

        updated[key] = DeviceSpec(
            name=name,
            aliases=aliases,
            base_url=base,
            on_path="/relay/on",
            off_path="/relay/off",
            toggle_path="/relay/toggle",
            status_path="/relay/status" if "relay" in kind or kind == "jarvis_esp" else "/health",
        )
        used_urls.add(base)
        added.append(key)

    return updated, added


def already_known_ips(devices: dict[str, DeviceSpec]) -> set[str]:
    ips: set[str] = set()
    for spec in devices.values():
        try:
            host = urlparse(spec.base_url).hostname
            if host:
                ips.add(host)
        except Exception:
            continue
    return ips
