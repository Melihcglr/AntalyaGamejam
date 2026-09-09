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


# Jarvis ESP varsayılan portu (80'e ek olarak taranır)
JARVIS_ESP_PORT = 8788
DEFAULT_SCAN_PORTS = (JARVIS_ESP_PORT, 80)

PROBE_PATHS = ("/health", "/", "/relay/status")
JARVIS_MARKERS = (
    "jarvis",
    "esp-hub",
    "esp_hub",
    "jarvis-relay",
    "jarvis_hub",
    "jarvis_relay",
    "pc-jarvis",
    "pc_online",
    "role\":\"esp-hub\"",
    "device\":\"jarvis-relay\"",
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


def _classify(text: str, data: Any | None) -> tuple[str, str]:
    """Yalnızca Jarvis işaretleri varsa hub/relay/esp; aksi halde http."""
    low = text.lower()
    blob = str(data).lower() if data is not None else low
    role = ""
    if isinstance(data, dict):
        role = str(data.get("role") or data.get("device") or "")
    role_l = role.lower()
    has_marker = any(m in blob for m in JARVIS_MARKERS) or any(m in low for m in JARVIS_MARKERS)
    if not has_marker:
        return "http", role

    if (
        role_l in {"esp-hub", "esp_hub", "jarvis-hub", "jarvis_hub"}
        or "esp-hub" in blob
        or "jarvis_hub" in blob
    ):
        return "jarvis_hub", role
    if (
        role_l in {"jarvis-relay", "jarvis_relay", "relay"}
        or "jarvis-relay" in blob
        or "jarvis_relay" in blob
        or ('"device": "jarvis-relay"' in blob)
        or ("device\":\"jarvis-relay\"" in blob)
    ):
        return "jarvis_relay", role
    return "jarvis_esp", role


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
                data = None
                try:
                    data = res.json()
                except Exception:
                    data = None
                kind, role = _classify(text, data)
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
    timeout: float = 0.3,
    workers: int = 64,
    jarvis_only: bool = False,
) -> ActionResult:
    """LAN'da HTTP cihaz ara; Jarvis ESP hub/relay'i önceliklendir."""
    started = time.time()
    try:
        network = guess_subnet(cidr)
    except Exception as exc:
        return ActionResult(False, str(exc))

    ports = ports or list(DEFAULT_SCAN_PORTS)
    hosts = [str(h) for h in network.hosts()]
    found: list[dict[str, Any]] = []
    seen_bases: set[str] = set()

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
            base = str(hit.get("base_url") or "")
            # Aynı IP'de 8788 varsa 80'i atla (tercih Jarvis portu)
            ip = str(hit.get("ip") or "")
            port = int(hit.get("port") or 0)
            if port == 80 and f"http://{ip}:{JARVIS_ESP_PORT}" in seen_bases:
                continue
            if base in seen_bases:
                continue
            # 80 bulunduysa ama sonra 8788 gelebilir — 80'i geçici tut, sonda süz
            found.append(hit)
            seen_bases.add(base)

    # Aynı IP için 8788'i tercih et
    by_ip: dict[str, dict[str, Any]] = {}
    for hit in found:
        ip = str(hit["ip"])
        prev = by_ip.get(ip)
        if prev is None:
            by_ip[ip] = hit
            continue
        if int(hit["port"]) == JARVIS_ESP_PORT and int(prev["port"]) != JARVIS_ESP_PORT:
            by_ip[ip] = hit
        elif int(prev["port"]) == JARVIS_ESP_PORT:
            continue
        elif str(hit["kind"]).startswith("jarvis") and not str(prev["kind"]).startswith("jarvis"):
            by_ip[ip] = hit
    found = list(by_ip.values())

    found.sort(key=lambda x: (0 if str(x["kind"]).startswith("jarvis") else 1, x["ip"]))
    elapsed = round(time.time() - started, 2)
    jarvis_n = sum(1 for f in found if str(f["kind"]).startswith("jarvis"))
    msg = (
        f"Tarama bitti: {len(found)} HTTP cihaz "
        f"({jarvis_n} Jarvis ESP), {elapsed}s — {network} "
        f"portlar {ports}."
    )
    return ActionResult(
        True,
        msg,
        data={
            "subnet": str(network),
            "elapsed_sec": elapsed,
            "count": len(found),
            "jarvis_count": jarvis_n,
            "ports": ports,
            "devices": found,
        },
    )


def _relay_spec(name: str, aliases: list[str], base_url: str) -> DeviceSpec:
    return DeviceSpec(
        name=name,
        aliases=aliases,
        base_url=base_url,
        on_path="/relay/on",
        off_path="/relay/off",
        toggle_path="/relay/toggle",
        status_path="/relay/status",
        method="GET",
    )


def adopt_discovered(
    discovered: list[dict[str, Any]],
    existing: dict[str, DeviceSpec],
    *,
    jarvis_only: bool = True,
) -> tuple[dict[str, DeviceSpec], list[str]]:
    """Bulunan Jarvis cihazlarını DeviceSpec olarak ekle.

    Hub hem `hub` hem (yoksa) `isik` olarak kaydedilir — sahneler/ışık komutları çalışsın.
    """
    updated = dict(existing)
    added: list[str] = []
    used_urls = {v.base_url.rstrip("/") for v in updated.values()}

    hub_i = relay_i = other_i = 0
    for item in discovered:
        kind = str(item.get("kind") or "")
        if jarvis_only and not kind.startswith("jarvis"):
            continue
        base = str(item.get("base_url") or "").rstrip("/")
        if not base:
            continue

        if kind == "jarvis_hub":
            if base in used_urls and any(
                v.base_url.rstrip("/") == base and k.startswith("hub") for k, v in updated.items()
            ):
                # Hub zaten var; isik eksikse tamamla
                if "isik" not in updated:
                    updated["isik"] = _relay_spec(
                        "Oda ışığı",
                        ["ışık", "isik", "lamba", "oda ışığı"],
                        base,
                    )
                    added.append("isik")
                continue
            hub_i += 1
            key = "hub" if hub_i == 1 and "hub" not in updated else f"hub{hub_i}"
            while key in updated:
                hub_i += 1
                key = f"hub{hub_i}"
            updated[key] = _relay_spec(
                "ESP Hub",
                ["hub", "esp hub", "merkez"],
                base,
            )
            used_urls.add(base)
            added.append(key)
            if "isik" not in updated:
                updated["isik"] = _relay_spec(
                    "Oda ışığı",
                    ["ışık", "isik", "lamba", "oda ışığı"],
                    base,
                )
                added.append("isik")
            continue

        if base in used_urls:
            continue

        if kind in {"jarvis_relay", "jarvis_esp"}:
            relay_i += 1
            key = "isik" if "isik" not in updated else f"esp{relay_i}"
            while key in updated:
                relay_i += 1
                key = f"esp{relay_i}"
            name = "Oda ışığı" if key == "isik" else f"ESP Röle {relay_i}"
            aliases = (
                ["ışık", "isik", "lamba", "oda ışığı"]
                if key == "isik"
                else [key, f"esp {relay_i}"]
            )
            updated[key] = _relay_spec(name, aliases, base)
            used_urls.add(base)
            added.append(key)
            continue

        if not jarvis_only:
            other_i += 1
            key = f"http{other_i}"
            while key in updated:
                other_i += 1
                key = f"http{other_i}"
            updated[key] = DeviceSpec(name=f"HTTP cihaz {other_i}", aliases=[key], base_url=base)
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
