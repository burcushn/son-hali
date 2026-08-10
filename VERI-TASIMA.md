# Verileri Taşıma / Yedekleme Kılavuzu

Emergent'te (yayında) girdiğiniz **tüm veriler MongoDB veritabanında saklanır**.
Daha sonra kendi PC'nize veya şirket sunucunuza geçtiğinizde bu verileri
kaybetmeden taşıyabilirsiniz. İki yol var:

---

## YOL 1 — Uygulama içinden (en kolay, teknik bilgi gerektirmez)

Sadece **Admin** kullanıcısı yapabilir.

### Yedek alma
1. Uygulamaya admin ile girin.
2. Sol menüden **Kullanıcı Yönetimi** sayfasına gidin.
3. Sağ üstteki **"Yedek İndir (JSON)"** butonuna basın.
4. `ihracat-yedek-YYYYAAGG-SSDD.json` dosyası bilgisayarınıza iner. Bu dosyada
   beyannameler, bedeller, eşleştirmeler, kullanıcılar ve hareket geçmişi bulunur.
5. Bu dosyayı güvenli bir yerde saklayın (şirket ortak klasörü, harici disk).

### Yeni kuruluma geri yükleme
1. PC'ye / sunucuya kurulumu yapın (bkz. `KURULUM-PC.md` veya `KURULUM-SUNUCU.md`).
2. Yeni sistemde admin ile giriş yapın.
3. **Kullanıcı Yönetimi → "Yedekten Geri Yükle"** butonuna basın.
4. İndirdiğiniz JSON dosyasını seçin.
   - **Birleştir (merge)**: mevcut kayıtlar korunur, aynı kayıtlar güncellenir.
   - **Sıfırla ve yükle (replace)**: mevcut tüm veriler silinir, sadece yedek yüklenir.
     (Boş, yeni bir kurulumda bunu seçmek en temizidir.)
5. "Geri yükleme tamamlandı" mesajını gördükten sonra sayfayı yenileyin.

> Not: Şifreler de yedekte şifrelenmiş (hash) olarak taşınır, eski şifrelerinizle
> giriş yapmaya devam edersiniz.

---

## YOL 2 — Sunucu tarafı (mongodump / mongorestore) — IT ekibi için

Tam veritabanı kopyası alır. Docker ile kurulumda:

### Yedek alma
Windows: `yedekle-veritabani.bat`
Linux/Sunucu: `bash yedekle-veritabani.sh`

Bu script `yedekler/` klasörüne `mongo-yedek-YYYYAAGG-SSDD` adlı bir klasör oluşturur.

Manuel komut (Docker):
```bash
docker exec ihracat-mongo mongodump --db=ihracat_db --archive=/tmp/yedek.archive
docker cp ihracat-mongo:/tmp/yedek.archive ./yedekler/yedek.archive
```

Manuel komut (MongoDB doğrudan kurulu ise):
```bash
mongodump --uri="mongodb://localhost:27017" --db=ihracat_db --out=./yedekler/
```

### Geri yükleme
Windows: `geri-yukle-veritabani.bat` (yedek klasörünü/arşivini sorar)
Linux/Sunucu: `bash geri-yukle-veritabani.sh ./yedekler/yedek.archive`

Manuel komut (Docker):
```bash
docker cp ./yedekler/yedek.archive ihracat-mongo:/tmp/yedek.archive
docker exec ihracat-mongo mongorestore --archive=/tmp/yedek.archive --drop
```

Manuel komut (MongoDB doğrudan kurulu ise):
```bash
mongorestore --uri="mongodb://localhost:27017" --drop ./yedekler/ihracat_db
```

`--drop` parametresi aynı isimli koleksiyonları silip yedekten yeniden oluşturur.

---

## Önerilen çalışma düzeni

| Aşama | Yapılacak |
|---|---|
| Emergent'te kullanırken | Haftada bir "Yedek İndir (JSON)" ile yedek alın |
| PC/sunucuya geçerken | Son yedeği alın → yeni kurulumda "replace" ile yükleyin |
| Kendi sunucunuzda | Günlük otomatik `yedekle-veritabani.sh` (cron / Görev Zamanlayıcı) |

Otomatik günlük yedek için Linux cron örneği (her gece 01:00):
```
0 1 * * * cd /opt/ihracat && bash yedekle-veritabani.sh >> yedek.log 2>&1
```

Windows'ta: Görev Zamanlayıcı → Yeni Görev → `yedekle-veritabani.bat` dosyasını
her gün 01:00'de çalıştır.

---

## Veri kaybı olmaması için 3 kural
1. Kuruluma geçmeden **önce** yedeğinizi indirin ve dosyanın boyutunun 0 KB
   olmadığını kontrol edin.
2. Geri yükleme sonrası Dashboard'daki beyanname sayılarının eskisiyle aynı
   olduğunu doğrulayın.
3. Yedek dosyasını en az 2 ayrı yerde saklayın.
