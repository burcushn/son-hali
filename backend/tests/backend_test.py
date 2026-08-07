"""Backend tests for İhracat Bedel Kapatma sistemi."""
import os
import io
from pathlib import Path
from datetime import datetime, timedelta

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin":    ("admin@ihracat.com",   "Admin1234!"),
    "ihracat":  ("ihracat@ihracat.com", "Test1234!"),
    "banka":    ("banka@ihracat.com",   "Test1234!"),
    "onaylayan":("sef@ihracat.com",     "Test1234!"),
    "viewer":   ("viewer@ihracat.com",  "Test1234!"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "token" in data and data["token"], "token missing"
    return data["token"], data


@pytest.fixture(scope="module")
def tokens():
    return {role: _login(e, p)[0] for role, (e, p) in CREDS.items()}


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ----------- auth -----------
class TestAuth:
    def test_login_all_roles(self):
        for role, (e, p) in CREDS.items():
            tok, data = _login(e, p)
            assert data["role"] in ("admin", "ihracat", "banka", "onaylayan", "goruntuleyici")
            assert data["email"] == e

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@ihracat.com", "password": "wrongxxx"})
        assert r.status_code == 401

    def test_me(self, tokens):
        r = requests.get(f"{API}/auth/me", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_me_unauthorized(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401


# ----------- rbac + declarations -----------
class TestDeclarations:
    beyanname_no = f"TEST_BEY_{int(datetime.now().timestamp())}"
    tescil_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    created_id = None

    def test_ihracat_can_create(self, tokens):
        payload = {
            "beyanname_no": self.__class__.beyanname_no,
            "tescil_tarihi": self.tescil_date,
            "ihracatci": "TEST İhracatçı A.Ş.",
            "alici": "TEST Alıcı Ltd.",
            "ulke": "Almanya",
            "doviz": "EUR",
            "tutar": 10000.0,
            "fatura_no": "TEST-INV-1",
        }
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["beyanname_no"] == self.__class__.beyanname_no
        assert d["durum"] == "ACIK"
        assert d["kalan"] == 10000.0
        # son_kapatma_tarihi = tescil + 180 gün
        exp = (datetime.strptime(self.tescil_date, "%Y-%m-%d") + timedelta(days=180)).strftime("%Y-%m-%d")
        assert d["son_kapatma_tarihi"] == exp
        self.__class__.created_id = d["id"]

    def test_duplicate_beyanname_no(self, tokens):
        payload = {
            "beyanname_no": self.__class__.beyanname_no,
            "tescil_tarihi": self.tescil_date,
            "ihracatci": "x", "alici": "y", "ulke": "Z", "doviz": "EUR", "tutar": 100,
        }
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json=payload)
        assert r.status_code == 400
        assert "zaten" in r.text.lower()

    def test_banka_cannot_create_declaration(self, tokens):
        r = requests.post(f"{API}/declarations", headers=_h(tokens["banka"]), json={
            "beyanname_no": "NO_ACCESS", "tescil_tarihi": "2025-01-01",
            "ihracatci": "x", "alici": "y", "ulke": "Z", "doviz": "USD", "tutar": 1,
        })
        assert r.status_code == 403

    def test_viewer_cannot_create_declaration(self, tokens):
        r = requests.post(f"{API}/declarations", headers=_h(tokens["viewer"]), json={
            "beyanname_no": "NO_ACCESS2", "tescil_tarihi": "2025-01-01",
            "ihracatci": "x", "alici": "y", "ulke": "Z", "doviz": "USD", "tutar": 1,
        })
        assert r.status_code == 403

    def test_all_roles_can_list(self, tokens):
        for role in ["admin", "ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.get(f"{API}/declarations", headers=_h(tokens[role]))
            assert r.status_code == 200, f"{role} list failed"
            assert isinstance(r.json(), list)


# ----------- payments -----------
class TestPayments:
    created_id = None

    def test_banka_can_create(self, tokens):
        payload = {
            "banka": "TEST Bank", "gonderen": "TEST Buyer GmbH",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "doviz": "EUR", "tutar": 15000.0, "aciklama": "TEST payment",
        }
        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json=payload)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["tutar"] == 15000.0
        assert p["bakiye"] == 15000.0
        assert p["durum"] == "KULLANILMADI"
        self.__class__.created_id = p["id"]

    def test_ihracat_cannot_create_payment(self, tokens):
        r = requests.post(f"{API}/payments", headers=_h(tokens["ihracat"]), json={
            "banka": "x", "gonderen": "y", "tarih": "2025-01-01", "doviz": "USD", "tutar": 1,
        })
        assert r.status_code == 403

    def test_onaylayan_cannot_create_payment(self, tokens):
        r = requests.post(f"{API}/payments", headers=_h(tokens["onaylayan"]), json={
            "banka": "x", "gonderen": "y", "tarih": "2025-01-01", "doviz": "USD", "tutar": 1,
        })
        assert r.status_code == 403

    def test_all_roles_can_list_payments(self, tokens):
        for role in ["admin", "ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.get(f"{API}/payments", headers=_h(tokens[role]))
            assert r.status_code == 200


# ----------- matches (needs same currency setup: EUR / EUR) -----------
class TestMatching:
    dec_id = None
    pay_id = None
    match_id = None
    dec_no = f"TEST_MATCH_{int(datetime.now().timestamp())}"

    def test_setup(self, tokens):
        tescil = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json={
            "beyanname_no": self.__class__.dec_no, "tescil_tarihi": tescil,
            "ihracatci": "TEST", "alici": "TEST", "ulke": "DE", "doviz": "EUR", "tutar": 5000.0,
        })
        assert r.status_code == 200
        self.__class__.dec_id = r.json()["id"]

        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "TEST", "gonderen": "TEST",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "doviz": "EUR", "tutar": 8000.0,
        })
        assert r.status_code == 200
        self.__class__.pay_id = r.json()["id"]

    def test_ihracat_cannot_match(self, tokens):
        r = requests.post(f"{API}/matches", headers=_h(tokens["ihracat"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 100, "kur": 1.0,
        })
        assert r.status_code == 403

    def test_onaylayan_partial_match_same_currency(self, tokens):
        # kur manuel = 1.0 same currency
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 2000.0, "kur": 1.0,
        })
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["kapatilan_tutar"] == 2000.0
        assert m["bedel_kullanilan"] == 2000.0
        self.__class__.match_id = m["id"]

        # verify declaration went to KISMI, kapatilan=2000
        d = requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
        dd = next(x for x in d if x["id"] == self.__class__.dec_id)
        assert dd["durum"] == "KISMI"
        assert dd["kapatilan"] == 2000.0
        assert dd["kalan"] == 3000.0

        # verify payment bakiye
        p = requests.get(f"{API}/payments", headers=_h(tokens["admin"])).json()
        pp = next(x for x in p if x["id"] == self.__class__.pay_id)
        assert pp["kullanilan"] == 2000.0
        assert pp["bakiye"] == 6000.0
        assert pp["durum"] == "KISMI"

    def test_match_over_declaration_kalan_fails(self, tokens):
        # kalan = 3000, try 4000
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 4000.0, "kur": 1.0,
        })
        assert r.status_code == 400
        assert "kalan" in r.text.lower() or "aş" in r.text.lower()

    def test_match_over_payment_bakiye_fails(self, tokens):
        # kalan dec = 3000, ok; but let payment bakiye = 6000; with kur=0.1, need 30000
        r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
            "declaration_id": self.__class__.dec_id, "payment_id": self.__class__.pay_id,
            "kapatilan_tutar": 3000.0, "kur": 0.1,
        })
        assert r.status_code == 400
        assert "bakiye" in r.text.lower() or "yetersiz" in r.text.lower()

    def test_delete_declaration_with_match_blocked(self, tokens):
        r = requests.delete(f"{API}/declarations/{self.__class__.dec_id}",
                            headers=_h(tokens["ihracat"]))
        assert r.status_code == 400

    def test_delete_payment_with_match_blocked(self, tokens):
        r = requests.delete(f"{API}/payments/{self.__class__.pay_id}",
                            headers=_h(tokens["banka"]))
        assert r.status_code == 400

    def test_update_match(self, tokens):
        # PUT uses query param
        r = requests.put(f"{API}/matches/{self.__class__.match_id}?kapatilan_tutar=1500",
                         headers=_h(tokens["onaylayan"]))
        assert r.status_code == 200, r.text
        d = requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
        dd = next(x for x in d if x["id"] == self.__class__.dec_id)
        assert dd["kapatilan"] == 1500.0

    def test_delete_match_restores(self, tokens):
        r = requests.delete(f"{API}/matches/{self.__class__.match_id}",
                            headers=_h(tokens["onaylayan"]))
        assert r.status_code == 200
        d = requests.get(f"{API}/declarations", headers=_h(tokens["admin"])).json()
        dd = next(x for x in d if x["id"] == self.__class__.dec_id)
        assert dd["kapatilan"] == 0.0
        assert dd["durum"] == "ACIK"

    def test_cleanup(self, tokens):
        requests.delete(f"{API}/declarations/{self.__class__.dec_id}", headers=_h(tokens["ihracat"]))
        requests.delete(f"{API}/payments/{self.__class__.pay_id}", headers=_h(tokens["banka"]))


# ----------- cross currency (TCMB) -----------
class TestRates:
    def test_rates_endpoint(self, tokens):
        r = requests.get(f"{API}/rates?from_cur=USD&to_cur=EUR&date=2025-06-02",
                         headers=_h(tokens["admin"]))
        # can fail if TCMB unreachable -> 503; treat both acceptable
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            data = r.json()
            assert data["kaynak"] == "TCMB"
            assert data["kur"] > 0

    def test_cross_currency_match_uses_tcmb(self, tokens):
        dec_no = f"TEST_CROSS_{int(datetime.now().timestamp())}"
        tescil = "2025-06-02"  # weekday
        r = requests.post(f"{API}/declarations", headers=_h(tokens["ihracat"]), json={
            "beyanname_no": dec_no, "tescil_tarihi": tescil,
            "ihracatci": "T", "alici": "T", "ulke": "DE", "doviz": "EUR", "tutar": 1000.0,
        })
        assert r.status_code == 200
        did = r.json()["id"]

        r = requests.post(f"{API}/payments", headers=_h(tokens["banka"]), json={
            "banka": "T", "gonderen": "T", "tarih": "2025-06-02", "doviz": "USD", "tutar": 5000.0,
        })
        assert r.status_code == 200
        pid = r.json()["id"]

        try:
            # No kur -> should fetch from TCMB
            r = requests.post(f"{API}/matches", headers=_h(tokens["onaylayan"]), json={
                "declaration_id": did, "payment_id": pid, "kapatilan_tutar": 100.0,
            })
            assert r.status_code in (200, 503), r.text
            if r.status_code == 200:
                m = r.json()
                assert m["kur_kaynak"] == "TCMB"
                assert m["bedel_kullanilan"] > 0
                requests.delete(f"{API}/matches/{m['id']}", headers=_h(tokens["onaylayan"]))
        finally:
            requests.delete(f"{API}/declarations/{did}", headers=_h(tokens["ihracat"]))
            requests.delete(f"{API}/payments/{pid}", headers=_h(tokens["banka"]))


# ----------- dashboard / audit / reports -----------
class TestDashboard:
    def test_dashboard(self, tokens):
        r = requests.get(f"{API}/dashboard", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        d = r.json()
        for k in ["acik", "kismi", "kapali", "acik_tutar", "bedel_bakiye",
                  "yaklasan", "gecmis", "son_hareketler"]:
            assert k in d, f"missing {k}"

    def test_audit_logs(self, tokens):
        r = requests.get(f"{API}/audit-logs", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reports_summary(self, tokens):
        r = requests.get(f"{API}/reports/summary", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        d = r.json()
        assert "doviz" in d and "ulke" in d and "ay" in d

    def test_excel_export(self, tokens):
        r = requests.get(f"{API}/export/excel", headers=_h(tokens["admin"]))
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml" in ct or "excel" in ct.lower()
        assert len(r.content) > 100


# ----------- users -----------
class TestUsers:
    def test_non_admin_cannot_create_user(self, tokens):
        for role in ["ihracat", "banka", "onaylayan", "viewer"]:
            r = requests.post(f"{API}/users", headers=_h(tokens[role]), json={
                "email": f"nope_{role}@test.com", "name": "x", "role": "viewer", "password": "P@ss12345",
            })
            assert r.status_code == 403, f"{role} should be 403"

    def test_admin_can_create_and_update_user(self, tokens):
        email = f"test_new_{int(datetime.now().timestamp())}@ihracat.com"
        r = requests.post(f"{API}/users", headers=_h(tokens["admin"]), json={
            "email": email, "name": "TEST New", "role": "goruntuleyici", "password": "P@ssword12!",
        })
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        # update role
        r = requests.put(f"{API}/users/{uid}", headers=_h(tokens["admin"]), json={"role": "banka"})
        assert r.status_code == 200
        assert r.json()["role"] == "banka"
        # cleanup
        r = requests.delete(f"{API}/users/{uid}", headers=_h(tokens["admin"]))
        assert r.status_code == 200
