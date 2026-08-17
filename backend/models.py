from datetime import datetime, timezone
from typing import Optional, Annotated, Any
from bson import ObjectId
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict


def _to_str(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(_to_str)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        d.pop("_id", None)
        return d

    @classmethod
    def from_mongo(cls, doc: Optional[dict]):
        if not doc:
            return None
        return cls.model_validate(doc)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ROLES = ["admin", "ihracat", "banka", "onaylayan", "goruntuleyici"]
ROLE_LABELS = {
    "admin": "Admin",
    "ihracat": "İhracat Personeli",
    "banka": "Banka Personeli",
    "onaylayan": "Onaylayan (Şef)",
    "goruntuleyici": "Görüntüleyici",
}


class User(BaseDocument):
    email: str
    name: str
    role: str
    active: bool = True
    two_factor: bool = False
    created_at: str = Field(default_factory=utcnow_iso)


class UserCreate(BaseModel):
    email: str
    name: str
    role: str
    password: str
    two_factor: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    two_factor: Optional[bool] = None
    password: Optional[str] = None


class LoginInput(BaseModel):
    email: str
    password: str


class VerifyCodeInput(BaseModel):
    challenge_id: str
    code: str


class ResendCodeInput(BaseModel):
    challenge_id: str


class DeclarationInput(BaseModel):
    beyanname_no: str
    acilis_tarihi: str
    kapanis_tarihi: Optional[str] = ""
    ithalatci: str
    gumruk_mudurlugu_no: Optional[str] = ""
    doviz: str
    tutar: float
    ibkb_alindi: bool = False
    destek_alindi: bool = False
    tesvik: bool = False
    taahhut: bool = False
    notlar: Optional[str] = ""


class Declaration(BaseDocument):
    beyanname_no: str
    acilis_tarihi: str
    kapanis_tarihi: str = ""
    ithalatci: str
    gumruk_mudurlugu_no: str = ""
    doviz: str
    tutar: float
    kapatilan: float = 0.0
    ibkb_alindi: bool = False
    destek_alindi: bool = False
    tesvik: bool = False
    taahhut: bool = False
    notlar: str = ""
    durum: str = "ACIK"
    tl_bedel: bool = False
    created_at: str = Field(default_factory=utcnow_iso)
    created_by: str = ""


class PaymentInput(BaseModel):
    banka: str
    gonderen: str
    tarih: str
    doviz: str
    tutar: float
    dth_iban: Optional[str] = ""
    ach_iban: Optional[str] = ""
    aciklama: Optional[str] = ""


class Payment(BaseDocument):
    banka: str
    gonderen: str
    tarih: str
    doviz: str
    tutar: float
    kullanilan: float = 0.0
    aciklama: str = ""
    durum: str = "KULLANILMADI"
    dth_iban: str = ""
    ach_iban: str = ""
    # IBKB ekranından girilen bilgiler
    ibkb_duzenlendi: bool = False
    ibkb_no: str = ""
    ibkb_tarihi: str = ""
    dosya_referansi: str = ""
    tcmb_devir_orani: float = 100.0
    created_at: str = Field(default_factory=utcnow_iso)
    created_by: str = ""


class IbkbInput(BaseModel):
    ibkb_duzenlendi: bool = True
    ibkb_no: str = ""
    ibkb_tarihi: str = ""
    dosya_referansi: str = ""
    ach_iban: Optional[str] = None
    tcmb_devir_orani: float = 100.0


class MatchInput(BaseModel):
    declaration_id: str
    payment_id: str
    kapatilan_tutar: float  # beyanname dövizi cinsinden
    kur: Optional[float] = None  # 1 bedel dövizi = kur x beyanname dövizi


class Match(BaseDocument):
    declaration_id: str
    payment_id: str
    kapatilan_tutar: float
    bedel_kullanilan: float
    kur: float
    kur_kaynak: str = "TCMB"
    tarih: str = Field(default_factory=utcnow_iso)
    kullanici: str = ""
    kullanici_ad: str = ""
