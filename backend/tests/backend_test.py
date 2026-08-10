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
        ws = wb.active
        headers = [c.value for c in ws[1]]
        expected = ["Beyanname No", "Açılış Tarihi", "Kapanış Tarihi",
                    "Son Kapatma Tarihi (180 gün)", "İthalatçı",
                    "Gümrük Müdürlüğü No", "IBKB Belgesi Durumu",
                    "Destek Ödemesi (%3)", "Destek Durumu"]
        for e in expected:
            assert e in headers, f"missing excel header: {e}"


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

