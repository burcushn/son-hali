# PRD — İhracat Bedeli Kapatma ve Banka Bildirim Yönetim Sistemi

## Problem Statement (orijinal)
İhracat beyannamelerinin bankaya gelen ihracat bedelleriyle doğru eşleştirilmesi, açık/kısmi/kapalı işlemlerin takibi ve bankaya gönderilecek resmi Excel dosyalarının otomatik hazırlanması. Masaüstü öncelikli, mobil uyumlu. Roller farklı yetkilere sahip.

## Kullanıcı Kararları
- Beyanname ve bedeller ayrı ayrı manuel girilir, sonra eşleştirilir (kısmi/tam).
- Bedelin kalan bakiyesi başka beyannamede kullanılabilir.
- Döviz aynı olmak zorunda değil; kur TCMB'den **GB tescil tarihi** ile otomatik çekilir (manuel kur opsiyonu var). Eksik kalırsa beyanname KISMİ kalır.
- Son kapatma tarihi = GB tescil tarihi + 180 gün.
- Kapatma beyanname tutarını aşamaz.
- Eşleştirmeyi Onaylayan (Şef) doğrudan yapar.
- Roller birbirinin işine müdahale edemez; herkes her şeyi görür.

## Mimari
React (CRA + Tailwind + shadcn) · FastAPI · MongoDB (motor) · JWT httpOnly cookie + Bearer · TCMB XML kur servisi · openpyxl Excel.
Backend: `server.py`, `models.py` (BaseDocument/PyObjectId), `tcmb.py`.
Frontend: `pages/` (Login, Dashboard, Declarations, Payments, AuditLog, Reports, Users), `components/` (Layout, MatchDialog), `context/AuthContext`, `lib/apiClient`.

## Roller
| Yetki | admin | ihracat | banka | onaylayan | goruntuleyici |
|---|---|---|---|---|---|
| Görüntüleme/Rapor/Excel | ✔ | ✔ | ✔ | ✔ | ✔ |
| Beyanname CRUD | ✔ | ✔ | – | – | – |
| Bedel CRUD | ✔ | – | ✔ | – | – |
| Eşleştirme/geri alma | ✔ | – | – | ✔ | – |
| Kullanıcı yönetimi | ✔ | – | – | – | – |

## Tamamlananlar (2026-06)
- JWT auth + 5 rol, admin & demo kullanıcı seed
- Dashboard: açık/kısmi/kapalı sayıları, döviz bazlı açık tutar, kullanılabilir bedel bakiyesi, süresi yaklaşan (≤30 gün) / geçen listeleri, son hareketler
- Beyanname yönetimi (CRUD, arama, durum & süre filtreleri, 180 gün otomatik)
- Bedel yönetimi (CRUD, kullanılan/bakiye/durum otomatik)
- Eşleştirme modalı: bedel seçimi, kısmi/tam kapatma, TCMB çapraz kur, manuel kur, eksik bakiye önizleme, düzeltme/geri alma
- Hareket geçmişi (audit log) + modül filtresi
- Raporlar (döviz/ülke/ay) + Recharts grafiği
- Excel aktarma (2 sayfa: Banka Bildirimi + Eşleştirme Detayı)
- Kullanıcı yönetimi + yetki matrisi
- Test: 31/31 backend, 23/23 frontend geçti

## Güncelleme (2026-06, 2. tur)
- Beyanname alan seti yenilendi: beyanname no, açılış tarihi, kapanış tarihi, tutar, döviz, **ithalatçı**, gümrük müdürlüğü no, IBKB durumu (DÜZENLENDİ/DÜZENLENMEDİ), destek ödemesi %3 (ALINDI/ALINMADI). Eski alanlar (ihracatçı/alıcı/ülke/fatura no) kaldırıldı.
- Süre: **kapanış tarihi + 180 gün** (kapanış yoksa açılış + 180).
- Eşleştirmede aynı döviz seçilirse kur alanı hiç görünmez, tutar birebir kapatılır (kur=1, AYNI_DOVIZ); kur yalnızca farklı dövizlerde, TCMB açılış tarihi kuruyla otomatik gelir (manuel override mümkün).
- IBKB/Destek filtreleri, raporlarda ithalatçı bazlı özet + IBKB/destek eksik sayaçları, Excel yeni kolonlar.

## Güncelleme (2026-06, 3. tur)
- **Girişte 2 adımlı doğrulama (2FA):** kullanıcı bazında açılabilir; e-postaya 6 haneli kod (5 dk, tek kullanımlık, 5 hatalı denemede kilit), kodu tekrar gönder akışı. Şifre adımında 5 hatalı denemede 15 dk hesap kilidi.
- **Haftalık e-posta uyarısı:** her Pazartesi 09:00 (Europe/Istanbul) → burcusahin@kalipsanaluminyum.com. İçerik: süresi geçmiş, 30 güne inen, IBKB düzenlenmemiş, destek (%3) alınmamış beyannameler. Raporlar sayfasında "Şimdi Gönder" (admin/onaylayan).
- Test: 42/42 backend pytest + frontend 2FA ve uyarı akışları geçti.

## Güncelleme (2026-06, 4. tur)
- **IBKB İşlemleri ekranı (/ibkb):** IBKB No, IBKB tarihi, **dosya referansı**, TCMB devir oranı (%100 zorunlu), kullanılacak **DTH** ve **ACH** tutarları (zorunlu %30 bozdurmanın nereye aktarıldığı) banka personeli tarafından girilir.
- **Beyannameye Teşvik / Taahhüt (EVET-HAYIR)** alanları eklendi.
- **Excel bankanın resmi şablonuna göre yeniden yazıldı:** ilk sayfa "BANKA BİLDİRİMİ" — SIRA NO, DOSYA REFERANSI, GÜMRÜK MÜDÜRLÜĞÜ KODU, GB NO, GB TARİHİ (gg.aa.yyyy), GB'YE SAYILACAK TUTAR, KULLANILACAK DTH, KULLANILACAK ACH, TCMB DEVİR ORANI, TEŞVİK, TAAHHÜT + TOPLAM satırı. Ek sayfalar: Beyanname Listesi, Eşleştirme Detayı.
- Test: 51/51 backend pytest + frontend IBKB/yetki akışları geçti.

## Backlog
- P0: Bankanın resmi Excel şablonuna birebir uyarlama (müşteri dosyayı paylaşacak)
- P0: Bedel (banka girişi) formuna bankadan gelen ek alanların eklenmesi (müşteri alan listesini paylaşacak)
- P1: Excel/CSV ile toplu beyanname & bedel içe aktarma; otomatik eşleştirme önerisi
- P1: Beyanname/bedel dosya eki (fatura, swift PDF) yükleme
- P2: Brute-force kilidi, CORS için açık origin listesi, e-posta ile süre uyarı bildirimi, PDF rapor
