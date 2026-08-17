import os
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"

TR = "%d.%m.%Y"


def _d(s: str) -> str:
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").strftime(TR)
    except Exception:
        return "-"


def _money(n: float, cur: str = "") -> str:
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (f" {cur}" if cur else "")


def _table(title: str, color: str, rows: list, cols: list) -> str:
    if not rows:
        return ""
    head = "".join(
        f'<th style="text-align:left;padding:6px 8px;border-bottom:2px solid {color};'
        f'font-size:12px;text-transform:uppercase;color:#3f3f46">{c}</th>' for c in cols
    )
    body = ""
    for r in rows:
        body += "<tr>" + "".join(
            f'<td style="padding:6px 8px;border-bottom:1px solid #e4e4e7;font-size:13px;color:#18181b">{c}</td>'
            for c in r
        ) + "</tr>"
    return (
        f'<h3 style="font-size:15px;margin:24px 0 8px;color:{color}">{title} ({len(rows)})</h3>'
        f'<table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse">'
        f"<tr>{head}</tr>{body}</table>"
    )


def build_html(decs: list) -> tuple:
    gecmis = [d for d in decs if d["sure_durum"] == "GECMIS"]
    yaklasan = [d for d in decs if d["sure_durum"] == "YAKLASAN"]
    ibkb = [d for d in decs if d["ibkb_durum"] == "DUZENLENMEDI" and d["durum"] != "KAPALI"]
    destek = [d for d in decs
              if d["destek_durum"] == "ALINMADI" and d["durum"] != "KAPALI"
              and not d.get("destek_kapsam_disi")]

    def rows(items, extra=None):
        out = []
        for d in items:
            row = [d["beyanname_no"], d["ithalatci"], _money(d["kalan"], d["doviz"]),
                   _d(d["son_kapatma_tarihi"])]
            if extra == "gun":
                row.append(str(d["kalan_gun"]))
            elif extra == "destek":
                row[2] = _money(d["destek_tutari"], d["doviz"])
            out.append(row)
        return out

    cols = ["Beyanname No", "İthalatçı", "Kalan Tutar", "Son Kapatma"]
    html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:820px;margin:0 auto;padding:24px;background:#ffffff">'
        '<div style="border-left:4px solid #4338CA;padding-left:12px;margin-bottom:8px">'
        '<div style="font-size:11px;letter-spacing:2px;color:#71717a;text-transform:uppercase">Haftalık Özet</div>'
        '<h2 style="margin:4px 0 0;font-size:20px;color:#18181b">İhracat Bedeli Kapatma Uyarı Raporu</h2>'
        f'<div style="font-size:12px;color:#71717a">{datetime.now().strftime(TR)}</div></div>'
        f'<p style="font-size:13px;color:#3f3f46">Toplam {len(decs)} beyanname üzerinden aşağıdaki '
        "kayıtlar takip gerektirmektedir.</p>"
        + _table("Süresi Geçmiş Beyannameler", "#dc2626", rows(gecmis, "gun"), cols + ["Gün"])
        + _table("Süresi 30 Güne İnen Beyannameler", "#d97706", rows(yaklasan, "gun"), cols + ["Gün"])
        + _table("IBKB Düzenlenmemiş Beyannameler", "#4338CA", rows(ibkb), cols)
        + _table("Destek Ödemesi (%3) Alınmamış Beyannameler", "#0f766e", rows(destek, "destek"),
                 ["Beyanname No", "İthalatçı", "Destek Tutarı (%3)", "Son Kapatma"])
        + '<p style="font-size:11px;color:#a1a1aa;margin-top:28px;border-top:1px solid #e4e4e7;padding-top:12px">'
          "Bu e-posta İhracat Bedeli Kapatma ve Banka Bildirim Yönetim Sistemi tarafından otomatik "
          "oluşturulmuştur.</p></div>"
    )
    counts = {"gecmis": len(gecmis), "yaklasan": len(yaklasan),
              "ibkb": len(ibkb), "destek": len(destek)}
    return html, counts


def recipients() -> list:
    return [e.strip() for e in os.environ.get("ALERT_EMAILS", "").split(",") if e.strip()]


async def send_code(email: str, name: str, code: str) -> bool:
    html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;padding:24px">'
        '<div style="border-left:4px solid #4338CA;padding-left:12px">'
        '<div style="font-size:11px;letter-spacing:2px;color:#71717a;text-transform:uppercase">Giriş Doğrulama</div>'
        '<h2 style="margin:4px 0 0;font-size:19px;color:#18181b">İhracat Bedeli Kapatma Sistemi</h2></div>'
        f'<p style="font-size:14px;color:#3f3f46">Sayın {name or "kullanıcı"}, giriş doğrulama kodunuz:</p>'
        f'<div style="font-family:monospace;font-size:34px;letter-spacing:10px;font-weight:bold;'
        f'color:#4338CA;background:#f4f4f5;padding:16px;text-align:center;border:1px solid #e4e4e7">{code}</div>'
        '<p style="font-size:13px;color:#71717a">Kod 5 dakika geçerlidir ve yalnızca bir kez kullanılabilir. '
        "Bu girişi siz yapmadıysanız şifrenizi değiştirin.</p></div>"
    )
    payload = {"to": [email], "subject": f"Giriş doğrulama kodunuz: {code}", "html": html,
               "from_name": os.environ["EMAIL_FROM_NAME"]}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                             headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]},
                             json=payload)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"2FA code email error: {e}")
        return False


async def send_alert(decs: list) -> dict:
    to = recipients()
    if not to:
        return {"sent": False, "reason": "Alıcı e-posta adresi tanımlı değil"}
    html, counts = build_html(decs)
    subject = (f"İhracat Bedeli Haftalık Uyarı — {counts['gecmis']} süresi geçmiş, "
               f"{counts['yaklasan']} yaklaşan")
    payload = {"to": to, "subject": subject, "html": html,
               "from_name": os.environ["EMAIL_FROM_NAME"]}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                             headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]},
                             json=payload)
        r.raise_for_status()
        return {"sent": True, "to": to, "counts": counts, "email_id": r.json().get("id")}
    except httpx.HTTPStatusError as e:
        logger.error(f"Alert email failed: {e.response.status_code} {e.response.text}")
        return {"sent": False, "reason": "E-posta gönderilemedi", "counts": counts}
    except Exception as e:
        logger.error(f"Alert email error: {e}")
        return {"sent": False, "reason": str(e), "counts": counts}
