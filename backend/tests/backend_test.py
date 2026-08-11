"""Backend tests for İhracat Bedel Kapatma sistemi (v2 schema)."""
import os
from datetime import datetime, timedelta

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin":     ("admin@ihracat.com",   "Admin1234!"),
    "ihracat":   ("ihracat@ihracat.com", "Test1234!"),
    "banka":     ("banka@ihracat.com",   "Test1234!"),
    "onaylayan": ("sef@ihracat.com",     "Test1234!"),
    "viewer":    ("viewer@ihracat.com",  "Test1234!"),
}
TWOFA_EMAIL = "test2fa@ihracat.com"
TWOFA_PW = "Test1234!"


def _read_last_2fa_code():
    """Read latest [2FA] line from backend log."""
    import subprocess
    for path in ("/var/log/supervisor/backend.err.log", "/var/log/supervisor/backend.out.log"):
        try:
            out = subprocess.check_output(
                f"grep '\\[2FA\\]' {path} | tail -1", shell=True, text=True, timeout=5)
            if out.strip():
                # "... [2FA] test2fa@... doğrulama kodu: 123456"
                return out.strip().split(":")[-1].strip()
        except Exception:
            continue
    return None


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert data.get("token"), "token missing"
    return data["token"], data


@pytest.fixture(scope="module")
def tokens():
    return {role: _login(e, p)[0] for role, (e, p) in CREDS.items()}


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _base_dec(beyanname_no, acilis, kapanis="", doviz="EUR", tutar=10000.0,
              ithalatci="TEST Ithalatci A.S.", gumruk="GM-001",
              ibkb=False, destek=False):
    return {
        "beyanname_no": beyanname_no,
        "acilis_tarihi": acilis,
        "kapanis_tarihi": kapanis,
        "ithalatci": ithalatci,
        "gumruk_mudurlugu_no": gumruk,
        "doviz": doviz,
        "tutar": tutar,
        "ibkb_alindi": ibkb,
        "destek_alindi": destek,
    }


# ---------- auth ----------
class TestAuth:
    def test_login_all_roles(self):
        for role, (e, p) in CREDS.items():
            _, data = _login(e, p)
            assert data["email"] == e
            assert data["role"] in ("admin", "ihracat", "banka", "onaylayan", "goruntuleyici")

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@ihracat.com", "password": "wrongxxx"})
        assert r.status_code == 401

    def test_me(self, tokens):
        r = requests.get(f"{API}/auth/me", headers=_h(tokens["admin"]))
        assert r.status_code == 200 and r.json()["role"] == "admin"

    def test_me_unauthorized(self):
        assert requests.get(f"{API}/auth/me").status_code == 401


# ---------- declarations (new schema) ----------
class TestDeclarations:
    beyanname_no = f"TEST_BEY_{int(datetime.now().timestamp())}"
    acilis = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    kapanis = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    created_id = None

    def test_create_with_kapanis(self, tokens):
        payload = _base_dec(self.__class__.beyanname_no, self.acilis, self.kapanis,
                            doviz="EUR", tutar=10000.0, ithalatci="TEST GmbH",
                            gumruk="GM-42", ibkb=False, destek=False)
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["beyanname_no"] == self.__class__.beyanname_no
        assert d["durum"] == "ACIK"
        assert d["kalan"] == 10000.0
        assert d["ithalatci"] == "TEST GmbH"
        assert d["gumruk_mudurlugu_no"] == "GM-42"
        assert d["ibkb_durum"] == "DUZENLENMEDI"
        assert d["destek_durum"] == "ALINMADI"
        # destek = %3
        assert abs(d["destek_tutari"] - 300.0) < 0.01
        # son kapatma = kapanis + 180
        exp = (datetime.strptime(self.kapanis, "%Y-%m-%d") + timedelta(days=180)).strftime("%Y-%m-%d")
        assert d["son_kapatma_tarihi"] == exp
        self.__class__.created_id = d["id"]

    def test_son_kapatma_falls_back_to_acilis(self, tokens):
        no = f"TEST_FALLBACK_{int(datetime.now().timestamp())}"
        acilis = "2026-02-01"
        payload = _base_dec(no, acilis, "", tutar=1000.0)
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        exp = (datetime.strptime(acilis, "%Y-%m-%d") + timedelta(days=180)).strftime("%Y-%m-%d")
        assert d["son_kapatma_tarihi"] == exp
        requests.delete(f"{API}/declarations/{d['id']}", headers=_h(tokens["ihracat"]))

    def test_ibkb_destek_true(self, tokens):
        no = f"TEST_IBKB_{int(datetime.now().timestamp())}"
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]),
                          json=_base_dec(no, "2026-01-01", tutar=5000.0, ibkb=True, destek=True))
        assert r.status_code == 200
        d = r.json()
        assert d["ibkb_durum"] == "DUZENLENDI" and d["destek_durum"] == "ALINDI"
        assert abs(d["destek_tutari"] - 150.0) < 0.01
        requests.delete(f"{API}/declarations/{d['id']}", headers=_h(tokens["ihracat"]))

    def test_duplicate_beyanname_no(self, tokens):
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]),
                          json=_base_dec(self.__class__.beyanname_no, self.acilis))
        assert r.status_code == 400 and "zaten" in r.text.lower()

    def test_rbac_create(self, tokens):
        for role in ["banka", "onaylayan", "viewer"]:
            r = requests.post(f"{API}/declarations", headers=_h(tokens[role]),
                              json=_base_dec(f"NO_{role}", "2026-01-01"))
            assert r.status_code == 403, f"{role} should be 403"

    def test_all_roles_can_list(self, tokens):
        for role in ["admin", "ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.get(f"{API}/declarations", headers=_h(tokens[role]))
            assert r.status_code == 200 and isinstance(r.json(), list)

    def test_search_by_ithalatci_and_gumruk(self, tokens):
        r = requests.get(f"{API}/declarations", headers=_h(tokens["admin"]),
                         params={"q": "TEST GmbH"})
        assert r.status_code == 200
        assert any(d["id"] == self.__class__.created_id for d in r.json())
        r2 = requests.get(f"{API}/declarations", headers=_h(tokens["admin"]),
                          params={"q": "GM-42"})
        assert any(d["id"] == self.__class__.created_id for d in r2.json())

    def test_filter_ibkb_destek(self, tokens):
        r = requests.get(f"{API}/declarations", headers=_h(tokens["admin"]),
                         params={"ibkb": "DUZENLENMEDI"})
        assert r.status_code == 200
        assert all(d["ibkb_durum"] == "DUZENLENMEDI" for d in r.json())
        r2 = requests.get(f"{API}/declarations", headers=_h(tokens["admin"]),
                          params={"destek": "ALINMADI"})
        assert all(d["destek_durum"] == "ALINMADI" for d in r2.json())


# ---------- payments ----------
class TestPayments:
    created_id = None

    def test_banka_create(self, tokens):
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST Bank", "gonderen": "TEST Buyer GmbH",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "doviz": "EUR", "tutar": 15000.0, "aciklama": "TEST",
        })
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["bakiye"] == 15000.0 and p["durum"] == "KULLANILMADI"
        self.__class__.created_id = p["id"]

    def test_rbac_create(self, tokens):
        for role in ["ihracat", "onaylayan", "viewer"]:
            r = requests.post(f"{API}/payments", headers=_h(tokens[role]),
                              json={"banka": "x", "gonderen": "y", "tarih": "2026-01-01",
                                    "doviz": "USD", "tutar": 1})
            assert r.status_code == 403


# ---------- matching (same currency and cross currency) ----------
class TestMatching:
    dec_id = None
    pay_id = None
    pay_usd_id = None
    match_id = None
    dec_no = f"TEST_MATCH_{int(datetime.now().timestamp())}"

    def test_setup(self, tokens):
        acilis = "2026-03-02"
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]),
                          json=_base_dec(self.__class__.dec_no, acilis, doviz="EUR", tutar=5000.0))
        assert r.status_code == 200
        self.__class__.dec_id = r.json()["id"]

        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST", "gonderen": "TEST",
            "tarih": "2026-03-02", "doviz": "EUR", "tutar": 8000.0})
        assert r.status_code == 200
        self.__class__.pay_id = r.json()["id"]

        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST", "gonderen": "TEST-USD",
            "tarih": "2026-03-02", "doviz": "USD", "tutar": 5000.0})
        assert r.status_code == 200
        self.__class__.pay_usd_id = r.json()["id"]

    def test_ihracat_cannot_match(self, tokens):
        r = requests.post(f"{API}/matches", headers=_h(tokens["ihracat"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 100})
        assert r.status_code == 403

    def test_same_currency_match_kur_1(self, tokens):
        """Same currency => kur=1, kur_kaynak='AYNI_DOVIZ', bedel = kapatilan."""
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 2000.0})
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["kur"] == 1.0
        assert m["kur_kaynak"] == "AYNI_DOVIZ"
        assert m["kapatilan_tutar"] == 2000.0
        assert m["bedel_kullanilan"] == 2000.0
        self.__class__.match_id = m["id"]

        d = next(x for x in requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
                 if x["id"] == self.__class__.dec_id)
        assert d["durum"] == "KISMI" and d["kapatilan"] == 2000.0 and d["kalan"] == 3000.0

        p = next(x for x in requests.get(f"{API}/payments", headers=_h(tokens["admin"])).json()
                 if x["id"] == self.__class__.pay_id)
        assert p["kullanilan"] == 2000.0 and p["bakiye"] == 6000.0

    def test_over_declaration_kalan(self, tokens):
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 4000.0})
        assert r.status_code == 400
        assert "kalan" in r.text.lower() or "aş" in r.text.lower()

    def test_over_payment_bakiye(self, tokens):
        # Cross-currency (EUR beyanname, USD bedel) with tiny kur so bedel needed >> bakiye
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_usd_id,
            "kapatilan_tutar": 3000.0, "kur": 0.1})
        assert r.status_code == 400
        assert "bakiye" in r.text.lower() or "yetersiz" in r.text.lower()

    def test_cross_currency_uses_tcmb(self, tokens):
        """Different currencies -> TCMB rate auto applied; bedel = kapatilan/kur."""
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_usd_id,
            "kapatilan_tutar": 100.0})
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            m = r.json()
            assert m["kur_kaynak"] == "TCMB"
            assert m["kur"] > 0
            # bedel_kullanilan = 100 / kur, approximately
            assert abs(m["bedel_kullanilan"] - 100.0 / m["kur"]) < 0.02
            requests.delete(f"{API}/matches/{m['id']}", headers=_h(tokens["onaylayan"]))

    def test_delete_blocked_when_matched(self, tokens):
        r = requests.delete(f"{API}/declarations/{self.__class__.dec_id}",
                            headers=_h(tokens["ihracat"]))
        assert r.status_code == 400
        r = requests.delete(f"{API}/payments/{self.__class__.pay_id}",
                            headers=_h(tokens["banka"]))
        assert r.status_code == 400

    def test_update_match_recalcs(self, tokens):
        r = requests.put(f"{API}/matches/{self.__class__.match_id}?kapatilan_tutar=1500",
                         headers=_h(tokens["onaylayan"]))
        assert r.status_code == 200, r.text
        d = next(x for x in requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
                 if x["id"] == self.__class__.dec_id)
        assert d["kapatilan"] == 1500.0

    def test_delete_match_restores(self, tokens):
        r = requests.delete(f"{API}/matches/{self.__class__.match_id}",
                            headers=_h(tokens["onaylayan"]))
        assert r.status_code == 200
        d = next(x for x in requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
                 if x["id"] == self.__class__.dec_id)
        assert d["kapatilan"] == 0.0 and d["durum"] == "ACIK"

    def test_cleanup(self, tokens):
        requests.delete(f"{API}/declarations/{self.__class__.dec_id}", headers=_h(tokens["ihracat"]))
        requests.delete(f"{API}/payments/{self.__class__.pay_id}", headers=_h(tokens["banka"]))
        requests.delete(f"{API}/payments/{self.__class__.pay_usd_id}", headers=_h(tokens["banka"]))


# ---------- reports / excel / dashboard ----------
class TestReportsAndDashboard:
    def test_reports_summary(self, tokens):
        r = requests.get(f"{API}/reports/summary", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        d = r.json()
        for k in ["doviz", "ithalatci", "ibkb_alinmadi", "destek_alinmadi", "ay"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["ithalatci"], list)
        assert isinstance(d["ibkb_alinmadi"], int)
        assert isinstance(d["destek_alinmadi"], int)

    def test_dashboard(self, tokens):
        r = requests.get(f"{API}/dashboard", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        for k in ["acik", "kismi", "kapali", "acik_tutar", "bedel_bakiye",
                  "yaklasan", "gecmis", "son_hareketler"]:
            assert k in r.json()

    def test_audit_logs(self, tokens):
        r = requests.get(f"{API}/audit-logs", headers=_h(tokens["admin"]))
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_excel_export_has_new_columns(self, tokens):
        r = requests.get(f"{API}/export/excel", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct.lower() or "excel" in ct.lower()
        # Read workbook and check headers
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb["BANKA BİLDİRİMİ"]
        headers = [c.value for c in ws[1]]
        expected = ["SIRA NO", "DOSYA REFERANSI", "GÜMRÜK MÜDÜRLÜĞÜ KODU", "GB NO", "GB TARİHİ",
                    "GB'YE SAYILACAK TUTAR", "KULLANILACAK DTH", "KULLANILACAK ACH",
                    "TCMB DEVİR ORANI", "TEŞVİK", "TAAHHÜT"]
        assert headers[:len(expected)] == expected, headers
        ws1 = wb["Beyanname Listesi"]
        h1 = [c.value for c in ws1[1]]
        for e in ["Beyanname No", "Açılış Tarihi", "Kapanış Tarihi",
                  "Son Kapatma Tarihi (180 gün)", "İthalatçı", "Gümrük Müdürlüğü No",
                  "IBKB Belgesi Durumu", "Destek Ödemesi (%3)", "Destek Durumu",
                  "Teşvik", "Taahhüt"]:
            assert e in h1, f"missing excel header: {e}"


# ---------- users ----------
class TestUsers:
    def test_admin_only_list(self, tokens):
        r = requests.get(f"{API}/users", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        for role in ["ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.get(f"{API}/users", headers=_h(tokens[role]))
            assert r.status_code == 403, f"{role} should not access user list"

    def test_non_admin_cannot_create(self, tokens):
        for role in ["ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.post(f"{API}/users", headers=_h(tokens[role]), json={
                "email": f"nope_{role}@test.com", "name": "x",
                "role": "goruntuleyici", "password": "P@ss12345"})
            assert r.status_code == 403

    def test_admin_crud_user(self, tokens):
        email = f"test_new_{int(datetime.now().timestamp())}@ihracat.com"
        r = requests.post(f"{API}/users", headers=_h(tokens["admin"]), json={
            "email": email, "name": "TEST", "role": "goruntuleyici", "password": "P@ss12345"})
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        r = requests.put(f"{API}/users/{uid}", headers=_h(tokens["admin"]),
                         json={"role": "banka"})
        assert r.status_code == 200 and r.json()["role"] == "banka"
        r = requests.delete(f"{API}/users/{uid}", headers=_h(tokens["admin"]))
        assert r.status_code == 200


# ---------- 2FA login flow ----------
class TestTwoFactor:
    challenge_id = None

    def test_login_2fa_returns_challenge(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": TWOFA_EMAIL, "password": TWOFA_PW}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("two_factor") is True
        assert data.get("challenge_id")
        assert "token" not in data
        self.__class__.challenge_id = data["challenge_id"]

    def test_verify_wrong_code_401(self):
        assert self.__class__.challenge_id
        r = requests.post(f"{API}/auth/verify-code",
                          json={"challenge_id": self.__class__.challenge_id, "code": "000000"})
        # If real code happens to be 000000, this would be 200 (extremely unlikely)
        assert r.status_code == 401, r.text
        assert "hatalı" in r.text.lower()

    def test_verify_correct_code_issues_token(self):
        import time
        time.sleep(0.6)  # let backend flush log
        code = _read_last_2fa_code()
        assert code and len(code) == 6, f"could not read 2FA code from log: {code!r}"
        r = requests.post(f"{API}/auth/verify-code",
                          json={"challenge_id": self.__class__.challenge_id, "code": code})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("token")
        assert data["email"] == TWOFA_EMAIL
        self.__class__.token = data["token"]

    def test_same_code_cannot_be_reused(self):
        code = _read_last_2fa_code()
        r = requests.post(f"{API}/auth/verify-code",
                          json={"challenge_id": self.__class__.challenge_id, "code": code})
        assert r.status_code == 400, r.text  # used

    def test_resend_creates_new_challenge_invalidates_old(self):
        import time
        r = requests.post(f"{API}/auth/login",
                          json={"email": TWOFA_EMAIL, "password": TWOFA_PW})
        old_cid = r.json()["challenge_id"]
        time.sleep(0.6)
        old_code = _read_last_2fa_code()

        r = requests.post(f"{API}/auth/resend-code", json={"challenge_id": old_cid})
        assert r.status_code == 200
        new_cid = r.json()["challenge_id"]
        assert new_cid != old_cid
        time.sleep(0.6)
        new_code = _read_last_2fa_code()
        assert new_code and new_code != old_code

        # old challenge is 'used' -> 400
        r = requests.post(f"{API}/auth/verify-code",
                          json={"challenge_id": old_cid, "code": old_code})
        assert r.status_code == 400

        # new code works
        r = requests.post(f"{API}/auth/verify-code",
                          json={"challenge_id": new_cid, "code": new_code})
        assert r.status_code == 200

    def test_five_wrong_attempts_locks(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": TWOFA_EMAIL, "password": TWOFA_PW})
        cid = r.json()["challenge_id"]
        codes = ["000001", "000002", "000003", "000004", "000005"]
        last = None
        for c in codes:
            last = requests.post(f"{API}/auth/verify-code",
                                 json={"challenge_id": cid, "code": c})
        # last (5th wrong) may still be 401; a 6th call should return 429
        r6 = requests.post(f"{API}/auth/verify-code",
                           json={"challenge_id": cid, "code": "999999"})
        assert r6.status_code == 429, f"expected 429 after 5 fails, got {r6.status_code} {r6.text}"

    def test_two_factor_off_account_single_step(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@ihracat.com", "password": "Admin1234!"})
        assert r.status_code == 200
        data = r.json()
        assert data.get("token")
        assert not data.get("two_factor")


# ---------- admin toggles 2FA flag ----------
class TestUserTwoFactorToggle:
    def test_admin_toggle_two_factor(self, tokens):
        # Create a fresh user (default two_factor=True per server.py)
        email = f"test_2fa_toggle_{int(datetime.now().timestamp())}@ihracat.com"
        r = requests.post(f"{API}/users", headers=_h(tokens["admin"]), json={
            "email": email, "name": "TEST 2FA", "role": "goruntuleyici",
            "password": "P@ss12345"})
        assert r.status_code == 200
        uid = r.json()["id"]
        assert r.json().get("two_factor") is True

        # Login should now require 2FA
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "P@ss12345"})
        assert r.status_code == 200 and r.json().get("two_factor") is True

        # Turn 2FA OFF
        r = requests.put(f"{API}/users/{uid}", headers=_h(tokens["admin"]),
                         json={"two_factor": False})
        assert r.status_code == 200 and r.json()["two_factor"] is False

        # Login should be single-step now
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "P@ss12345"})
        assert r.status_code == 200
        assert r.json().get("token")
        assert not r.json().get("two_factor")

        # cleanup
        requests.delete(f"{API}/users/{uid}", headers=_h(tokens["admin"]))


# ---------- alerts preview + send RBAC ----------
class TestAlerts:
    def test_preview_all_roles(self, tokens):
        for role in ["admin", "ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.get(f"{API}/alerts/preview", headers=_h(tokens[role]))
            assert r.status_code == 200, f"{role} {r.text}"
            data = r.json()
            for k in ["alicilar", "sayilar", "plan"]:
                assert k in data
            for k in ["gecmis", "yaklasan", "ibkb", "destek"]:
                assert k in data["sayilar"]
            assert isinstance(data["alicilar"], list)
            assert data["alicilar"], "recipients list should be non-empty"

    def test_send_rbac_forbidden_roles(self, tokens):
        for role in ["ihracat", "banka", "viewer"]:
            r = requests.post(f"{API}/alerts/send", headers=_h(tokens[role]))
            assert r.status_code == 403, f"{role} should be 403 got {r.status_code}"

    def test_send_by_onaylayan_and_audit(self, tokens):
        # Single real send (avoid spamming)
        r = requests.post(f"{API}/alerts/send", headers=_h(tokens["onaylayan"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("sent") is True
        # audit log should contain Uyarı/EPOSTA entry
        r = requests.get(f"{API}/audit-logs", headers=_h(tokens["admin"]),
                         params={"modul": "Uyarı"})
        assert r.status_code == 200
        logs = r.json()
        assert any(l.get("islem") == "EPOSTA" for l in logs), "no audit log for alert send"


# ---------- IBKB (v3) + Banka Bildirimi Excel şablonu ----------
class TestIbkbAndBankaBildirimi:
    dec_id = None
    dec_no = f"TEST_IBKBFLOW_{int(datetime.now().timestamp())}"
    pay_eur_id = None
    pay_usd_id = None
    match_ids = []
    acilis = "2026-04-02"

    def test_seed(self, tokens):
        # Beyanname (EUR 10000)
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]),
                          json={**_base_dec(self.__class__.dec_no, self.acilis,
                                            doviz="EUR", tutar=10000.0,
                                            ithalatci="TEST IBKB GmbH", gumruk="GM-IBKB"),
                                "tesvik": True, "taahhut": True})
        assert r.status_code == 200, r.text
        self.__class__.dec_id = r.json()["id"]

        # EUR bedel 6000
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "Ziraat", "gonderen": "TEST IBKB EUR",
            "tarih": self.acilis, "doviz": "EUR", "tutar": 6000.0})
        assert r.status_code == 200
        self.__class__.pay_eur_id = r.json()["id"]

        # USD bedel 9000
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "Is Bankasi", "gonderen": "TEST IBKB USD",
            "tarih": self.acilis, "doviz": "USD", "tutar": 9000.0})
        assert r.status_code == 200
        self.__class__.pay_usd_id = r.json()["id"]

    def test_payment_persists_dth_ach_iban(self, tokens):
        """PaymentInput.dth_iban / ach_iban are persisted and readable via GET /api/payments."""
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST", "gonderen": "TEST_IBAN_PAY",
            "tarih": "2026-04-02", "doviz": "EUR", "tutar": 100.0,
            "dth_iban": "TR22 EUR IBAN 0000 0000 0000 01",
            "ach_iban": "TR22 TL  IBAN 0000 0000 0000 02",
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["dth_iban"].startswith("TR22 EUR")
        assert r.json()["ach_iban"].startswith("TR22 TL")

        got = next(x for x in requests.get(f"{API}/payments", headers=_h(tokens["admin"])).json()
                   if x["id"] == pid)
        assert got["dth_iban"].startswith("TR22 EUR")
        assert got["ach_iban"].startswith("TR22 TL")
        requests.delete(f"{API}/payments/{pid}", headers=_h(tokens["banka"]))

    def test_ach_iban_fallback_to_default_env(self, tokens):
        """When ach_iban is empty, payment_view returns DEFAULT_ACH_IBAN env value."""
        default_iban = "TR00 0000 0000 0000 0000 0000 00"
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST", "gonderen": "TEST_ACH_FALLBACK",
            "tarih": "2026-04-02", "doviz": "EUR", "tutar": 50.0,
        })
        assert r.status_code == 200
        pid = r.json()["id"]
        got = next(x for x in requests.get(f"{API}/payments", headers=_h(tokens["admin"])).json()
                   if x["id"] == pid)
        assert got["ach_iban"] == "", got["ach_iban"]
        assert got["ach_iban_default"] == default_iban, got["ach_iban_default"]
        requests.delete(f"{API}/payments/{pid}", headers=_h(tokens["banka"]))

    def test_ibkb_payment_view_defaults(self, tokens):
        r = requests.get(f"{API}/payments", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        p = next(x for x in r.json() if x["id"] == self.__class__.pay_eur_id)
        assert p["ibkb_durum"] == "DUZENLENMEDI"
        # zorunlu bozdurma = %30
        assert abs(p["zorunlu_bozdurma"] - 1800.0) < 0.01
        assert p["tcmb_devir_orani"] == 100.0

    def test_ibkb_rbac_forbidden_roles(self, tokens):
        payload = {"ibkb_no": "IBKB-1", "ibkb_tarihi": "2026-04-03",
                   "dosya_referansi": "REF-1", "ach_iban": "TR11 0006 2000 0000 0000 0000 01",
                   "tcmb_devir_orani": 100}
        for role in ["ihracat", "onaylayan", "viewer"]:
            r = requests.put(f"{API}/payments/{self.__class__.pay_eur_id}/ibkb",
                             headers=_h(tokens[role]), json=payload)
            assert r.status_code == 403, f"{role} should be 403, got {r.status_code}"

    def test_dth_iban_from_payment(self, tokens):
        r = requests.get(f"{API}/payments", headers=_h(tokens["admin"]))
        p = next(x for x in r.json() if x["id"] == self.__class__.pay_eur_id)
        assert "dth_iban" in p and "ach_iban" in p

    def test_banka_can_save_ibkb(self, tokens):
        r = requests.put(f"{API}/payments/{self.__class__.pay_eur_id}/ibkb",
                         headers=_h(tokens["banka"]),
                         json={"ibkb_duzenlendi": True, "ibkb_no": "IBKB-EUR-1",
                               "ibkb_tarihi": "2026-04-03",
                               "dosya_referansi": "DOSYA-EUR-1",
                               "ach_iban": "TR11 0006 2000 1234 0006 2999 88",
                               "tcmb_devir_orani": 100})
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["ibkb_durum"] == "DUZENLENDI"
        assert p["ibkb_no"] == "IBKB-EUR-1"
        assert p["dosya_referansi"] == "DOSYA-EUR-1"
        assert p["ach_iban"] == "TR11 0006 2000 1234 0006 2999 88"
        assert p["tcmb_devir_orani"] == 100

        r = requests.put(f"{API}/payments/{self.__class__.pay_usd_id}/ibkb",
                         headers=_h(tokens["admin"]),
                         json={"ibkb_duzenlendi": True, "ibkb_no": "IBKB-USD-1",
                               "ibkb_tarihi": "2026-04-03",
                               "dosya_referansi": "DOSYA-USD-1",
                               "tcmb_devir_orani": 100})
        assert r.status_code == 200

    def test_ibkb_input_rejects_legacy_tutar_fields(self, tokens):
        """dth_tutar / ach_tutar are no longer part of IbkbInput; extras must be ignored.
        The endpoint must still succeed but the payment must not store any tutar fields."""
        r = requests.put(f"{API}/payments/{self.__class__.pay_eur_id}/ibkb",
                         headers=_h(tokens["banka"]),
                         json={"ibkb_duzenlendi": True, "ibkb_no": "IBKB-EUR-1",
                               "ibkb_tarihi": "2026-04-03",
                               "dosya_referansi": "DOSYA-EUR-1",
                               "ach_iban": "TR11 0006 2000 1234 0006 2999 88",
                               "tcmb_devir_orani": 100,
                               "dth_tutar": 123, "ach_tutar": 456})
        assert r.status_code == 200, r.text
        p = r.json()
        assert "dth_tutar" not in p
        assert "ach_tutar" not in p

    def test_create_matches(self, tokens):
        # EUR->EUR match 3000
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id,
            "payment_id": self.__class__.pay_eur_id,
            "kapatilan_tutar": 3000.0})
        assert r.status_code == 200, r.text
        self.__class__.match_ids.append(r.json()["id"])

        # USD->EUR match 1000 (manual kur 1.1 to avoid TCMB dependency)
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id,
            "payment_id": self.__class__.pay_usd_id,
            "kapatilan_tutar": 1000.0, "kur": 0.9})
        assert r.status_code == 200, r.text
        self.__class__.match_ids.append(r.json()["id"])

    def test_excel_banka_bildirimi_shape(self, tokens):
        r = requests.get(f"{API}/export/excel", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        import io as _io
        from openpyxl import load_workbook
        wb = load_workbook(_io.BytesIO(r.content))
        assert "BANKA BİLDİRİMİ" in wb.sheetnames
        assert wb.sheetnames[0] == "BANKA BİLDİRİMİ"
        assert "Beyanname Listesi" in wb.sheetnames
        assert "Eşleştirme Detayı" in wb.sheetnames

        ws = wb["BANKA BİLDİRİMİ"]
        expected = ["SIRA NO", "DOSYA REFERANSI", "GÜMRÜK MÜDÜRLÜĞÜ KODU", "GB NO",
                    "GB TARİHİ", "GB'YE SAYILACAK TUTAR", "KULLANILACAK DTH",
                    "KULLANILACAK ACH", "TCMB DEVİR ORANI", "TEŞVİK", "TAAHHÜT"]
        headers = [c.value for c in ws[1]]
        assert headers == expected, headers

        # Find our two rows by GB NO
        our_rows = []
        toplam_row = None
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == "TOPLAM":
                toplam_row = row
                continue
            if row[3] == self.__class__.dec_no:
                our_rows.append(row)
        assert len(our_rows) == 2, f"expected 2 matching rows, got {len(our_rows)}"

        # Sıra artıyor
        siras = [r[0] for r in our_rows]
        assert all(isinstance(s, int) and s > 0 for s in siras)

        for row in our_rows:
            # dosya referansı bedelden
            assert row[1] in ("DOSYA-EUR-1", "DOSYA-USD-1"), row
            assert row[2] == "GM-IBKB"
            assert row[3] == self.__class__.dec_no
            # GB tarihi dd.mm.yyyy
            assert row[4] == "02.04.2026", row[4]
            assert row[8] == "%100"
            assert row[9] == "E"  # tesvik (banka şablonunda E/H)
            assert row[10] == "E"  # taahhut

        # EUR row: DTH/ACH artık IBAN metni
        eur_row = next(r for r in our_rows if r[1] == "DOSYA-EUR-1")
        assert abs(eur_row[5] - 3000.0) < 0.01
        assert eur_row[7] == "TR11 0006 2000 1234 0006 2999 88", eur_row[7]

        usd_row = next(r for r in our_rows if r[1] == "DOSYA-USD-1")
        assert abs(usd_row[5] - 1000.0) < 0.01

        # Başlık satırı boyalı OLMAMALI (banka istemiyor)
        assert ws["A1"].fill.fill_type in (None, "none"), ws["A1"].fill.fill_type
        assert ws["A1"].font.bold is True

        assert toplam_row is not None
        # TOPLAM col F must include our two matches (3000 + 1000 = 4000);
        # parallel test classes may add unrelated matches so use >=.
        assert toplam_row[5] >= 4000.0 - 0.01, toplam_row

        # Beyanname Listesi tesvik/taahhut kolonları
        ws1 = wb["Beyanname Listesi"]
        h1 = [c.value for c in ws1[1]]
        assert "Teşvik" in h1 and "Taahhüt" in h1

        # Eşleştirme Detayı IBKB No + Dosya Ref kolonları
        ws2 = wb["Eşleştirme Detayı"]
        h2 = [c.value for c in ws2[1]]
        assert "IBKB No" in h2 and "Dosya Referansı" in h2
        assert "DTH IBAN" in h2 and "ACH IBAN" in h2

    def test_declaration_view_returns_tesvik_taahhut(self, tokens):
        r = requests.get(f"{API}/declarations", headers=_h(tokens["admin"]),
                         params={"q": self.__class__.dec_no})
        assert r.status_code == 200
        d = next(x for x in r.json() if x["id"] == self.__class__.dec_id)
        assert d.get("tesvik") is True
        assert d.get("taahhut") is True

    def test_audit_has_ibkb_module(self, tokens):
        r = requests.get(f"{API}/audit-logs", headers=_h(tokens["admin"]),
                         params={"modul": "IBKB"})
        assert r.status_code == 200
        logs = r.json()
        assert any(l.get("modul") == "IBKB" for l in logs), "IBKB audit log missing"

    def test_cleanup(self, tokens):
        for mid in self.__class__.match_ids:
            requests.delete(f"{API}/matches/{mid}", headers=_h(tokens["onaylayan"]))
        requests.delete(f"{API}/declarations/{self.__class__.dec_id}",
                        headers=_h(tokens["ihracat"]))
        requests.delete(f"{API}/payments/{self.__class__.pay_eur_id}",
                        headers=_h(tokens["banka"]))
        requests.delete(f"{API}/payments/{self.__class__.pay_usd_id}",
                        headers=_h(tokens["banka"]))


# ---------- Iteration 6: NOTLAR removal, export/check, dashboard extras, backup/restore ----------
class TestIteration6NotesRemoval:
    """BANKA BİLDİRİMİ sayfasında NOTLAR/taahhütname bloğu HİÇ olmamalı ve merged cell bulunmamalı."""

    FORBIDDEN_SUBSTR = [
        "NOTLAR", "notlar",
        "taahhüt ederiz", "taahhut ederiz", "TAAHHÜT EDERIZ", "TAAHHUT EDERIZ",
        "Döviz Dönüşüm Desteği", "Doviz Donusum Destegi",
        "Döviz Dönüşüm Desteği Talebi",
        "kaşe", "kase",
        "imza", "İmza",
    ]

    def test_excel_first_sheet_has_no_notes_block(self, tokens):
        r = requests.get(f"{API}/export/excel", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        import io as _io
        from openpyxl import load_workbook
        wb = load_workbook(_io.BytesIO(r.content))
        assert wb.sheetnames[0] == "BANKA BİLDİRİMİ"
        ws = wb["BANKA BİLDİRİMİ"]

        # (1) No merged cells anywhere on the first sheet
        merged = list(ws.merged_cells.ranges)
        assert merged == [], f"BANKA BİLDİRİMİ should have no merged cells, got: {merged}"

        # (2) No forbidden substrings in any cell value on the first sheet
        offenders = []
        for row in ws.iter_rows(values_only=True):
            for val in row:
                if val is None:
                    continue
                s = str(val)
                for needle in self.FORBIDDEN_SUBSTR:
                    if needle in s:
                        offenders.append((needle, s))
        assert not offenders, f"BANKA BİLDİRİMİ contains forbidden notes text: {offenders[:5]}"

        # (3) The last non-empty row must be TOPLAM (i.e. nothing appended after totals)
        last_data_row = None
        for r_idx in range(ws.max_row, 0, -1):
            row_vals = [ws.cell(row=r_idx, column=c).value for c in range(1, ws.max_column + 1)]
            if any(v not in (None, "") for v in row_vals):
                last_data_row = r_idx
                break
        assert last_data_row is not None
        assert ws.cell(row=last_data_row, column=1).value == "TOPLAM", (
            f"Last row of BANKA BİLDİRİMİ must be TOPLAM, got "
            f"{[ws.cell(row=last_data_row, column=c).value for c in range(1, ws.max_column + 1)]}"
        )

    def test_excel_opens_cleanly_with_openpyxl(self, tokens):
        """.xlsx must be valid — load_workbook must not raise."""
        r = requests.get(f"{API}/export/excel", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        assert "spreadsheet" in r.headers.get("content-type", "").lower()
        import io as _io
        from openpyxl import load_workbook
        wb = load_workbook(_io.BytesIO(r.content))
        # required sheets still there
        for name in ["BANKA BİLDİRİMİ", "Beyanname Listesi", "Eşleştirme Detayı"]:
            assert name in wb.sheetnames, wb.sheetnames

        # Beyanname Listesi has rows (>=1 data row expected in preview DB)
        ws1 = wb["Beyanname Listesi"]
        assert ws1.max_row >= 1
        # Eşleştirme Detayı has header
        ws2 = wb["Eşleştirme Detayı"]
        headers2 = [c.value for c in ws2[1]]
        assert "Beyanname No" in headers2 and "DTH IBAN" in headers2 and "ACH IBAN" in headers2


class TestIteration6ExportCheck:
    def test_export_check_ok(self, tokens):
        r = requests.get(f"{API}/export/check", headers=_h(tokens["admin"]))
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("satir_sayisi", "eksik_sayisi", "eksikler"):
            assert k in d, d
        assert isinstance(d["satir_sayisi"], int)
        assert isinstance(d["eksik_sayisi"], int)
        assert isinstance(d["eksikler"], list)
        # each missing row has beyanname_no / bedel / alanlar list
        for e in d["eksikler"]:
            assert "beyanname_no" in e and "alanlar" in e and isinstance(e["alanlar"], list)

    def test_export_check_requires_auth(self):
        r = requests.get(f"{API}/export/check")
        assert r.status_code == 401


class TestIteration6DashboardExtras:
    def test_dashboard_has_new_cards(self, tokens):
        r = requests.get(f"{API}/dashboard", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        d = r.json()
        for k in ("bu_ay_kapatilan", "bu_ay_islem_sayi",
                  "destek_bekleyen_sayi", "destek_bekleyen_tutar"):
            assert k in d, f"missing dashboard key {k}: keys={list(d.keys())}"
        assert isinstance(d["bu_ay_kapatilan"], dict)
        assert isinstance(d["bu_ay_islem_sayi"], int)
        assert isinstance(d["destek_bekleyen_sayi"], int)
        assert isinstance(d["destek_bekleyen_tutar"], dict)
        # legacy keys still present
        for k in ("acik", "kismi", "kapali", "acik_tutar", "bedel_bakiye",
                  "yaklasan", "gecmis", "son_hareketler"):
            assert k in d


class TestIteration6Backup:
    """/api/backup indir + /api/backup/restore geri yükleme (admin-only)."""

    backup_bytes = None

    def test_backup_rbac_non_admin_forbidden(self, tokens):
        for role in ("ihracat", "banka", "onaylayan", "viewer"):
            r = requests.get(f"{API}/backup", headers=_h(tokens[role]))
            assert r.status_code == 403, f"{role} got {r.status_code}"

    def test_backup_download_json(self, tokens):
        r = requests.get(f"{API}/backup", headers=_h(tokens["admin"]))
        assert r.status_code == 200, r.text
        assert "application/json" in r.headers.get("content-type", "").lower()
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        import json as _json
        data = _json.loads(r.content.decode("utf-8"))
        assert "_meta" in data
        for col in ("users", "declarations", "payments", "matches", "audit_logs"):
            assert col in data, f"missing collection {col} in backup"
            assert isinstance(data[col], list)
        # meta info
        assert data["_meta"].get("olusturan") == "admin@ihracat.com"
        self.__class__.backup_bytes = r.content

    def test_restore_rbac_non_admin_forbidden(self, tokens):
        # Use a minimal fake backup for rbac (no real restore should occur since 403 first)
        files = {"file": ("dummy.json", b'{"users": []}', "application/json")}
        for role in ("ihracat", "banka", "onaylayan", "viewer"):
            hdr = {"Authorization": f"Bearer {tokens[role]}"}
            r = requests.post(f"{API}/backup/restore?mode=merge",
                              headers=hdr, files=files)
            assert r.status_code == 403, f"{role} got {r.status_code}"

    def test_restore_invalid_file_400(self, tokens):
        hdr = {"Authorization": f"Bearer {tokens['admin']}"}
        files = {"file": ("bad.json", b"not-json-content", "application/json")}
        r = requests.post(f"{API}/backup/restore?mode=merge", headers=hdr, files=files)
        assert r.status_code == 400, r.text

    def test_restore_non_backup_json_400(self, tokens):
        hdr = {"Authorization": f"Bearer {tokens['admin']}"}
        files = {"file": ("noop.json", b'{"foo": "bar"}', "application/json")}
        r = requests.post(f"{API}/backup/restore?mode=merge", headers=hdr, files=files)
        assert r.status_code == 400

    def test_restore_merge_roundtrip(self, tokens):
        """Download → merge-restore the same backup. Should be idempotent and 200."""
        assert self.__class__.backup_bytes, "backup was not captured earlier"
        # count declarations before
        before = requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
        n_before = len(before)

        hdr = {"Authorization": f"Bearer {tokens['admin']}"}
        files = {"file": ("backup.json", self.__class__.backup_bytes, "application/json")}
        r = requests.post(f"{API}/backup/restore?mode=merge", headers=hdr, files=files)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("mode") == "merge"
        assert "yuklenen" in body
        for col in ("users", "declarations", "payments", "matches", "audit_logs"):
            assert col in body["yuklenen"]

        # After merge with identical data, declaration count should not decrease
        after = requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
        assert len(after) >= n_before, (n_before, len(after))

    def test_backup_audit_log(self, tokens):
        r = requests.get(f"{API}/audit-logs", headers=_h(tokens["admin"]),
                         params={"modul": "Yedek"})
        assert r.status_code == 200
        logs = r.json()
        assert any(l.get("islem") == "INDIR" for l in logs), "backup INDIR audit log missing"
        assert any(l.get("islem") == "GERI_YUKLE" for l in logs), "restore audit log missing"

