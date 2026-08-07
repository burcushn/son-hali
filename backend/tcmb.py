import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import httpx

CURRENCIES = ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK", "CNY", "AED", "SAR", "RUB", "TRY"]

_cache: dict = {}


async def _fetch_day(d: datetime):
    url = f"https://www.tcmb.gov.tr/kurlar/{d.strftime('%Y%m')}/{d.strftime('%d%m%Y')}.xml"
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(url)
    if r.status_code != 200 or not r.text.strip().startswith("<?xml"):
        return None
    root = ET.fromstring(r.text)
    rates = {"TRY": 1.0}
    for cur in root.findall("Currency"):
        code = cur.get("Kod")
        if code not in CURRENCIES:
            continue
        unit = float((cur.findtext("Unit") or "1").strip())
        val = (cur.findtext("ForexSelling") or "").strip() or (cur.findtext("ForexBuying") or "").strip()
        if not val:
            continue
        rates[code] = float(val) / unit
    return {"date": root.get("Tarih") or d.strftime("%d.%m.%Y"), "rates": rates}


async def get_rates(date_str: str):
    """date_str: YYYY-MM-DD. TCMB kuru yoksa en yakın önceki iş günü kuru kullanılır."""
    try:
        base = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        base = datetime.now()
    if base > datetime.now():
        base = datetime.now()
    key = base.strftime("%Y-%m-%d")
    if key in _cache:
        return _cache[key]
    for i in range(0, 10):
        d = base - timedelta(days=i)
        try:
            res = await _fetch_day(d)
        except Exception:
            res = None
        if res:
            res["kur_tarihi"] = d.strftime("%Y-%m-%d")
            _cache[key] = res
            return res
    return None


async def cross_rate(from_cur: str, to_cur: str, date_str: str):
    """1 from_cur kaç to_cur eder."""
    from_cur, to_cur = from_cur.upper(), to_cur.upper()
    if from_cur == to_cur:
        return 1.0, "AYNI_DOVIZ", date_str[:10]
    data = await get_rates(date_str)
    if not data:
        return None, None, None
    r = data["rates"]
    if from_cur not in r or to_cur not in r:
        return None, None, None
    return round(r[from_cur] / r[to_cur], 6), "TCMB", data["kur_tarihi"]
