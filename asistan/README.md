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

- `cursor aç` / `asistan projesini cursor'da aç`
- `bana konya restoran sitesi yap` / `şu tarz bir internet sitesi yap: ortalik`
- `projeye şunu ekle: hakkımızda sayfası`
- `valorantı ekran 2 de aç` / `valo monitör 2 başlat`
- `google'la araştır python asyncio`
- `bana konya restoranları araştır`
- `jarvis saat kaç`
- `not defteri aç` / `spotify aç`
- `sistem durumu` / `çalışan programlar`

### Cursor ve kod (önemli)

- Jarvis Cursor'ı ve kayıtlı projeyi **açabilir**.
- “Site yap” → vanilla HTML/CSS/JS iskeleti `workspace_root/sites/` altına yazar, Cursor'da açar.
- “Projeyi düzenle / şunu ekle” → `JARVIS_GOREV.md` yazar ve projeyi açar; Cursor Agent sohbetini uzaktan tam süremez, görev dosyasını Agent'a sen verirsin.
- Projeleri `config.json` → `projects` map'ine ekle.

Valorant yolu `config.json` → `allowed_apps.valorant` içinde.

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
