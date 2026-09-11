# Jarvis — Bu PC’de kurulum ve komutlar

Bu dosya, repodaki `asistan/` kodunu Windows PC’de çalıştırmak içindir.

## 0) Önkoşullar

1. **Python 3.11+** (PATH’e ekli olsun)  
   https://www.python.org/downloads/  
   Kurulumda “Add python.exe to PATH” işaretle.
2. **Mikrofon / hoparlör** Windows ayarlarında çalışır durumda.
3. (Opsiyonel) **Cursor CLI** PATH’te: `cursor`
4. (Opsiyonel) ESP32 hub aynı Wi‑Fi’de.

---

## 1) Kodu PC’ye al

PowerShell veya CMD:

```bat
git clone https://github.com/Melihcglr/AntalyaGamejam.git
cd AntalyaGamejam
git checkout cursor/windows-jarvis-asistan-bd5e
cd asistan
```

Zaten klonladıysan:

```bat
cd AntalyaGamejam
git fetch origin
git checkout cursor/windows-jarvis-asistan-bd5e
git pull origin cursor/windows-jarvis-asistan-bd5e
cd asistan
```

---

## 2) İlk kurulum (tek tık)

```bat
baslat.bat
```

Bu şunları yapar:
- `.venv` oluşturur
- `pip install -r requirements.txt`
- `config.example.json` → `config.json` kopyalar
- paneli açar: http://127.0.0.1:8787

PyAudio hata verirse (sık olur):

```bat
call .venv\Scripts\activate.bat
pip install pipwin
pipwin install pyaudio
```

veya:

```bat
pip install PyAudio
```

Hâlâ olmazsa: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio  
uygun `.whl` indir → `pip install dosya_adi.whl`

---

## 3) `config.json` mutlaka düzenle

`asistan\config.json` aç:

```json
{
  "host": "0.0.0.0",
  "port": 8787,
  "api_token": "",
  "openai_api_key": "",
  "pc_mac": "AA:BB:CC:DD:EE:FF",
  "esp_hub_url": "http://192.168.1.50:8788",
  "esp_mdns_name": "jarvis-hub.local",
  "require_wake_word": true,
  "wake_word": "jarvis",
  "stt_backend": "auto",
  "stt_model_path": "",
  "push_to_talk": false
}
```

| Alan | Ne yazacaksın |
|------|----------------|
| `pc_mac` | PC Ethernet/Wi‑Fi MAC (WOL için). `ipconfig /all` → Physical Address |
| `esp_hub_url` | ESP IP:8788 (yoksa boş bırak) |
| `openai_api_key` | İsteğe bağlı; boşsa offline kurallar |
| `api_token` | LAN güvenliği — panelden **Üret** veya elle yaz |
| `allowed_apps.valorant.path` | Riot Client gerçek yolu |

ESP kullanıyorsan cihaz token’ı aynı olsun:

```json
"devices": {
  "isik": {
    "base_url": "http://ESP_IP:8788",
    "token": "AYNI_API_TOKEN"
  }
}
```

---

## 4) Çalıştırma komutları

### Panel (normal)

```bat
cd asistan
baslat.bat
```

Tarayıcı: http://127.0.0.1:8787  
ESP’nin ulaşması için: http://PC_IP:8787

### Metin CLI

```bat
call .venv\Scripts\activate.bat
python main.py --cli
```

### Mikrofon + metin

```bat
python main.py --listen
```

### Tray (sistem tepsisi)

```bat
python main.py --host 0.0.0.0 --port 8787 --tray
```

### Watchdog (çökünce yeniden)

```bat
jarvis_watchdog.bat
```

---

## 5) Windows açılışında otomatik başlat

1. `Win + R` → `shell:startup`
2. `windows_autostart.bat` için kısayol oluştur  
   **veya** Görev Zamanlayıcı’da “oturum açılınca” → `windows_autostart.bat`

Bu dosya `jarvis_watchdog.bat`’i başlatır (tray + yeniden ayağa kalkma).

---

## 6) Panelden ilk ayarlar

1. http://127.0.0.1:8787 aç
2. **API token → Üret → Kaydet** (tarayıcıda saklanır)
3. **Dinlemeyi aç**
4. İstersen **Wake: zorunlu**
5. ESP varsa: **Ağı tara** → **ESP bağla**

---

## 7) Sesli / yazılı deneme komutları

```
jarvis saat kaç
jarvis not al süt al
jarvis notlarımı göster
jarvis ışığı kapat
jarvis oyun modu
jarvis ağı tara
jarvis bulunan cihazları bağla
jarvis mikrofonu kapat
jarvis mikrofonu aç
jarvis ptt aç
```

---

## 8) (Opsiyonel) Yerel STT — Vosk

İnternetsiz tanıma için:

1. Türkçe Vosk modeli indir (ör. `vosk-model-small-tr-0.3`)
2. Klasöre çıkar, örn. `C:\vosk\vosk-model-small-tr-0.3`
3. Kurulu ortama:

```bat
call .venv\Scripts\activate.bat
pip install vosk
```

4. `config.json`:

```json
"stt_backend": "vosk",
"stt_model_path": "C:\\vosk\\vosk-model-small-tr-0.3"
```

---

## 9) ESP32 (opsiyonel ama oda için)

1. Arduino IDE / PlatformIO ile `esp32/jarvis_hub/jarvis_hub.ino` yükle
2. Firmware’de doldur:
   - `WIFI_SSID` / `WIFI_PASS`
   - `PC_HOST` = PC’nin yerel IP’si
   - `PC_PORT` = `8787`
   - `PC_MAC` = PC MAC
   - `AUTH_TOKEN` = PC `api_token`
   - `PC_API_TOKEN` = aynı token
3. Seri monitörden ESP IP’yi gör → `config.json` `esp_hub_url`
4. Router’da ESP’ye sabit IP ver
5. BIOS’ta Wake-on-LAN açık olsun

Detay: `esp32/README.md`

---

## 10) Sık hatalar

| Sorun | Çözüm |
|-------|--------|
| `Python bulunamadı` | Python kur + PATH + yeni CMD aç |
| PyAudio hatası | `pipwin install pyaudio` veya `.whl` |
| Panel açılmıyor | `8787` dolu mu? `netstat -ano \| findstr 8787` |
| ESP PC’ye ulaşamıyor | `host: 0.0.0.0`, Windows Güvenlik Duvarı 8787 izin |
| 401 Unauthorized | Panel token = `config.json` `api_token` |
| Mikrofon yok | Windows Gizlilik → Mikrofon → uygulama izni |
| Valorant açılmıyor | `allowed_apps.valorant.path` gerçek yol |

Güvenlik duvarı (yönetici CMD):

```bat
netsh advfirewall firewall add rule name="Jarvis 8787" dir=in action=allow protocol=TCP localport=8787
```

---

## 11) Günlük kullanım özeti

```bat
cd AntalyaGamejam\asistan
baslat.bat
```

veya açılışta otomatik: `windows_autostart.bat`  
Panel: http://127.0.0.1:8787  
Ses: “Jarvis …” (wake açıksa)
