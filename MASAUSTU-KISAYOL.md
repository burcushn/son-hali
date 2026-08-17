# Masaüstünde Logolu Simge ile Açma

Uygulamayı tarayıcıdan adres yazarak değil, **masaüstündeki Kalıpsan logolu simgeye
çift tıklayarak** açmak için 2 yol var. İkisi de çalışır, 1. yol daha kolay.

---

## YOL 1 — Tarayıcıdan "Uygulama olarak yükle" (en kolay, 20 saniye)

Chrome veya Edge ile uygulamayı açın (yayın adresi veya `http://localhost:3000`), sonra:

**Chrome:**
1. Adres çubuğunun sağındaki **monitör/indirme simgesi** (⊕ "Yükle") → yoksa
   sağ üst **⋮** → **Yayınla / Kaydet ve paylaş → Kısayol oluştur…**
   (yeni sürümlerde: **⋮ → Yayınla → Uygulama olarak yükle**)
2. **"Pencere olarak aç"** kutusunu işaretleyin → **Yükle**.

**Edge:**
1. Sağ üst **…** → **Uygulamalar → Bu siteyi uygulama olarak yükle**
2. Ad: `İhracat Bedeli Sistemi` → **Yükle**.

Sonuç: Masaüstünde **Kalıpsan logolu** simge oluşur. Çift tıklayınca uygulama
**adres çubuğu olmadan**, tıpkı bir masaüstü programı gibi açılır. Başlat menüsünde
ve görev çubuğunda da görünür (sağ tık → Görev çubuğuna sabitle).

---

## YOL 2 — Hazır script ile kısayol oluştur

Proje klasöründeki **`masaustu-kisayol.bat`** dosyasına çift tıklayın:

1. Uygulama adresini sorar:
   - Kendi PC'nizde çalıştırıyorsanız: `http://localhost:3000`
   - Şirket sunucusundaysa: `http://192.168.1.50` (IT ekibinizin verdiği adres)
   - Emergent'te yayındaysa: yayın adresiniz (`https://....emergent.host`)
2. Masaüstünde **"Ihracat Bedeli Sistemi"** adlı, **logolu** kısayol oluşturur.
3. Kısayol uygulamayı Chrome/Edge'in "uygulama modunda" (sekme ve adres çubuğu
   olmadan) açar.

> Simge dosyası: `frontend/public/favicon.ico` (logonuzdan üretildi).
> Kısayolun simgesini elle değiştirmek isterseniz: kısayola sağ tık → Özellikler →
> Simge Değiştir → bu dosyayı seçin.

---

## Kendi PC'nizde kurulumda önemli not

Uygulamanın açılması için arka planda iki servisin çalışıyor olması gerekir
(`baslat-backend.bat` ve `baslat-frontend.bat`). Bilgisayar her açıldığında
otomatik başlaması için:

1. `Win + R` → `shell:startup` → Enter (Başlangıç klasörü açılır).
2. `baslat-backend.bat` ve `baslat-frontend.bat` dosyalarının **kısayollarını**
   bu klasöre kopyalayın.

Böylece bilgisayarı açtığınızda servisler kendiliğinden çalışır, masaüstündeki
logolu simgeye tıklamanız yeterli olur.

Şirket sunucusuna kurulum yapıldıysa (Docker), servisler sunucuda 7/24 çalışır;
kullanıcıların yalnızca masaüstü kısayoluna ihtiyacı olur.
