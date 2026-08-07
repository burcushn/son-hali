import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Link2, FileDown, Search } from "lucide-react";
import { api, errMsg, fmt, fmtDate, CURRENCIES, D_STATUS, can, API } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Badge2 } from "@/components/Layout";
import { MatchDialog } from "@/components/MatchDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

const EMPTY = {
  beyanname_no: "", tescil_tarihi: new Date().toISOString().slice(0, 10), ihracatci: "",
  alici: "", ulke: "", doviz: "USD", tutar: "", fatura_no: "", notlar: "",
};

const SURE = {
  GECMIS: { label: "SÜRESİ GEÇTİ", cls: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800" },
  YAKLASAN: { label: "SÜRE YAKLAŞIYOR", cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
};

export default function Declarations() {
  const { user } = useAuth();
  const allowed = can(user, "declaration");
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [durum, setDurum] = useState("");
  const [sure, setSure] = useState("");
  const [form, setForm] = useState(null);
  const [matchFor, setMatchFor] = useState(null);

  const load = useCallback(async () => {
    const { data } = await api.get("/declarations", { params: { q, durum, sure } });
    setItems(data);
  }, [q, durum, sure]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    const body = { ...form, tutar: Number(form.tutar) };
    try {
      if (form.id) await api.put(`/declarations/${form.id}`, body);
      else await api.post("/declarations", body);
      toast.success("Beyanname kaydedildi");
      setForm(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const remove = async (d) => {
    if (!window.confirm(`${d.beyanname_no} silinsin mi?`)) return;
    try {
      await api.delete(`/declarations/${d.id}`);
      toast.success("Beyanname silindi");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const exportExcel = async () => {
    try {
      const res = await api.get("/export/excel", { params: { durum }, responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "banka_bildirim.xlsx";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Excel indirildi");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="declarations-page">
      <PageHeader title="Beyanname Yönetimi" desc="İhracat beyannameleri · 180 günlük kapatma süresi otomatik hesaplanır">
        <Button variant="outline" className="rounded-sm" onClick={exportExcel} data-testid="export-excel-button">
          <FileDown className="h-4 w-4 mr-1.5" /> Excel Aktar
        </Button>
        {allowed && (
          <Button className="rounded-sm" onClick={() => setForm({ ...EMPTY })} data-testid="add-declaration-button">
            <Plus className="h-4 w-4 mr-1.5" /> Yeni Beyanname
          </Button>
        )}
      </PageHeader>

      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
          <Input
            placeholder="Beyanname no, alıcı, fatura ara..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="rounded-sm pl-9 w-72"
            data-testid="declaration-search"
          />
        </div>
        {[["", "Tümü"], ["ACIK", "Açık"], ["KISMI", "Kısmi"], ["KAPALI", "Kapalı"]].map(([v, l]) => (
          <Button key={v} variant={durum === v ? "default" : "outline"} className="rounded-sm"
                  data-testid={`filter-durum-${v || "all"}`} onClick={() => setDurum(v)}>
            {l}
          </Button>
        ))}
        {[["YAKLASAN", "Süresi Yaklaşan"], ["GECMIS", "Süresi Geçen"]].map(([v, l]) => (
          <Button key={v} variant={sure === v ? "default" : "outline"} className="rounded-sm"
                  data-testid={`filter-sure-${v}`} onClick={() => setSure(sure === v ? "" : v)}>
            {l}
          </Button>
        ))}
      </div>

      <div className="border border-border bg-card rounded-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60 sticky top-0">
            <tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2.5 font-medium">Beyanname No</th>
              <th className="px-3 py-2.5 font-medium">Tescil / Son Tarih</th>
              <th className="px-3 py-2.5 font-medium">Alıcı / Ülke</th>
              <th className="px-3 py-2.5 font-medium text-right">Tutar</th>
              <th className="px-3 py-2.5 font-medium text-right">Kapatılan</th>
              <th className="px-3 py-2.5 font-medium text-right">Kalan</th>
              <th className="px-3 py-2.5 font-medium">Durum</th>
              <th className="px-3 py-2.5 font-medium text-right">İşlem</th>
            </tr>
          </thead>
          <tbody data-testid="declarations-table">
            {items.map((d) => (
              <tr key={d.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                <td className="px-3 py-2 mono text-xs font-medium">
                  {d.beyanname_no}
                  {d.fatura_no && <div className="text-muted-foreground">Fat: {d.fatura_no}</div>}
                </td>
                <td className="px-3 py-2 mono text-xs">
                  {fmtDate(d.tescil_tarihi)}
                  <div className="text-muted-foreground">→ {fmtDate(d.son_kapatma_tarihi)}</div>
                </td>
                <td className="px-3 py-2">
                  {d.alici}
                  <div className="text-xs text-muted-foreground">{d.ulke} · {d.ihracatci}</div>
                </td>
                <td className="px-3 py-2 mono text-right">{fmt(d.tutar, d.doviz)}</td>
                <td className="px-3 py-2 mono text-right text-muted-foreground">{fmt(d.kapatilan)}</td>
                <td className="px-3 py-2 mono text-right font-semibold">{fmt(d.kalan)}</td>
                <td className="px-3 py-2 space-y-1">
                  <Badge2 cfg={D_STATUS[d.durum]} testid={`declaration-status-${d.id}`} />
                  {SURE[d.sure_durum] && <div><Badge2 cfg={SURE[d.sure_durum]} testid={`declaration-sure-${d.id}`} /></div>}
                </td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <Button variant="outline" size="sm" className="rounded-sm h-7 mr-1"
                          data-testid={`link-payment-${d.id}`} onClick={() => setMatchFor(d)}>
                    <Link2 className="h-3.5 w-3.5 mr-1" /> Bedel Bağla
                  </Button>
                  {allowed && (
                    <>
                      <Button variant="ghost" size="sm" className="rounded-sm h-7"
                              data-testid={`edit-declaration-${d.id}`}
                              onClick={() => setForm({ ...d, tutar: String(d.tutar) })}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" className="rounded-sm h-7 text-destructive"
                              data-testid={`delete-declaration-${d.id}`} onClick={() => remove(d)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={8} className="px-3 py-12 text-center text-sm text-muted-foreground">
                  Kayıt bulunamadı.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)}>
        <DialogContent className="max-w-2xl rounded-sm" data-testid="declaration-form-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">
              {form?.id ? "Beyanname Düzenle" : "Yeni Beyanname"}
            </DialogTitle>
          </DialogHeader>
          {form && (
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Beyanname No *" v={form.beyanname_no} t="declaration-no-input"
                     on={(v) => setForm({ ...form, beyanname_no: v })} mono />
              <Field label="GB Tescil Tarihi *" type="date" v={form.tescil_tarihi} t="declaration-date-input"
                     on={(v) => setForm({ ...form, tescil_tarihi: v })} />
              <Field label="İhracatçı *" v={form.ihracatci} t="declaration-exporter-input"
                     on={(v) => setForm({ ...form, ihracatci: v })} />
              <Field label="Alıcı Firma *" v={form.alici} t="declaration-buyer-input"
                     on={(v) => setForm({ ...form, alici: v })} />
              <Field label="Ülke" v={form.ulke} t="declaration-country-input"
                     on={(v) => setForm({ ...form, ulke: v })} />
              <Field label="Fatura No" v={form.fatura_no} t="declaration-invoice-input"
                     on={(v) => setForm({ ...form, fatura_no: v })} mono />
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wide">Döviz *</Label>
                <select
                  className="w-full h-10 border border-input bg-background rounded-sm px-3 text-sm mono"
                  value={form.doviz}
                  data-testid="declaration-currency-select"
                  onChange={(e) => setForm({ ...form, doviz: e.target.value })}
                >
                  {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <Field label="Beyanname / Fatura Tutarı *" type="number" v={form.tutar} t="declaration-amount-input"
                     on={(v) => setForm({ ...form, tutar: v })} mono />
              <div className="sm:col-span-2 space-y-1.5">
                <Label className="text-xs uppercase tracking-wide">Notlar</Label>
                <Textarea className="rounded-sm" value={form.notlar}
                          data-testid="declaration-notes-input"
                          onChange={(e) => setForm({ ...form, notlar: e.target.value })} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" className="rounded-sm" onClick={() => setForm(null)}>İptal</Button>
            <Button className="rounded-sm" onClick={save} data-testid="save-declaration-button">Kaydet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <MatchDialog
        declaration={matchFor}
        open={!!matchFor}
        onOpenChange={(o) => !o && setMatchFor(null)}
        onChanged={load}
      />
    </div>
  );
}

export const Field = ({ label, v, on, t, type = "text", mono }) => (
  <div className="space-y-1.5">
    <Label className="text-xs uppercase tracking-wide">{label}</Label>
    <Input type={type} value={v ?? ""} data-testid={t} onChange={(e) => on(e.target.value)}
           className={`rounded-sm ${mono ? "mono" : ""}`} step={type === "number" ? "0.01" : undefined} />
  </div>
);
