# Proje 0 — Jarvis

Bu klasör, Jarvis asistanının **tek başına çalışan** kopyasıdır.
Unity `KediGozu` oyunundan ayrıdır.

## Windows PC’de başlat

1. Python 3.11+ kur → **Add to PATH**
2. Bu klasörde `BASLAT.bat` çift tıkla
3. Panel: http://127.0.0.1:8787

Masaüstüne sıfırdan kurmak için repo kökündeki:
`proje-0-jarvis\MASAUSTUNE_KUR.bat`

## Ne içerir

- Ses / panel / notlar / sahneler
- ESP32 hub + ağ tarama
- API token, mic mute/PTT, tray, watchdog
- `KURULUM_PC.md` detaylı rehber

## Config

İlk çalıştırmada `config.example.json` → `config.json` kopyalanır.
Düzenle: `pc_mac`, `esp_hub_url`, `api_token`, uygulama yolları.
