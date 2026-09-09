# ESP32 röle → Jarvis

1. Arduino IDE veya PlatformIO ile `jarvis_relay.ino` yükle.
2. `WIFI_SSID` / `WIFI_PASS` doldur.
3. Seri monitörden IP’yi oku (örn. `192.168.1.50`).
4. `asistan/config.json` içinde:

```json
"devices": {
  "isik": {
    "name": "Oda ışığı",
    "aliases": ["ışık", "lamba"],
    "base_url": "http://192.168.1.50"
  }
}
```

5. Sesli: `ışığı kapat` / `oyun modu`

Röle pinini ve ACTIVE_LOW ayarını kartına göre değiştir.
