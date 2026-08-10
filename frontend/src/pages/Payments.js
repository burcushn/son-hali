import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import { api, errMsg, fmt, fmtDate, CURRENCIES, P_STATUS, can } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Badge2 } from "@/components/Layout";
import { Field } from "@/pages/Declarations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

const EMPTY = {
  banka: "", gonderen: "", tarih: new Date().toISOString().slice(0, 10),
  doviz: "USD", tutar: "", aciklama: "",
};

export default function Payments() {
  const { user } = useAuth();
  const allowed = can(user, "payment");
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [durum, setDurum] = useState("");
  const [form, setForm] = useState(null);

  const load = useCallback(async () => {
    const { data } = await api.get("/payments", { params: { q, durum } });
    setItems(data);
  }, [q, durum]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    const body = { ...form, tutar: Number(form.tutar) };
    try {
      if (form.id) await api.put(`/payments/${form.id}`, body);
      else await api.post("/payments", body);
      toast.success("Bedel kaydedildi");
      setForm(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const remove = async (p) => {
    if (!window.confirm(`${p.gonderen} bedeli silinsin mi?`)) return;
    try {
      await api.delete(`/payments/${p.id}`);
      toast.success("Bedel silindi");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="payments-page">
      <PageHeader title="Bedel Yönetimi" desc="Bankaya gelen ihracat bedelleri ve kullanılabilir bakiyeler">
        {allowed && (
          <Button className="rounded-sm" onClick={() => setForm({ ...EMPTY })} data-testid="add-payment-button">
            <Plus className="h-4 w-4 mr-1.5" /> Yeni Bedel
          </Button>
        )}
      </PageHeader>

      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
          <Input placeholder="Gönderen, banka ara..." value={q} onChange={(e) => setQ(e.target.value)}
                 className="rounded-sm pl-9 w-72" data-testid="payment-search" />
        </div>
        {[["", "Tümü"], ["KULLANILMADI", "Kullanılmadı"], ["KISMI", "Kısmi"], ["TUKENDI", "Tükendi"]].map(([v, l]) => (
          <Button key={v} variant={durum === v ? "default" : "outline"} className="rounded-sm"
                  data-testid={`filter-payment-${v || "all"}`} onClick={() => setDurum(v)}>
            {l}
          </Button>
        ))}
      </div>

      <div className="border border-border bg-card rounded-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60">
            <tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2.5 font-medium">Gönderen</th>
              <th className="px-3 py-2.5 font-medium">Banka</th>
              <th className="px-3 py-2.5 font-medium">Tarih</th>
              <th className="px-3 py-2.5 font-medium text-right">Gelen Tutar</th>
              <th className="px-3 py-2.5 font-medium text-right">Kullanılan</th>
              <th className="px-3 py-2.5 font-medium text-right">Bakiye</th>
              <th className="px-3 py-2.5 font-medium">Durum</th>
              <th className="px-3 py-2.5 font-medium text-right">İşlem</th>
            </tr>
          </thead>
          <tbody data-testid="payments-table">
            {items.map((p) => (
              <tr key={p.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                <td className="px-3 py-2">
                  {p.gonderen}
                  {p.aciklama && <div className="text-xs text-muted-foreground">{p.aciklama}</div>}
                </td>
                <td className="px-3 py-2">{p.banka}</td>
                <td className="px-3 py-2 mono text-xs">{fmtDate(p.tarih)}</td>
                <td className="px-3 py-2 mono text-right">{fmt(p.tutar, p.doviz)}</td>
                <td className="px-3 py-2 mono text-right text-muted-foreground">{fmt(p.kullanilan)}</td>
                <td className="px-3 py-2 mono text-right font-semibold">{fmt(p.bakiye)}</td>
                <td className="px-3 py-2"><Badge2 cfg={P_STATUS[p.durum]} testid={`payment-status-${p.id}`} /></td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  {allowed && (
                    <>
                      <Button variant="ghost" size="sm" className="rounded-sm h-7"
                              data-testid={`edit-payment-${p.id}`}
                              onClick={() => setForm({ ...p, tutar: String(p.tutar) })}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" className="rounded-sm h-7 text-destructive"
                              data-testid={`delete-payment-${p.id}`} onClick={() => remove(p)}>
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
        <DialogContent className="max-w-2xl rounded-sm" data-testid="payment-form-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">{form?.id ? "Bedel Düzenle" : "Yeni Bedel"}</DialogTitle>
            <DialogDescription>
              Bankaya gelen ihracat bedeli. IBKB bilgileri IBKB İşlemleri ekranından girilir.
            </DialogDescription>
          </DialogHeader>
          {form && (
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Banka *" v={form.banka} t="payment-bank-input" on={(v) => setForm({ ...form, banka: v })} />
              <Field label="Gönderen Firma *" v={form.gonderen} t="payment-sender-input" on={(v) => setForm({ ...form, gonderen: v })} />
              <Field label="Tarih *" type="date" v={form.tarih} t="payment-date-input" on={(v) => setForm({ ...form, tarih: v })} />
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wide">Döviz *</Label>
                <select className="w-full h-10 border border-input bg-background rounded-sm px-3 text-sm mono"
                        value={form.doviz} data-testid="payment-currency-select"
                        onChange={(e) => setForm({ ...form, doviz: e.target.value })}>
                  {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <Field label="Gelen Tutar *" type="number" v={form.tutar} t="payment-amount-input" mono
                     on={(v) => setForm({ ...form, tutar: v })} />
              <Field label="Açıklama" v={form.aciklama} t="payment-note-input" on={(v) => setForm({ ...form, aciklama: v })} />
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" className="rounded-sm" onClick={() => setForm(null)}>İptal</Button>
            <Button className="rounded-sm" onClick={save} data-testid="save-payment-button">Kaydet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
