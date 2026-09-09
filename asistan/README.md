# Windows Jarvis Asistan

Ses algılayan, gerektiğinde kamera/ekran kullanan, izinli sistem işlemleri yapan yerel Windows asistanı.

## Gereksinimler (Windows)

- Python 3.11+
- Mikrofon / kamera için Windows gizlilik izinleri
- PyAudio için: [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) veya önceden derlenmiş tekerlek

## Kurulum

```bat
cd asistan
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.json config.json
```

`config.json` içine isteğe bağlı `openai_api_key` yaz. Anahtar yoksa çevrimdışı kural motoru çalışır.

## Çalıştırma

Kontrol paneli (önerilen):

```bat
python main.py
```

Tarayıcı: `http://127.0.0.1:8787`

Sadece metin CLI:

```bat
python main.py --cli
```

Mikrofon + CLI:

```bat
python main.py --listen
```

## Örnek komutlar

- `not defteri aç`
- `kameradan fotoğraf çek`
- `ekran görüntüsü al`
- `sistem durumu`
- `chrome aç`

## Güvenlik

- Uygulamalar yalnızca `allowed_apps` listesinden açılır
- Riskli kabuk komutları onay ister; tehlikeli kalıplar engellenir
- Asistan **tam yetkili admin** değildir; bilinçli olarak sınırlıdır

## Klasörler

- `core/` — kulak, ağız, beyin, eller, göz, güvenlik
- `ui/` — vanilla kontrol paneli
- `captures/` — kamera/ekran kayıtları
