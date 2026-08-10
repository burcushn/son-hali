# PC'ye Kurulum — Adım Adım (Windows)

Bu rehber uygulamayı kendi bilgisayarında çalıştırmak içindir. Veriler tamamen bilgisayarında kalır.

---

## ADIM 0 — Kodu bilgisayarına indir
Emergent arayüzünde **Save to GitHub** → GitHub'da repo → **Code → Download ZIP** →
ZIP'i `C:\ihracat-bedeli` gibi bir klasöre çıkar. İçinde `backend` ve `frontend` klasörleri olmalı.

---

## ADIM 1 — Gerekli 3 programı kur (tek seferlik)

1. **Python 3.11+** → https://www.python.org/downloads/
   Kurulumda **"Add Python to PATH"** kutusunu MUTLAKA işaretle.
2. **Node.js 18+ (LTS)** → https://nodejs.org
3. **MongoDB Community Server** → https://www.mongodb.com/try/download/community
   Kurulumda "Install MongoDB as a Service" seçili kalsın (Windows açılışında kendi başlar).

Kurulumları doğrula — **Başlat → cmd** yazıp Komut İstemi'ni aç ve şunları çalıştır:
```
python --version
node --version
```
İkisi de sürüm yazdırıyorsa tamam.

Yarn'ı kur (bir kez):
```
npm install -g yarn
```

---

## ADIM 2 — Ayar dosyalarını düzenle

`backend\.env` dosyasını Not Defteri ile aç, şu hale getir (kendi bilgilerinle):
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="ihracat_bedeli"
CORS_ORIGINS="http://localhost:3000"
JWT_SECRET="buraya-uzun-rastgele-bir-metin-yaz-1234567890abcdef"
ADMIN_EMAIL="kendi@firmaniz.com"
ADMIN_PASSWORD="GucluBirSifre!2026"
EMERGENT_EMAIL_KEY=""
EMAIL_FROM_NAME="Kalıpsan Alüminyum - İhracat Bedeli Takip"
ALERT_EMAILS="burcusahin@kalipsanaluminyum.com"
SEED_DEMO_USERS="false"
DEFAULT_ACH_IBAN="TR.. kendi TL IBAN'ınız .."
AUDIT_RETENTION_DAYS="30"
```

`frontend\.env` dosyası:
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

> `SEED_DEMO_USERS="false"` → demo hesaplar oluşmaz, sadece `ADMIN_EMAIL` hesabı açılır.
> `EMERGENT_EMAIL_KEY` boş kalırsa e-posta gönderilmez (2FA ve haftalık uyarı çalışmaz).

---

## ADIM 3 — İlk kurulum (tek seferlik)

Proje klasöründe `kurulum.bat` dosyasına **çift tıkla**. Bittiğinde pencereyi kapat.

Elle yapmak istersen:
```
cd C:\ihracat-bedeli\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd ..\frontend
yarn install
```

---

## ADIM 4 — Uygulamayı çalıştır (her açılışta)

1. `baslat-backend.bat` → çift tıkla (pencereyi KAPATMA)
2. `baslat-frontend.bat` → çift tıkla (pencereyi KAPATMA)
3. Tarayıcı kendiliğinden açılır: **http://localhost:3000**
   Açılmazsa adresi elle yaz.

Giriş: `.env` içine yazdığın `ADMIN_EMAIL` ve `ADMIN_PASSWORD`.

Kapatmak için iki siyah pencereyi kapatman yeterli.

---

## ADIM 5 — Kullanıcıları oluştur
Admin ile gir → **Kullanıcı Yönetimi** → ihracat personeli, banka personeli, şef ve
görüntüleyici hesaplarını ekle. (Yerel kurulumda e-posta gitmediği için 2FA'yı kapalı bırak.)

---

## YEDEKLEME (önemli)
Veriler bilgisayarındaki MongoDB'de. Haftada bir yedek al:
```
"C:\Program Files\MongoDB\Tools\100\bin\mongodump.exe" --db=ihracat_bedeli --out=D:\yedek\%date%
```
Bu klasörü harici disk veya kuruma ait bulut alanına kopyala. Bilgisayar bozulursa
veriler yalnızca bu yedekten döner.

Geri yükleme:
```
"C:\Program Files\MongoDB\Tools\100\bin\mongorestore.exe" D:\yedek\<tarih>
```

---

## SIK KARŞILAŞILAN SORUNLAR

| Sorun | Çözüm |
|---|---|
| `python` komutu bulunamadı | Python'u "Add to PATH" işaretli şekilde tekrar kur |
| Sayfa açılıyor ama veri gelmiyor | `baslat-backend.bat` penceresi açık mı? `frontend\.env` içindeki adres `http://localhost:8001` mi? |
| MongoDB bağlantı hatası | Başlat → "Hizmetler" → **MongoDB Server** durumu "Çalışıyor" olmalı |
| Kur alınamadı uyarısı | TCMB kuru internetten çekilir; internet bağlantısını kontrol et veya kuru elle gir |
| 2FA kodu gelmiyor | Yerel kurulumda e-posta kapalı; Kullanıcı Yönetimi'nden ilgili kullanıcının 2FA'sını kapat |
| Port 3000/8001 kullanımda | Diğer programı kapat veya bilgisayarı yeniden başlat |

---

## Ağdaki diğer bilgisayarlardan erişim (opsiyonel)
Uygulama bir bilgisayarda çalışırken ekip aynı ofis ağından girebilir:
1. Sunucu bilgisayarın IP'sini öğren: `ipconfig` → örn. `192.168.1.50`
2. `frontend\.env` → `REACT_APP_BACKEND_URL=http://192.168.1.50:8001`
3. `backend\.env` → `CORS_ORIGINS="http://192.168.1.50:3000"`
4. Windows Güvenlik Duvarı'nda 3000 ve 8001 portlarına gelen bağlantıya izin ver
5. Diğer bilgisayarlar: `http://192.168.1.50:3000`

> Sunucu bilgisayar kapalıyken kimse giremez.
