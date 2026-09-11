# Windows Jarvis Asistan

Ses, kamera, bellek ve izinli sistem işlemleri olan yerel Windows asistanı.

## Hızlı başlat (Windows)

`baslat.bat` dosyasına çift tıkla. İlk seferde sanal ortam ve paketler kurulur.

veya:

```bat
cd asistan
baslat.bat
```

Kontrol paneli: `http://127.0.0.1:8787`

## Olmazsa olmaz (yeni)

- **API token:** `config.json` → `api_token` (panelden Üret). ESP `AUTH_TOKEN` / cihaz `token` aynı olsun.
- **Mikrofon mute / PTT:** `mikrofonu kapat`, panel Mute / PTT; konuşurken mic otomatik durur.
- **Yerel STT:** `stt_backend: auto|google|vosk` + `stt_model_path` (Vosk model klasörü).
- **Tray + watchdog:** `python main.py --tray` · açılışta `windows_autostart.bat` → `jarvis_watchdog.bat`.
- **mDNS / IP uyarısı:** ESP `jarvis-hub.local`; status `device_warnings` düşen IP’leri söyler.

## Komut örnekleri

- `bilgisayar aç` (WOL / ESP hub)
- `oyun modu` → ışık kapat + Valorant ekran 2 (PC açıkken)
- `ışığı kapat` / `lambayı aç`
- `çalışma modu` / `uyku modu`
- `cursor aç` / `asistan projesini cursor'da aç`
- `valorantı ekran 2 de aç`
- `google'la araştır python asyncio`

### Akıllı oda — ESP hub + PC + ağ tarama

ESP her zaman açık yönlendirici (`esp32/jarvis_hub/`):
- **PC açıksa** → komut Windows Jarvis’e gider
- **PC kapalıysa** → ESP ışık / WOL yapar

Ağ keşfi:
- `ağı tara` / `esp bul` → LAN’da HTTP/Jarvis ESP ara
- `bulunan cihazları bağla` → ESP’leri `config.json` devices’a yazar
- Panel: **Ağı tara** / **ESP bağla**

PC’de `host: 0.0.0.0`, MAC/`esp_hub_url` ayarla; açılışta `windows_autostart.bat`.
Detay: `esp32/README.md`

### Cursor ve kod (önemli)

- Jarvis Cursor'ı ve kayıtlı projeyi **açabilir**.
- “Site yap” → vanilla HTML/CSS/JS iskeleti yazar.
- “Projeyi düzenle” → `JARVIS_GOREV.md` notu; Agent sohbetini uzaktan tam sürmez.

## Yapılandırma

`config.json` (ilk çalıştırmada örneğinden kopyalanır):

- `openai_api_key` — isteğe bağlı; yoksa çevrimdışı kurallar
- `require_wake_word` — `true` olursa yalnızca "jarvis ..." dinlenir
- `allowed_apps` — açılabilecek uygulamalar
- `blocked_commands` — engelli kabuk kalıpları

## Modlar

```bat
python main.py           rem panel
python main.py --cli     rem metin
python main.py --listen  rem mikrofon + metin
```

## Güvenlik

Tam yönetici yetkisi yok. Uygulamalar listeden, riskli kabuk onaylı, tehlikeli kalıplar engelli.

## Klasörler

- `core/` kulak, ağız, beyin, eller, göz, bellek, güvenlik
- `ui/` kontrol paneli
- `captures/` görüntüler
- `data/` notlar / diyalog hafızası
