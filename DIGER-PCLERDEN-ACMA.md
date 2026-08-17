# Diğer Bilgisayarlardan Açma (Ofis Ağı)

Uygulama **tek bir bilgisayarda** çalışır; diğer bilgisayarlar tarayıcıdan o
bilgisayara bağlanır. Yani sadece 1 kurulum yeter, herkes aynı verileri görür.

- Uygulamanın kurulu olduğu bilgisayara **"ana bilgisayar"** diyeceğiz (sizin PC'niz).
- Diğerleri (**istemci**) hiçbir kurulum yapmaz, sadece adrese girer.

---

## 1. ADIM — Ana bilgisayarda (tek seferlik, 2 dakika)

Proje klasöründeki **`ag-erisimi-ayarla.bat`** dosyasına **sağ tık → Yönetici olarak
çalıştır**. Script şunları kendisi yapar:

1. Bilgisayarın ağ IP adresini bulur (örn. `192.168.1.50`) ve onaylatır.
2. `frontend\.env` ve `backend\.env` dosyalarını bu IP ile günceller.
3. Windows Güvenlik Duvarı'nda **3000** ve **8001** portlarını açar.

Sonra `baslat-backend.bat` ve `baslat-frontend.bat` pencerelerini **kapatıp yeniden
açın** (yeni ayarların yüklenmesi için).

> Elle yapmak isterseniz: `ipconfig` → IPv4 adresini alın →
> `frontend\.env` → `REACT_APP_BACKEND_URL=http://192.168.1.50:8001`
> `backend\.env` → `CORS_ORIGINS="http://192.168.1.50:3000,http://localhost:3000"`

---

## 2. ADIM — Diğer bilgisayarlarda

Tarayıcıya (Chrome/Edge) şunu yazın:

```
http://192.168.1.50:3000
```

(`192.168.1.50` yerine script'in size gösterdiği IP.)

Kalıcı ve logolu simge için o bilgisayarda **`masaustu-kisayol.bat`** çalıştırıp bu
adresi girin — ya da Chrome'da **⋮ → Yayınla → Uygulama olarak yükle**.

Her kullanıcıya **kendi hesabını** verin (Kullanıcı Yönetimi ekranından, uygun rolle).
Aynı hesabı paylaşmayın; Hareket Geçmişi'nde kim ne yaptı görünsün.

---

## Önemli 3 kural

1. **Ana bilgisayar açık olmalı.** Kapalıysa/uykudaysa kimse giremez.
   Uyku moduna geçmemesi için: Ayarlar → Sistem → Güç → Uyku: **Asla**.
2. **Aynı ofis ağında olmalısınız.** Evden veya şubeden erişim gerekiyorsa
   IT ekibinizden VPN isteyin ya da uygulamayı şirket sunucusuna kurdurun
   (`KURULUM-SUNUCU.md`).
3. **Yedek alın.** Tüm veri ana bilgisayarda durur:
   `yedekle-veritabani.bat` veya uygulama içinden "Yedek İndir (JSON)"
   (bkz. `VERI-TASIMA.md`).

---

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Diğer PC'de sayfa açılmıyor | Ana bilgisayarda `baslat-frontend.bat` açık mı? `ag-erisimi-ayarla.bat`'ı Yönetici olarak çalıştırdınız mı? |
| Sayfa açılıyor ama "giriş yapılamadı" / veriler boş | `frontend\.env` içindeki adres `localhost` kalmış olabilir; IP olmalı. Değiştirip servisleri yeniden başlatın |
| IP adresi değişti, artık girilemiyor | Modem IP'yi değiştirmiş olabilir. `ag-erisimi-ayarla.bat`'ı tekrar çalıştırın (veya IT'den sabit IP isteyin) |
| Güvenlik duvarı uyarısı çıktı | "Erişime izin ver" seçin (Özel ağ) |
| Çok kullanıcı olacak, sürekli açık kalsın | Kişisel PC yerine şirket sunucusuna kurulum daha doğru: `KURULUM-SUNUCU.md` (Docker) |
