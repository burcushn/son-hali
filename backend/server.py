from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import io
import logging
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from models import (
    User, UserCreate, UserUpdate, LoginInput, Declaration, DeclarationInput,
    Payment, PaymentInput, Match, MatchInput, ROLES, ROLE_LABELS, utcnow_iso,
)
import tcmb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api = APIRouter(prefix="/api")

JWT_ALG = "HS256"


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def create_access_token(uid: str, email: str) -> str:
    return jwt.encode(
        {"sub": uid, "email": email, "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(hours=12)},
        os.environ["JWT_SECRET"], algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Oturum bulunamadı")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Oturum süresi doldu")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz oturum")
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user or not user.get("active", True):
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı veya pasif")
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return user


def require(*roles):
    async def dep(user: dict = Depends(get_current_user)):
        if user["role"] != "admin" and user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
        return user
    return dep


async def log_action(user: dict, modul: str, islem: str, aciklama: str, ref: str = ""):
    await db.audit_logs.insert_one({
        "modul": modul, "islem": islem, "aciklama": aciklama, "ref": ref,
        "kullanici_ad": user.get("name", ""), "kullanici_rol": user.get("role", ""),
        "tarih": utcnow_iso(),
    })


# ---------------- helpers ----------------

def declaration_view(doc: dict) -> dict:
    d = Declaration.from_mongo(doc).model_dump()
    d["kalan"] = round(d["tutar"] - d["kapatilan"], 2)
    try:
        son = datetime.strptime(d["tescil_tarihi"][:10], "%Y-%m-%d") + timedelta(days=180)
        d["son_kapatma_tarihi"] = son.strftime("%Y-%m-%d")
        kalan_gun = (son.date() - datetime.now().date()).days
    except Exception:
        kalan_gun = None
    d["kalan_gun"] = kalan_gun
    if d["durum"] == "KAPALI":
        d["sure_durum"] = "TAMAM"
    elif kalan_gun is None:
        d["sure_durum"] = "NORMAL"
    elif kalan_gun < 0:
        d["sure_durum"] = "GECMIS"
    elif kalan_gun <= 30:
        d["sure_durum"] = "YAKLASAN"
    else:
        d["sure_durum"] = "NORMAL"
    return d


def payment_view(doc: dict) -> dict:
    p = Payment.from_mongo(doc).model_dump()
    p["bakiye"] = round(p["tutar"] - p["kullanilan"], 2)
    return p


def dstatus(tutar: float, kapatilan: float) -> str:
    if kapatilan <= 0.004:
        return "ACIK"
    if kapatilan >= tutar - 0.01:
        return "KAPALI"
    return "KISMI"


def pstatus(tutar: float, kullanilan: float) -> str:
    if kullanilan <= 0.004:
        return "KULLANILMADI"
    if kullanilan >= tutar - 0.01:
        return "TUKENDI"
    return "KISMI"


async def recalc_declaration(did: str):
    ms = await db.matches.find({"declaration_id": did}).to_list(2000)
    total = round(sum(m["kapatilan_tutar"] for m in ms), 2)
    doc = await db.declarations.find_one({"_id": ObjectId(did)})
    if doc:
        await db.declarations.update_one({"_id": ObjectId(did)},
            {"$set": {"kapatilan": total, "durum": dstatus(doc["tutar"], total)}})


async def recalc_payment(pid: str):
    ms = await db.matches.find({"payment_id": pid}).to_list(2000)
    total = round(sum(m["bedel_kullanilan"] for m in ms), 2)
    doc = await db.payments.find_one({"_id": ObjectId(pid)})
    if doc:
        await db.payments.update_one({"_id": ObjectId(pid)},
            {"$set": {"kullanilan": total, "durum": pstatus(doc["tutar"], total)}})


# ---------------- auth ----------------
@api.post("/auth/login")
async def login(body: LoginInput, response: Response):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Hesabınız pasif durumda")
    token = create_access_token(str(user["_id"]), email)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                        samesite="none", max_age=43200, path="/")
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return {**User.from_mongo(user).model_dump(), "token": token}


@api.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return User.from_mongo(user).model_dump()


# ---------------- users ----------------
@api.get("/users")
async def list_users(user: dict = Depends(require())):
    docs = await db.users.find({}, {"password_hash": 0}).sort("created_at", 1).to_list(500)
    return [User.from_mongo(d).model_dump() for d in docs]


@api.post("/users")
async def create_user(body: UserCreate, user: dict = Depends(require())):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Geçersiz rol")
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")
    doc = {"email": email, "name": body.name, "role": body.role, "active": True,
           "password_hash": hash_password(body.password), "created_at": utcnow_iso()}
    res = await db.users.insert_one(doc)
    await log_action(user, "Kullanıcı", "EKLE", f"{body.name} ({ROLE_LABELS[body.role]}) eklendi", str(res.inserted_id))
    doc["_id"] = res.inserted_id
    return User.from_mongo(doc).model_dump()


@api.put("/users/{uid}")
async def update_user(uid: str, body: UserUpdate, user: dict = Depends(require())):
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items() if k != "password"}
    if body.password:
        upd["password_hash"] = hash_password(body.password)
    if not upd:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
    await db.users.update_one({"_id": ObjectId(uid)}, {"$set": upd})
    await log_action(user, "Kullanıcı", "GUNCELLE", f"Kullanıcı güncellendi", uid)
    doc = await db.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
    return User.from_mongo(doc).model_dump()


@api.delete("/users/{uid}")
async def delete_user(uid: str, user: dict = Depends(require())):
    if uid == user["_id"]:
        raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz")
    await db.users.delete_one({"_id": ObjectId(uid)})
    await log_action(user, "Kullanıcı", "SIL", "Kullanıcı silindi", uid)
    return {"ok": True}


# ---------------- declarations ----------------
@api.get("/declarations")
async def list_declarations(durum: str = "", q: str = "", sure: str = "",
                            user: dict = Depends(get_current_user)):
    query = {}
    if durum:
        query["durum"] = durum
    if q:
        query["$or"] = [{"beyanname_no": {"$regex": q, "$options": "i"}},
                        {"alici": {"$regex": q, "$options": "i"}},
                        {"ihracatci": {"$regex": q, "$options": "i"}},
                        {"fatura_no": {"$regex": q, "$options": "i"}}]
    docs = await db.declarations.find(query).sort("tescil_tarihi", -1).to_list(2000)
    items = [declaration_view(d) for d in docs]
    if sure:
        items = [i for i in items if i["sure_durum"] == sure]
    return items


@api.post("/declarations")
async def create_declaration(body: DeclarationInput, user: dict = Depends(require("ihracat"))):
    if await db.declarations.find_one({"beyanname_no": body.beyanname_no.strip()}):
        raise HTTPException(status_code=400, detail="Bu beyanname numarası zaten kayıtlı")
    d = Declaration(**body.model_dump(), created_by=user["name"])
    d.beyanname_no = d.beyanname_no.strip()
    d.durum = "ACIK"
    res = await db.declarations.insert_one(d.to_mongo())
    await log_action(user, "Beyanname", "EKLE",
                     f"{d.beyanname_no} / {d.tutar} {d.doviz} eklendi", str(res.inserted_id))
    doc = await db.declarations.find_one({"_id": res.inserted_id})
    return declaration_view(doc)


@api.put("/declarations/{did}")
async def update_declaration(did: str, body: DeclarationInput, user: dict = Depends(require("ihracat"))):
    doc = await db.declarations.find_one({"_id": ObjectId(did)})
    if not doc:
        raise HTTPException(status_code=404, detail="Beyanname bulunamadı")
    if body.tutar < doc.get("kapatilan", 0) - 0.01:
        raise HTTPException(status_code=400, detail="Yeni tutar, kapatılan tutardan küçük olamaz")
    upd = body.model_dump()
    await db.declarations.update_one({"_id": ObjectId(did)},
        {"$set": {**upd, "durum": dstatus(body.tutar, doc.get("kapatilan", 0))}})
    await log_action(user, "Beyanname", "GUNCELLE", f"{body.beyanname_no} güncellendi", did)
    return declaration_view(await db.declarations.find_one({"_id": ObjectId(did)}))


@api.delete("/declarations/{did}")
async def delete_declaration(did: str, user: dict = Depends(require("ihracat"))):
    if await db.matches.find_one({"declaration_id": did}):
        raise HTTPException(status_code=400, detail="Eşleştirmesi olan beyanname silinemez. Önce eşleştirmeleri geri alın.")
    doc = await db.declarations.find_one({"_id": ObjectId(did)})
    await db.declarations.delete_one({"_id": ObjectId(did)})
    await log_action(user, "Beyanname", "SIL", f"{doc.get('beyanname_no','')} silindi", did)
    return {"ok": True}


# ---------------- payments ----------------
@api.get("/payments")
async def list_payments(durum: str = "", q: str = "", only_available: bool = False,
                        user: dict = Depends(get_current_user)):
    query = {}
    if durum:
        query["durum"] = durum
    if q:
        query["$or"] = [{"gonderen": {"$regex": q, "$options": "i"}},
                        {"banka": {"$regex": q, "$options": "i"}},
                        {"aciklama": {"$regex": q, "$options": "i"}}]
    docs = await db.payments.find(query).sort("tarih", -1).to_list(2000)
    items = [payment_view(d) for d in docs]
    if only_available:
        items = [i for i in items if i["bakiye"] > 0.01]
    return items


@api.post("/payments")
async def create_payment(body: PaymentInput, user: dict = Depends(require("banka"))):
    p = Payment(**body.model_dump(), created_by=user["name"])
    res = await db.payments.insert_one(p.to_mongo())
    await log_action(user, "Bedel", "EKLE",
                     f"{p.gonderen} / {p.tutar} {p.doviz} ({p.banka}) eklendi", str(res.inserted_id))
    return payment_view(await db.payments.find_one({"_id": res.inserted_id}))


@api.put("/payments/{pid}")
async def update_payment(pid: str, body: PaymentInput, user: dict = Depends(require("banka"))):
    doc = await db.payments.find_one({"_id": ObjectId(pid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Bedel bulunamadı")
    if body.tutar < doc.get("kullanilan", 0) - 0.01:
        raise HTTPException(status_code=400, detail="Yeni tutar, kullanılan tutardan küçük olamaz")
    await db.payments.update_one({"_id": ObjectId(pid)},
        {"$set": {**body.model_dump(), "durum": pstatus(body.tutar, doc.get("kullanilan", 0))}})
    await log_action(user, "Bedel", "GUNCELLE", f"{body.gonderen} bedeli güncellendi", pid)
    return payment_view(await db.payments.find_one({"_id": ObjectId(pid)}))


@api.delete("/payments/{pid}")
async def delete_payment(pid: str, user: dict = Depends(require("banka"))):
    if await db.matches.find_one({"payment_id": pid}):
        raise HTTPException(status_code=400, detail="Eşleştirmesi olan bedel silinemez. Önce eşleştirmeleri geri alın.")
    doc = await db.payments.find_one({"_id": ObjectId(pid)})
    await db.payments.delete_one({"_id": ObjectId(pid)})
    await log_action(user, "Bedel", "SIL", f"{doc.get('gonderen','')} bedeli silindi", pid)
    return {"ok": True}


# ---------------- rates ----------------
@api.get("/rates")
async def rates(date: str = "", from_cur: str = "USD", to_cur: str = "EUR",
                user: dict = Depends(get_current_user)):
    date = date or datetime.now().strftime("%Y-%m-%d")
    kur, kaynak, kur_tarihi = await tcmb.cross_rate(from_cur, to_cur, date)
    if kur is None:
        raise HTTPException(status_code=503, detail="TCMB kuru alınamadı, kuru manuel giriniz")
    return {"kur": kur, "kaynak": kaynak, "kur_tarihi": kur_tarihi,
            "from": from_cur.upper(), "to": to_cur.upper()}


# ---------------- matching ----------------
@api.get("/declarations/{did}/matches")
async def declaration_matches(did: str, user: dict = Depends(get_current_user)):
    ms = await db.matches.find({"declaration_id": did}).sort("tarih", -1).to_list(500)
    out = []
    for m in ms:
        p = await db.payments.find_one({"_id": ObjectId(m["payment_id"])})
        item = Match.from_mongo(m).model_dump()
        item["payment"] = payment_view(p) if p else None
        out.append(item)
    return out


@api.post("/matches")
async def create_match(body: MatchInput, user: dict = Depends(require("onaylayan"))):
    d = await db.declarations.find_one({"_id": ObjectId(body.declaration_id)})
    p = await db.payments.find_one({"_id": ObjectId(body.payment_id)})
    if not d or not p:
        raise HTTPException(status_code=404, detail="Beyanname veya bedel bulunamadı")
    if body.kapatilan_tutar <= 0:
        raise HTTPException(status_code=400, detail="Kapatılacak tutar sıfırdan büyük olmalı")

    d_kalan = round(d["tutar"] - d.get("kapatilan", 0), 2)
    if body.kapatilan_tutar > d_kalan + 0.01:
        raise HTTPException(status_code=400,
            detail=f"Beyanname kalan tutarı aşılamaz. Kalan: {d_kalan:,.2f} {d['doviz']}")

    if body.kur:
        kur, kaynak, kur_tarihi = float(body.kur), "MANUEL", d["tescil_tarihi"][:10]
    else:
        kur, kaynak, kur_tarihi = await tcmb.cross_rate(p["doviz"], d["doviz"], d["tescil_tarihi"])
        if kur is None:
            raise HTTPException(status_code=503, detail="TCMB kuru alınamadı, kuru manuel giriniz")

    bedel_kullanilan = round(body.kapatilan_tutar / kur, 2)
    p_bakiye = round(p["tutar"] - p.get("kullanilan", 0), 2)
    if bedel_kullanilan > p_bakiye + 0.01:
        raise HTTPException(status_code=400,
            detail=f"Bedel bakiyesi yetersiz. Bakiye: {p_bakiye:,.2f} {p['doviz']} "
                   f"(gereken {bedel_kullanilan:,.2f} {p['doviz']})")

    m = Match(declaration_id=body.declaration_id, payment_id=body.payment_id,
              kapatilan_tutar=round(body.kapatilan_tutar, 2), bedel_kullanilan=bedel_kullanilan,
              kur=kur, kur_kaynak=kaynak, kullanici=user["_id"], kullanici_ad=user["name"])
    res = await db.matches.insert_one(m.to_mongo())
    await recalc_declaration(body.declaration_id)
    await recalc_payment(body.payment_id)
    await log_action(user, "Eşleştirme", "EKLE",
        f"{d['beyanname_no']} beyannamesi {body.kapatilan_tutar:,.2f} {d['doviz']} kapatıldı "
        f"({bedel_kullanilan:,.2f} {p['doviz']}, kur {kur} / {kaynak} {kur_tarihi})", str(res.inserted_id))
    return Match.from_mongo(await db.matches.find_one({"_id": res.inserted_id})).model_dump()


@api.put("/matches/{mid}")
async def update_match(mid: str, kapatilan_tutar: float, user: dict = Depends(require("onaylayan"))):
    m = await db.matches.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Eşleştirme bulunamadı")
    d = await db.declarations.find_one({"_id": ObjectId(m["declaration_id"])})
    p = await db.payments.find_one({"_id": ObjectId(m["payment_id"])})
    d_kalan = round(d["tutar"] - d.get("kapatilan", 0) + m["kapatilan_tutar"], 2)
    if kapatilan_tutar > d_kalan + 0.01 or kapatilan_tutar <= 0:
        raise HTTPException(status_code=400, detail=f"Geçersiz tutar. Üst limit: {d_kalan:,.2f} {d['doviz']}")
    yeni_bedel = round(kapatilan_tutar / m["kur"], 2)
    p_bakiye = round(p["tutar"] - p.get("kullanilan", 0) + m["bedel_kullanilan"], 2)
    if yeni_bedel > p_bakiye + 0.01:
        raise HTTPException(status_code=400, detail=f"Bedel bakiyesi yetersiz. Üst limit: {p_bakiye:,.2f} {p['doviz']}")
    await db.matches.update_one({"_id": ObjectId(mid)},
        {"$set": {"kapatilan_tutar": round(kapatilan_tutar, 2), "bedel_kullanilan": yeni_bedel}})
    await recalc_declaration(m["declaration_id"])
    await recalc_payment(m["payment_id"])
    await log_action(user, "Eşleştirme", "GUNCELLE",
        f"{d['beyanname_no']} eşleştirmesi {kapatilan_tutar:,.2f} {d['doviz']} olarak güncellendi", mid)
    return {"ok": True}


@api.delete("/matches/{mid}")
async def delete_match(mid: str, user: dict = Depends(require("onaylayan"))):
    m = await db.matches.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Eşleştirme bulunamadı")
    d = await db.declarations.find_one({"_id": ObjectId(m["declaration_id"])})
    await db.matches.delete_one({"_id": ObjectId(mid)})
    await recalc_declaration(m["declaration_id"])
    await recalc_payment(m["payment_id"])
    await log_action(user, "Eşleştirme", "GERI_AL",
        f"{d.get('beyanname_no','')} eşleştirmesi geri alındı ({m['kapatilan_tutar']:,.2f})", mid)
    return {"ok": True}


# ---------------- dashboard / audit ----------------
@api.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    decs = [declaration_view(d) for d in await db.declarations.find({}).to_list(5000)]
    pays = [payment_view(p) for p in await db.payments.find({}).to_list(5000)]

    def group(items, key, val):
        out = {}
        for i in items:
            out[i[key]] = round(out.get(i[key], 0) + i[val], 2)
        return out

    open_decs = [d for d in decs if d["durum"] != "KAPALI"]
    logs = await db.audit_logs.find({}).sort("tarih", -1).to_list(12)
    return {
        "acik": len([d for d in decs if d["durum"] == "ACIK"]),
        "kismi": len([d for d in decs if d["durum"] == "KISMI"]),
        "kapali": len([d for d in decs if d["durum"] == "KAPALI"]),
        "toplam": len(decs),
        "acik_tutar": group(open_decs, "doviz", "kalan"),
        "bedel_bakiye": group([p for p in pays if p["bakiye"] > 0.01], "doviz", "bakiye"),
        "yaklasan": sorted([d for d in decs if d["sure_durum"] == "YAKLASAN"], key=lambda x: x["kalan_gun"])[:10],
        "gecmis": sorted([d for d in decs if d["sure_durum"] == "GECMIS"], key=lambda x: x["kalan_gun"])[:10],
        "yaklasan_sayi": len([d for d in decs if d["sure_durum"] == "YAKLASAN"]),
        "gecmis_sayi": len([d for d in decs if d["sure_durum"] == "GECMIS"]),
        "son_hareketler": [{**{k: v for k, v in l.items() if k != "_id"}} for l in logs],
    }


@api.get("/audit-logs")
async def audit_logs(modul: str = "", limit: int = 200, user: dict = Depends(get_current_user)):
    query = {"modul": modul} if modul else {}
    logs = await db.audit_logs.find(query).sort("tarih", -1).to_list(limit)
    return [{k: v for k, v in l.items() if k != "_id"} for l in logs]


# ---------------- excel export ----------------
HDR_FILL = PatternFill("solid", fgColor="4338CA")


def _style(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = 20
    ws.freeze_panes = "A2"


@api.get("/export/excel")
async def export_excel(durum: str = "", user: dict = Depends(get_current_user)):
    query = {"durum": durum} if durum else {}
    decs = await db.declarations.find(query).sort("tescil_tarihi", -1).to_list(5000)
    wb = Workbook()
    ws = wb.active
    ws.title = "Banka Bildirimi"
    headers = ["Beyanname No", "Tescil Tarihi", "Son Kapatma Tarihi", "İhracatçı", "Alıcı",
               "Ülke", "Fatura No", "Döviz", "Beyanname Tutarı", "Kapatılan", "Kalan",
               "Durum", "Süre Durumu"]
    ws.append(headers)
    for d in decs:
        v = declaration_view(d)
        ws.append([v["beyanname_no"], v["tescil_tarihi"], v["son_kapatma_tarihi"], v["ihracatci"],
                   v["alici"], v["ulke"], v["fatura_no"], v["doviz"], v["tutar"], v["kapatilan"],
                   v["kalan"], v["durum"], v["sure_durum"]])
    _style(ws, len(headers))

    ws2 = wb.create_sheet("Eşleştirme Detayı")
    h2 = ["Beyanname No", "Bedel Gönderen", "Banka", "Bedel Tarihi", "Bedel Dövizi",
          "Kullanılan Bedel", "Kur", "Kur Kaynağı", "Kapatılan (Beyanname Dövizi)",
          "Beyanname Dövizi", "İşlem Tarihi", "İşlemi Yapan"]
    ws2.append(h2)
    for m in await db.matches.find({}).sort("tarih", -1).to_list(5000):
        d = await db.declarations.find_one({"_id": ObjectId(m["declaration_id"])})
        p = await db.payments.find_one({"_id": ObjectId(m["payment_id"])})
        if not d or not p:
            continue
        ws2.append([d["beyanname_no"], p["gonderen"], p["banka"], p["tarih"], p["doviz"],
                    m["bedel_kullanilan"], m["kur"], m.get("kur_kaynak", ""), m["kapatilan_tutar"],
                    d["doviz"], m["tarih"][:19].replace("T", " "), m.get("kullanici_ad", "")])
    _style(ws2, len(h2))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    await log_action(user, "Excel", "AKTAR", "Banka bildirim Excel dosyası indirildi")
    fname = f"banka_bildirim_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@api.get("/reports/summary")
async def reports_summary(user: dict = Depends(get_current_user)):
    decs = [declaration_view(d) for d in await db.declarations.find({}).to_list(5000)]
    by_cur, by_country, by_month = {}, {}, {}
    for d in decs:
        c = by_cur.setdefault(d["doviz"], {"doviz": d["doviz"], "tutar": 0, "kapatilan": 0, "kalan": 0, "adet": 0})
        c["tutar"] = round(c["tutar"] + d["tutar"], 2)
        c["kapatilan"] = round(c["kapatilan"] + d["kapatilan"], 2)
        c["kalan"] = round(c["kalan"] + d["kalan"], 2)
        c["adet"] += 1
        k = by_country.setdefault(d["ulke"] or "-", {"ulke": d["ulke"] or "-", "adet": 0, "kalan": 0})
        k["adet"] += 1
        k["kalan"] = round(k["kalan"] + d["kalan"], 2)
        ay = d["tescil_tarihi"][:7]
        m = by_month.setdefault(ay, {"ay": ay, "tutar": 0, "kapatilan": 0})
        m["tutar"] = round(m["tutar"] + d["tutar"], 2)
        m["kapatilan"] = round(m["kapatilan"] + d["kapatilan"], 2)
    return {"doviz": list(by_cur.values()),
            "ulke": sorted(by_country.values(), key=lambda x: -x["adet"])[:10],
            "ay": sorted(by_month.values(), key=lambda x: x["ay"])[-12:]}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.declarations.create_index("beyanname_no", unique=True)
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_pw),
                                   "name": "Sistem Yöneticisi", "role": "admin", "active": True,
                                   "created_at": utcnow_iso()})
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_pw)}})
    demo = [("ihracat@ihracat.com", "İhracat Personeli", "ihracat"),
            ("banka@ihracat.com", "Banka Personeli", "banka"),
            ("sef@ihracat.com", "Operasyon Şefi", "onaylayan"),
            ("viewer@ihracat.com", "Görüntüleyici", "goruntuleyici")]
    for email, name, role in demo:
        if not await db.users.find_one({"email": email}):
            await db.users.insert_one({"email": email, "password_hash": hash_password("Test1234!"),
                                       "name": name, "role": role, "active": True,
                                       "created_at": utcnow_iso()})


@app.on_event("shutdown")
async def shutdown():
    client.close()
