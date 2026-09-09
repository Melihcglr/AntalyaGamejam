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

Eski sadece-röle: `jarvis_relay/` (hub yok).

**Port:** ESP HTTP **8788** (Jarvis tarama bunu tercih eder; 80 de taranır).
Router’da ESP’ye sabit IP ver.

## 2) PC Jarvis

`config.json`:
```json
"host": "0.0.0.0",
"port": 8787,
"pc_mac": "AA:BB:CC:DD:EE:FF",
"esp_hub_url": "http://ESP_IP:8788",
"devices": {
  "isik": { "base_url": "http://ESP_IP:8788", "aliases": ["ışık", "lamba"] }
}
```

`0.0.0.0` şart — yoksa ESP PC’ye ulaşamaz.

Windows açılışında otomatik: `asistan/windows_autostart.bat` dosyasını Görev Zamanlayıcı’ya veya Startup klasörüne ekle.

## 3) Komut yollama (ESP üzerinden)

```
GET  http://ESP_IP:8788/api/command?text=isigi%20kapat
POST http://ESP_IP:8788/api/command  {"text":"oyun modu"}
GET  http://ESP_IP:8788/health
```

PC açıkken `oyun modu` Jarvis’te çalışır (Valorant + ışık).
PC kapalıyken aynı istek ESP’de ışık/WOL ile sınırlı kalır.

## Güvenlik notu

Hub şu an LAN içi açık HTTP. İleride token / sadece yerel subnet eklenebilir.
