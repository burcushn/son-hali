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
    created_at: str = Field(default_factory=utcnow_iso)


class UserCreate(BaseModel):
    email: str
    name: str
    role: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


class LoginInput(BaseModel):
    email: str
    password: str


class DeclarationInput(BaseModel):
    beyanname_no: str
    tescil_tarihi: str
    ihracatci: str
    alici: str
    ulke: str
    doviz: str
    tutar: float
    fatura_no: Optional[str] = ""
    notlar: Optional[str] = ""


class Declaration(BaseDocument):
    beyanname_no: str
    tescil_tarihi: str
    ihracatci: str
    alici: str
    ulke: str
    doviz: str
    tutar: float
    kapatilan: float = 0.0
    fatura_no: str = ""
    notlar: str = ""
    son_kapatma_tarihi: str = ""
    durum: str = "ACIK"
    created_at: str = Field(default_factory=utcnow_iso)
    created_by: str = ""


class PaymentInput(BaseModel):
    banka: str
    gonderen: str
    tarih: str
    doviz: str
    tutar: float
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
    created_at: str = Field(default_factory=utcnow_iso)
    created_by: str = ""


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
