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

## Backlog
- P0: Bankanın resmi Excel şablonuna birebir uyarlama (müşteri dosyayı paylaşacak)
- P1: Excel/CSV ile toplu beyanname & bedel içe aktarma; otomatik eşleştirme önerisi
- P1: Beyanname/bedel dosya eki (fatura, swift PDF) yükleme
- P2: Brute-force kilidi, CORS için açık origin listesi, e-posta ile süre uyarı bildirimi, PDF rapor
