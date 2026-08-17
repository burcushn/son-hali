# E-posta Ayarları (2FA kodu + haftalık uyarı)

Sistem 2 şekilde e-posta gönderebilir. Hangisi tanımlıysa onu kullanır.

---

## 1) Emergent e-posta servisi (varsayılan — Emergent'te yayındaysanız)

`backend/.env` içinde şu iki satır yeter:

```
EMERGENT_EMAIL_KEY=ek_xxxxxxxxxxxxxxxx
EMAIL_FROM_NAME="İhracat Bedeli Takip"
ALERT_EMAILS="burcusahin@kalipsanaluminyum.com"
```

`ALERT_EMAILS` birden fazla olabilir: virgülle ayırın.
Bu yöntem **yalnızca Emergent üzerinde** çalışır.

---

## 2) Kurumsal SMTP (kendi PC'nizde / şirket sunucusunda)

`backend/.env` dosyasına aşağıdaki satırları ekleyin. **`SMTP_HOST` ve `SMTP_FROM`
dolu olduğu anda sistem otomatik olarak SMTP'ye geçer**, Emergent servisini kullanmaz.

```
SMTP_HOST=mail.kalipsanaluminyum.com
SMTP_PORT=587
SMTP_USER=bildirim@kalipsanaluminyum.com
SMTP_PASSWORD=uygulama-sifresi
SMTP_FROM=bildirim@kalipsanaluminyum.com
SMTP_SSL=false
SMTP_TIMEOUT_SECONDS=20
EMAIL_FROM_NAME="İhracat Bedeli Takip"
ALERT_EMAILS="burcusahin@kalipsanaluminyum.com"
```

Port kuralı (IT ekibinize sorulacak tek şey bu):
- **587** → `SMTP_SSL=false` (STARTTLS, en yaygın)
- **465** → `SMTP_SSL=true`
- **25** → şirket içi röle; kullanıcı/şifre genelde gerekmez (boş bırakın)

Office 365 için: `SMTP_HOST=smtp.office365.com`, port `587`, `SMTP_SSL=false`
Google Workspace için: `SMTP_HOST=smtp.gmail.com`, port `587`, şifre olarak
**uygulama şifresi** (normal hesap şifresi çalışmaz).

`.env` değiştirdikten sonra backend'i yeniden başlatın
(`baslat-backend.bat` penceresini kapatıp yeniden açın; Docker'da
`docker compose restart backend`).

---

## Test etme

Uygulamada **Raporlar** ekranındaki **"Uyarı E-postası Gönder"** butonuna basın.
- Başarılıysa: "E-posta gönderildi" bildirimi çıkar ve adres(ler)e ulaşır.
- Başarısızsa: hata mesajı çıkar. Sunucu tarafında sebep loglanır
  (`baslat-backend.bat` penceresinde ya da `docker compose logs backend`).

## Giriş doğrulama kodu (2FA)

Kullanıcı Yönetimi'nde bir kullanıcının "Girişte e-posta doğrulama kodu istensin"
kutusu işaretliyse, o kullanıcı girişte e-postasına gelen 6 haneli kodu girer.

Güvenlik ağı: e-posta gönderilemezse kullanıcı **kilitlenmez**, doğrulama adımı
atlanır ve bu durum Hareket Geçmişi'ne "2FA_ATLANDI" olarak kaydedilir.
Bu davranışı kapatmak isterseniz `backend/.env` içine
`TWO_FACTOR_FALLBACK=false` ekleyin (o zaman e-posta çalışmazsa 2FA'lı kullanıcı
giriş yapamaz).

## Haftalık otomatik uyarı

Her Pazartesi 09:00'da `ALERT_EMAILS` adreslerine özet gider:
süresi geçmiş / yaklaşan beyannameler, IBKB düzenlenmemişler ve destek alınmamışlar.
