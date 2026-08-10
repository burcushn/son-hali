# Şirket Sunucusuna Kurulum — BT Sorumlusu İçin

**Uygulama:** İhracat Bedeli Kapatma ve Banka Bildirim Yönetim Sistemi
**Mimari:** React (statik build) + FastAPI (Python 3.11) + MongoDB 7 + Nginx reverse proxy
**Kullanıcı sayısı:** 4-6 kişi (iç ağ). Kaynak ihtiyacı: 2 vCPU, 4 GB RAM, 20 GB disk yeterli.

---

## Seçenek A — Docker ile kurulum (ÖNERİLEN, 10 dakika)

Gereksinim: sunucuda **Docker** + **Docker Compose v2** (Windows Server için Docker Desktop / WSL2, Linux için docker-ce).

1. Proje klasörünü sunucuya kopyalayın (ZIP'i çıkarın), örn. `C:\apps\ihracat-bedeli` veya `/opt/ihracat-bedeli`.

2. `backend/.env` dosyasını düzenleyin:
   ```
   DB_NAME="ihracat_bedeli"
   CORS_ORIGINS="http://SUNUCU_IP:8080"
   JWT_SECRET="<openssl rand -hex 32 çıktısı>"
   ADMIN_EMAIL="admin@firmaniz.com"
   ADMIN_PASSWORD="<güçlü şifre>"
   EMERGENT_EMAIL_KEY=""          # kurumsal SMTP/Resend eklenecekse doldurulur
   EMAIL_FROM_NAME="Firma Adı - İhracat Bedeli Takip"
   ALERT_EMAILS="uyari@firmaniz.com"
   SEED_DEMO_USERS="false"
   DEFAULT_ACH_IBAN="TR.. şirket TL IBAN .."
   AUDIT_RETENTION_DAYS="30"
   ```
   > `MONGO_URL` compose tarafından otomatik verilir (`mongodb://mongo:27017`), .env'de olsa da ezilir.

3. Proje kökünde `.env` dosyası oluşturun (frontend build'i için):
   ```
   PUBLIC_URL=http://SUNUCU_IP:8080
   ```
   Alan adı kullanılacaksa: `PUBLIC_URL=https://ihracat.firmaniz.com`

4. Başlatın:
   ```
   docker compose up -d --build
   ```

5. Erişim: `http://SUNUCU_IP:8080` — admin bilgileriyle giriş yapın.

6. Güncelleme (yeni sürüm geldiğinde):
   ```
   docker compose down
   docker compose up -d --build
   ```
   Veriler `mongo_data` adlı Docker volume'unda kalır, silinmez.

### Port / güvenlik
- Dışarıya açılan tek port: **8080** (Nginx). MongoDB ve backend dışarıya kapalıdır.
- İnternete açılacaksa mutlaka HTTPS: kurumsal reverse proxy (IIS/Nginx/Traefik) arkasına alın veya Let's Encrypt sertifikası tanımlayın. Aksi halde yalnızca iç ağda/VPN üzerinden yayınlayın.
- Giden internet erişimi gereken adresler: `www.tcmb.gov.tr` (günlük kur), e-posta sağlayıcısı (SMTP/Resend).

---

## Seçenek B — Docker olmadan (mevcut sunucuya elle kurulum)

1. **MongoDB 7** kurun, servis olarak çalıştırın (`mongodb://localhost:27017`).
2. **Python 3.11** kurun:
   ```
   cd backend
   python -m venv .venv && .venv\Scripts\activate     (Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
   Servis olarak çalıştırın (Windows: NSSM ile "IhracatBedeliAPI" servisi / Linux: systemd unit):
   ```
   uvicorn server:app --host 0.0.0.0 --port 8001
   ```
3. **Node 20** kurun, arayüzü derleyin:
   ```
   cd frontend
   # .env: REACT_APP_BACKEND_URL=http://SUNUCU_IP:8080
   yarn install && yarn build
   ```
   Oluşan `frontend/build` klasörünü IIS veya Nginx ile yayınlayın.
4. Reverse proxy kuralları (IIS: URL Rewrite / ARR, Nginx: `nginx.conf` dosyasını kullanın):
   - `/api/*` → `http://localhost:8001`
   - diğer tüm yollar → statik `build` klasörü (SPA fallback: `index.html`)

---

## Yedekleme (zorunlu)
Günlük yedek görevi tanımlayın:

Docker kurulumunda:
```
docker exec ihracat_mongo mongodump --db=ihracat_bedeli --archive=/tmp/y.gz --gzip
docker cp ihracat_mongo:/tmp/y.gz  D:\yedek\ihracat_%DATE%.gz
```
Elle kurulumda:
```
mongodump --db=ihracat_bedeli --archive=D:\yedek\ihracat_%DATE%.gz --gzip
```
Geri yükleme: `mongorestore --gzip --archive=<dosya>`

Yedekleri kurumsal yedek politikanıza dahil edin (en az 7 günlük saklama önerilir).

---

## Zamanlanmış görevler (uygulama içinde, APScheduler)
- **Pazartesi 09:00** — haftalık uyarı e-postası (süresi yaklaşan/geçen, IBKB düzenlenmemiş, destek alınmamış beyannameler)
- **Her gün 03:30** — 30 günden eski hareket kayıtlarının otomatik temizliği
Saat dilimi: `Europe/Istanbul`. Bu görevler backend süreci ayakta olduğu sürece çalışır.

---

## Sağlık kontrolü
```
curl http://SUNUCU_IP:8080/api/auth/me      -> 401 dönmesi normaldir (servis ayakta demektir)
docker compose ps                           -> tüm servisler "running"
docker compose logs -f backend              -> hata takibi
```
