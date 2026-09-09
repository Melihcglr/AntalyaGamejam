# ESP32 ↔ PC Jarvis hub

## Mimari

```
Ses / telefon / panel
        │
        ▼
   ESP32 Hub  (her zaman açık)
        │
        ├─ PC online? ──GET /api/health──► Windows Jarvis
        │                      │
        │                      └─ POST /api/command  (oyun modu, cursor, ışık…)
        │
        └─ PC offline?
               ├─ ışık aç/kapat  (röle)
               └─ bilgisayar aç  (Wake-on-LAN / power röle)
```

PC açılınca Windows’ta Jarvis otomatik başlar; aynı WiFi’de ESP bundan sonra komutları PC’ye yollar.

## 1) ESP firmware

Tercih edilen: `jarvis_hub/jarvis_hub.ino`

Doldur:
- `WIFI_SSID` / `WIFI_PASS`
- `PC_HOST` = PC’nin yerel IP’si (sabit IP önerilir)
- `PC_PORT` = `8787`
- `PC_MAC` = PC MAC (WOL için BIOS’ta Wake-on-LAN açık olsun)
- `AUTH_TOKEN` = ESP koruma (PC `api_token` ile aynı olabilir)
- `PC_API_TOKEN` = PC’ye giderken Bearer token

Eski sadece-röle: `jarvis_relay/` (hub yok) — `AUTH_TOKEN` + mDNS `jarvis-relay.local`.

**Port:** ESP HTTP **8788** (Jarvis tarama bunu tercih eder; 80 de taranır).
**mDNS:** `http://jarvis-hub.local:8788` — DHCP IP değişince de bulunur.
Router’da ESP’ye sabit IP vermek hâlâ iyi fikir.

## 2) PC Jarvis

`config.json`:
```json
"host": "0.0.0.0",
"port": 8787,
"api_token": "UZUN-GIZLI-TOKEN",
"pc_mac": "AA:BB:CC:DD:EE:FF",
"esp_hub_url": "http://192.168.1.50:8788",
"esp_mdns_name": "jarvis-hub.local",
"esp_http_port": 8788,
"devices": {
  "isik": { "base_url": "http://192.168.1.50:8788", "aliases": ["ışık", "lamba"], "token": "UZUN-GIZLI-TOKEN" }
}
```

`0.0.0.0` şart — yoksa ESP PC’ye ulaşamaz.

Windows açılışında: `windows_autostart.bat` → `jarvis_watchdog.bat` (çökünce yeniden; `--tray`).

## 3) Komut yollama (ESP üzerinden)

```
GET  http://ESP_IP:8788/api/command?text=isigi%20kapat&token=TOKEN
POST http://ESP_IP:8788/api/command  {"text":"oyun modu"}
     Header: Authorization: Bearer TOKEN
GET  http://ESP_IP:8788/health
GET  http://jarvis-hub.local:8788/health
```

PC açıkken `oyun modu` Jarvis’te çalışır (Valorant + ışık).
PC kapalıyken aynı istek ESP’de ışık/WOL ile sınırlı kalır.

## Güvenlik

- `/health` keşif için açıktır.
- `/relay/*` ve `/api/command` — `AUTH_TOKEN` doluysa token ister.
- Panelden **Üret** veya `POST /api/token/generate` ile PC token oluştur; ESP’ye yaz.
