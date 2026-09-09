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

- `oyun modu` → ışık kapat + Valorant ekran 2 (sahne)
- `ışığı kapat` / `lambayı aç`
- `çalışma modu` / `uyku modu`
- `cursor aç` / `asistan projesini cursor'da aç`
- `bana konya restoran sitesi yap`
- `valorantı ekran 2 de aç`
- `google'la araştır python asyncio`

### Akıllı oda (ESP32)

- `config.json` → `devices` (ESP32 IP) ve `scenes` (oyun/çalışma…)
- Örnek firmware: `esp32/jarvis_relay/`
- Dinlemeyi açınca komutlar sürekli dinlenir (`Dinlemeyi aç` / `python main.py --listen`)

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
