from __future__ import annotations

import re
import socket
from typing import Iterable

from .hands import ActionResult


def normalize_mac(mac: str) -> bytes:
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac)
    if len(cleaned) != 12:
        raise ValueError(f"Geçersiz MAC: {mac}")
    return bytes.fromhex(cleaned)


def send_wol(mac: str, broadcast: str = "255.255.255.255", ports: Iterable[int] = (9, 7)) -> ActionResult:
    try:
        mac_bytes = normalize_mac(mac)
    except ValueError as exc:
        return ActionResult(False, str(exc))
    packet = b"\xff" * 6 + mac_bytes * 16
    sent = 0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for port in ports:
                sock.sendto(packet, (broadcast, port))
                sent += 1
    except OSError as exc:
        return ActionResult(False, f"WOL gönderilemedi: {exc}")
    return ActionResult(
        True,
        f"Wake-on-LAN gönderildi ({mac}).",
        data={"mac": mac, "packets": sent, "broadcast": broadcast},
    )
