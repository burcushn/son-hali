# İhracat Bedeli Kapatma ve Banka Bildirim Yönetim Sistemi

Dış ticaret operasyonu için beyanname–banka bedeli eşleştirme, IBKB takibi ve banka bildirim Excel'i üreten yönetim sistemi.

## Teknoloji
- Backend: FastAPI (Python 3.11+), MongoDB (motor), JWT + 2FA, TCMB kur servisi, openpyxl
- Frontend: React (CRA), Tailwind, shadcn/ui
- Zamanlanmış görev: APScheduler (haftalık uyarı e-postası, Pazartesi 09:00)

## Bilgisayarda Kurulum

### 1. Gereksinimler
- Python 3.11+
- Node.js 18+ ve **yarn** (`npm install -g yarn`)
- MongoDB Community Edition (yerelde çalışır durumda)

### 2. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

`backend/.env` dosyası (örnek):
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="ihracat_bedeli"
CORS_ORIGINS="http://localhost:3000"
JWT_SECRET="uzun-rastgele-bir-anahtar"
ADMIN_EMAIL="admin@firmaniz.com"
ADMIN_PASSWORD="GucluBirSifre!"
EMERGENT_EMAIL_KEY=""
EMAIL_FROM_NAME="Firma Adı - İhracat Bedeli Takip"
ALERT_EMAILS="uyari-alacak-adres@firmaniz.com"
SEED_DEMO_USERS="false"
DEFAULT_ACH_IBAN="TR00 0000 0000 0000 0000 0000 00"
AUDIT_RETENTION_DAYS="30"
```

> `AUDIT_RETENTION_DAYS`: hareket geçmişi kaç gün saklanacak (varsayılan 30). Her gün 03:30'da bu süreden eski kayıtlar otomatik silinir; admin ekrandan manuel de temizleyebilir.
```

> `DEFAULT_ACH_IBAN`: bozdurulan TL'nin yattığı sabit TL IBAN. Excel'in "KULLANILACAK ACH" kolonu bu değerden gelir; kayıt bazında IBKB ekranından değiştirilebilir. Ödemenin geldiği döviz IBAN'ı (KULLANILACAK DTH) ise bedel girişi ekranında yazılır.

### Gerçek (canlı) kullanım için önemli notlar
- `DB_NAME` değerini kendi veritabanı adınızla değiştirin (örn. `ihracat_bedeli`). Böylece test verileriyle karışmaz.
- `SEED_DEMO_USERS="false"` yaparsanız demo hesaplar (ihracat@/banka@/sef@/viewer@ihracat.com) **hiç oluşturulmaz**; sadece `ADMIN_EMAIL` ile admin hesabı açılır, diğer kullanıcıları Kullanıcı Yönetimi ekranından kendiniz eklersiniz.
- `ADMIN_EMAIL` ve `ADMIN_PASSWORD`'ü kendi kurumsal bilgilerinizle değiştirin; şifreyi ilk girişten sonra da güncelleyebilirsiniz.
- `JWT_SECRET`'i mutlaka uzun ve rastgele bir değerle değiştirin.
- Örnek/deneme kayıtlarını silmek isterseniz: mongo shell'de `db.declarations.deleteMany({}); db.payments.deleteMany({}); db.matches.deleteMany({}); db.audit_logs.deleteMany({})`
> Not: E-posta gönderimi (2FA kodu + haftalık uyarı) Emergent'in yönettiği e-posta servisiyle çalışır. Yerel kurulumda `EMERGENT_EMAIL_KEY` boşsa e-posta gitmez; 2FA kodu backend logunda görünür. Kendi kurumsal e-postanızı bağlamak isterseniz SMTP/Resend entegrasyonu eklenebilir.

### 3. Frontend
```bash
cd frontend
yarn install
yarn start
```

`frontend/.env`:
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 4. İlk giriş
Backend ilk açılışta `ADMIN_EMAIL` / `ADMIN_PASSWORD` ile admin hesabını oluşturur.
Tarayıcı: http://localhost:3000

## Roller
| Yetki | Admin | İhracat | Banka | Onaylayan | Görüntüleyici |
|---|---|---|---|---|---|
| Tüm ekranları görüntüleme, rapor, Excel | ✔ | ✔ | ✔ | ✔ | ✔ |
| Beyanname ekle/düzenle/sil | ✔ | ✔ | – | – | – |
| Bedel ekle/düzenle/sil | ✔ | – | ✔ | – | – |
| IBKB bilgileri (dosya ref., DTH/ACH, TCMB oranı) | ✔ | – | ✔ | – | – |
| Eşleştirme yap / düzelt / geri al | ✔ | – | – | ✔ | – |
| Kullanıcı yönetimi | ✔ | – | – | – | – |

## İş akışı
1. İhracat personeli beyannameyi girer (beyanname no, açılış/kapanış tarihi, ithalatçı, gümrük müdürlüğü no, tutar, döviz, teşvik/taahhüt).
2. Banka personeli gelen bedeli girer; IBKB düzenlendikten sonra IBKB ekranından dosya referansı, DTH/ACH ve TCMB devir oranını (%100) girer.
3. Onaylayan (şef) beyannameye bedel bağlar. Aynı dövizde kur kullanılmaz; farklı dövizde TCMB kuru beyanname açılış tarihinden otomatik alınır.
4. Süre: beyanname kapanış tarihi + 180 gün. Süresi yaklaşan/geçen kayıtlar dashboard'da ve haftalık e-posta uyarısında listelenir.
5. "Excel Aktar" ile bankanın istediği **BANKA BİLDİRİMİ** sayfası (SIRA NO, DOSYA REFERANSI, GÜMRÜK MÜDÜRLÜĞÜ KODU, GB NO, GB TARİHİ, GB'YE SAYILACAK TUTAR, KULLANILACAK DTH, KULLANILACAK ACH, TCMB DEVİR ORANI, TEŞVİK, TAAHHÜT + TOPLAM) üretilir.

## Testler
```bash
cd backend
python -m pytest tests/backend_test.py -q
```
