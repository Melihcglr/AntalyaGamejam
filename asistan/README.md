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

## Komut örnekleri

- `bilgisayar aç` (WOL / ESP hub)
- `oyun modu` → ışık kapat + Valorant ekran 2 (PC açıkken)
- `ışığı kapat` / `lambayı aç`
- `çalışma modu` / `uyku modu`
- `cursor aç` / `asistan projesini cursor'da aç`
- `valorantı ekran 2 de aç`
- `google'la araştır python asyncio`

### Akıllı oda — ESP hub + PC

ESP her zaman açık yönlendirici (`esp32/jarvis_hub/`):
- **PC açıksa** → komut Windows Jarvis’e gider
- **PC kapalıysa** → ESP ışık / WOL yapar

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
