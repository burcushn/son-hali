import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return e?.message || "Bir hata oluştu";
}

export const CURRENCIES = ["USD", "EUR", "GBP", "CHF", "TRY", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK", "CNY", "AED", "SAR"];

export const fmt = (n, cur) =>
  `${Number(n || 0).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${cur ? " " + cur : ""}`;

export const fmtDate = (s) => (s ? String(s).slice(0, 10).split("-").reverse().join(".") : "-");
export const fmtDateTime = (s) =>
  s ? `${fmtDate(s)} ${String(s).slice(11, 16)}` : "-";

export const D_STATUS = {
  ACIK: { label: "AÇIK", cls: "bg-zinc-100 text-zinc-800 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700" },
  KISMI: { label: "KISMİ KAPALI", cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  KAPALI: { label: "KAPALI", cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" },
};

export const P_STATUS = {
  KULLANILMADI: { label: "KULLANILMADI", cls: "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-300 dark:border-indigo-800" },
  KISMI: { label: "KISMİ KULLANILDI", cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  TUKENDI: { label: "TÜKENDİ", cls: "bg-zinc-100 text-zinc-600 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700" },
};

export const ROLE_LABELS = {
  admin: "Admin",
  ihracat: "İhracat Personeli",
  banka: "Banka Personeli",
  onaylayan: "Onaylayan (Şef)",
  goruntuleyici: "Görüntüleyici",
};

export async function downloadBankExcel(params = {}) {
  const { data: check } = await api.get("/export/check", { params });
  if (check.eksik_sayisi > 0) {
    const list = check.eksikler
      .slice(0, 5)
      .map((e) => `• ${e.beyanname_no} (${e.bedel}): ${e.alanlar.join(", ")}`)
      .join("\n");
    const ok = window.confirm(
      `${check.eksik_sayisi} satırda banka bildiriminde boş kalacak alan var:\n\n${list}` +
        `${check.eksik_sayisi > 5 ? `\n… ve ${check.eksik_sayisi - 5} satır daha` : ""}` +
        `\n\nYine de Excel'i indirmek istiyor musunuz?`
    );
    if (!ok) return false;
  }
  const res = await api.get("/export/excel", { params, responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `banka_bildirim_${new Date().toISOString().slice(0, 10)}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
  return true;
}

export const can = (user, action) => {
  if (!user) return false;
  if (user.role === "admin") return true;
  const map = {
    declaration: ["ihracat"],
    payment: ["banka"],
    match: ["onaylayan"],
    users: [],
  };
  return (map[action] || []).includes(user.role);
};
