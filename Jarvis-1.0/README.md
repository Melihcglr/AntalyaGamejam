# Jarvis 1.0

Yerel Windows asistanı — **buluta bağlı değil**. Masaüstünde kendi klasöründe çalışır.

## Masaüstüne yedekle (önerilen)

1. Bu paketi bilgisayarına indir / kopyala
2. `YEDEKLE_MASAUSTU.bat` çift tıkla  
   → `%USERPROFILE%\Desktop\Jarvis 1.0` oluşur  
   → yerel `git` deposu açılır (uzak sunucu yok)  
   → bağımlılıklar kurulur, Jarvis başlar
3. Panel: http://127.0.0.1:8787

## Sadece başlat

Zaten `Desktop\Jarvis 1.0` içindeysen: `BASLAT.bat`

## Gereksinimler

- Windows 10/11
- Python 3.11+ (PATH’te)
- Git (masaüstü yedek / yerel repo için)

## Config

İlk çalıştırmada `config.example.json` → `config.json`.  
Düzenle: `pc_mac`, `esp_hub_url`, `api_token`, uygulama yolları.

## İçerik

Ses, panel, notlar, sahneler, ESP32 hub, ağ tarama, API token, mic mute/PTT, tray, watchdog.
