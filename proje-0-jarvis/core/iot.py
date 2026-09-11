from __future__ import annotations

from typing import Any

import httpx

from .hands import ActionResult
from .iot_models import DeviceSpec


class IoTHub:
    """ESP32 / akıllı oda cihazları — HTTP röle kontrolü."""

    def __init__(self, devices: dict[str, DeviceSpec]):
        self.devices = {k.lower(): v for k, v in devices.items()}

    def resolve(self, name: str) -> tuple[str, DeviceSpec] | None:
        q = name.lower().strip()
        if q in self.devices:
            return q, self.devices[q]
        for key, spec in self.devices.items():
            aliases = [a.lower() for a in spec.aliases] + [key, (spec.name or "").lower()]
            if q in aliases or any(q in a or a in q for a in aliases if a):
                return key, spec
        return None

    def set_state(self, name: str, state: str) -> ActionResult:
        found = self.resolve(name)
        if not found:
            return ActionResult(False, f"Cihaz yok: {name}")
        key, spec = found
        state_l = state.lower().strip()
        if state_l in {"on", "aç", "ac", "1", "true"}:
            path = spec.on_path
            label = "açıldı"
            norm = "on"
        elif state_l in {"off", "kapat", "0", "false"}:
            path = spec.off_path
            label = "kapatıldı"
            norm = "off"
        elif state_l in {"toggle", "değiştir", "degistir"}:
            path = spec.toggle_path
            label = "toggle"
            norm = "toggle"
        else:
            return ActionResult(False, "state: on|off|toggle")

        ok, body, err = self._request(spec, path)
        if not ok:
            return ActionResult(False, f"{spec.name or key}: {err}")
        return ActionResult(
            True,
            f"{spec.name or key} {label}.",
            data={"device": key, "state": norm, "response": body},
        )

    def status(self, name: str | None = None) -> ActionResult:
        items: dict[str, Any] = {}
        targets = [name] if name else list(self.devices)
        for raw in targets:
            found = self.resolve(raw) if name else (raw, self.devices[raw])
            if not found:
                continue
            key, spec = found
            ok, body, err = self._request(spec, spec.status_path)
            items[key] = {"ok": ok, "body": body if ok else err, "name": spec.name or key}
        if not items:
            return ActionResult(False, "Cihaz bulunamadı.")
        summary = ", ".join(
            f"{k}:{'ok' if v['ok'] else 'hata'}" for k, v in items.items()
        )
        return ActionResult(True, f"Cihaz durumu — {summary}", data={"devices": items})

    def list_devices(self) -> ActionResult:
        data = {
            k: {"name": v.name or k, "aliases": v.aliases, "base_url": v.base_url}
            for k, v in self.devices.items()
        }
        return ActionResult(True, "Kayıtlı cihazlar", data={"devices": data})

    def _request(self, spec: DeviceSpec, path: str) -> tuple[bool, Any, str]:
        url = spec.base_url.rstrip("/") + "/" + path.lstrip("/")
        headers = {}
        if spec.token:
            headers["Authorization"] = f"Bearer {spec.token}"
        try:
            with httpx.Client(timeout=spec.timeout_sec) as client:
                if spec.method.upper() == "POST":
                    res = client.post(url, headers=headers)
                else:
                    res = client.get(url, headers=headers)
            if res.status_code >= 400:
                return False, None, f"HTTP {res.status_code}: {res.text[:200]}"
            try:
                return True, res.json(), ""
            except Exception:
                return True, res.text[:300], ""
        except Exception as exc:
            return False, None, str(exc)
