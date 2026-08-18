import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { FileCheck2, Search, Loader2 } from "lucide-react";
import { api, errMsg, fmt, fmtDate, can } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Badge2 } from "@/components/Layout";
import { Field } from "@/pages/Declarations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

const OK = { label: "DÜZENLENDİ", cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" };
const NOK = { label: "DÜZENLENMEDİ", cls: "bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" };
const DESTEK = {
  ALINDI: { label: "ALINDI", cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" },
  TALEP_EDILDI: { label: "TALEP EDİLDİ", cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  ALINMADI: { label: "ALINMADI", cls: "bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" },
  KAPSAM_DISI: { label: "KAPSAM DIŞI (TL)", cls: "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950 dark:text-sky-300 dark:border-sky-800" },
};

export default function Ibkb() {
  const { user } = useAuth();
  const allowed = can(user, "payment");
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [only, setOnly] = useState("");
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { data } = await api.get("/payments", { params: { q } });
    setItems(only ? data.filter((p) => p.ibkb_durum === only) : data);
  }, [q, only]);

  useEffect(() => {
    load();
  }, [load]);

  const open = (p) =>
    setForm({
      id: p.id,
      gonderen: p.gonderen,
      banka: p.banka,
      doviz: p.doviz,
      tutar: p.tutar,
      kullanilan: p.kullanilan,
      bakiye: p.bakiye,
      destek_tutari: p.destek_tutari,
      destek_bekleyen: p.destek_bekleyen,
      destek_kapsam_disi: p.destek_kapsam_disi,
      zorunlu_bozdurma: p.zorunlu_bozdurma,
      ibkb_no: p.ibkb_no || "",
      ibkb_tarihi: p.ibkb_tarihi || new Date().toISOString().slice(0, 10),
      dosya_referansi: p.dosya_referansi || "",
      dth_iban: p.dth_iban || "",
      ach_iban: p.ach_iban || p.ach_iban_default || "",
      tcmb_devir_orani: String(p.tcmb_devir_orani ?? 100),
      destek_talep_edildi: !!p.destek_talep_edildi,
      destek_alindi: !!p.destek_alindi,
      tesvik: !!p.tesvik,
      taahhut: !!p.taahhut,
    });

  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/payments/${form.id}/ibkb`, {
        ibkb_duzenlendi: true,
        ibkb_no: form.ibkb_no,
        ibkb_tarihi: form.ibkb_tarihi,
        dosya_referansi: form.dosya_referansi,
        ach_iban: form.ach_iban,
        tcmb_devir_orani: Number(form.tcmb_devir_orani || 100),
        destek_talep_edildi: !!form.destek_talep_edildi,
        destek_alindi: !!form.destek_alindi,
        tesvik: !!form.tesvik,
        taahhut: !!form.taahhut,
      });
      toast.success("IBKB bilgileri kaydedildi");
      setForm(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="ibkb-page">
      <PageHeader
        title="IBKB İşlemleri"
        desc="IBKB düzenlendikten sonra dosya referansı, IBAN bilgileri ve TCMB devir oranı girilir. Bu bilgiler banka bildirim Excel'ini besler."
      />

      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
          <Input placeholder="Gönderen, banka ara..." value={q} onChange={(e) => setQ(e.target.value)}
                 className="rounded-sm pl-9 w-72" data-testid="ibkb-search" />
        </div>
        {[["", "Tümü"], ["DUZENLENMEDI", "Düzenlenmedi"], ["DUZENLENDI", "Düzenlendi"]].map(([v, l]) => (
          <Button key={v || "all"} variant={only === v ? "default" : "outline"} className="rounded-sm"
                  data-testid={`filter-ibkb-${v || "all"}`} onClick={() => setOnly(v)}>
            {l}
          </Button>
        ))}
      </div>

      <div className="border border-border bg-card rounded-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60">
            <tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2.5 font-medium">Gönderen / Banka</th>
              <th className="px-3 py-2.5 font-medium">Tarih</th>
              <th className="px-3 py-2.5 font-medium text-right">Gelen Tutar</th>
              <th className="px-3 py-2.5 font-medium text-right">Zorunlu Bozdurma (%35)</th>
              <th className="px-3 py-2.5 font-medium">IBKB No / Tarih</th>
              <th className="px-3 py-2.5 font-medium">Dosya Referansı</th>
              <th className="px-3 py-2.5 font-medium">DTH IBAN (döviz)</th>
              <th className="px-3 py-2.5 font-medium">ACH IBAN (TL)</th>
              <th className="px-3 py-2.5 font-medium text-right">TCMB Devir</th>
              <th className="px-3 py-2.5 font-medium">Destek (%3)</th>
              <th className="px-3 py-2.5 font-medium text-center">Teşvik / Taahhüt</th>
              <th className="px-3 py-2.5 font-medium">Durum</th>
              <th className="px-3 py-2.5 font-medium text-right">İşlem</th>
            </tr>
          </thead>
          <tbody data-testid="ibkb-table">
            {items.map((p) => (
              <tr key={p.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                <td className="px-3 py-2">
                  {p.gonderen}
                  <div className="text-xs text-muted-foreground">{p.banka}</div>
                </td>
                <td className="px-3 py-2 mono text-xs">{fmtDate(p.tarih)}</td>
                <td className="px-3 py-2 mono text-right">{fmt(p.tutar, p.doviz)}</td>
                <td className="px-3 py-2 mono text-right text-muted-foreground">{fmt(p.zorunlu_bozdurma)}</td>
                <td className="px-3 py-2 mono text-xs">
                  {p.ibkb_no || "-"}
                  <div className="text-muted-foreground">{p.ibkb_tarihi ? fmtDate(p.ibkb_tarihi) : ""}</div>
                </td>
                <td className="px-3 py-2 mono text-xs">{p.dosya_referansi || "-"}</td>
                <td className="px-3 py-2 mono text-xs">{p.dth_iban || "-"}</td>
                <td className="px-3 py-2 mono text-xs">{p.ach_iban || p.ach_iban_default || "-"}</td>
                <td className="px-3 py-2 mono text-right">%{p.tcmb_devir_orani ?? 100}</td>
                <td className="px-3 py-2">
                  {p.destek_kapsam_disi ? (
                    <Badge2 cfg={DESTEK.KAPSAM_DISI} testid={`ibkb-destek-${p.id}`} />
                  ) : (
                    <>
                      <div className="mono text-xs mb-1">{fmt(p.destek_tutari, p.doviz)}</div>
                      <Badge2 cfg={DESTEK[p.destek_durum] || DESTEK.ALINMADI} testid={`ibkb-destek-${p.id}`} />
                      {p.destek_bekleyen > 0 && (
                        <div className="text-[11px] text-muted-foreground mt-1">
                          açık kısım: {fmt(p.destek_bekleyen, p.doviz)}
                        </div>
                      )}
                    </>
                  )}
                </td>
                <td className="px-3 py-2 text-center mono text-xs" data-testid={`ibkb-tesvik-taahhut-${p.id}`}>
                  {p.tesvik ? "E" : "H"} / {p.taahhut ? "E" : "H"}
                </td>
                <td className="px-3 py-2">
                  <Badge2 cfg={p.ibkb_durum === "DUZENLENDI" ? OK : NOK} testid={`ibkb-status-${p.id}`} />
                </td>
                <td className="px-3 py-2 text-right">
                  {allowed && (
                    <Button variant="outline" size="sm" className="rounded-sm h-7"
                            data-testid={`edit-ibkb-${p.id}`} onClick={() => open(p)}>
                      <FileCheck2 className="h-3.5 w-3.5 mr-1" /> IBKB Bilgileri
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={13} className="px-3 py-12 text-center text-sm text-muted-foreground">
                  Kayıt bulunamadı. Bedel girildikten sonra burada listelenir.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)}>
        <DialogContent className="max-w-2xl rounded-sm max-h-[92vh] overflow-y-auto" data-testid="ibkb-form-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">IBKB Bilgileri</DialogTitle>
            {form && (
              <DialogDescription>
                {form.gonderen} · {form.banka} · Gelen tutar{" "}
                <span className="mono">{fmt(form.tutar, form.doviz)}</span> · Zorunlu bozdurma (%35){" "}
                <span className="mono">{fmt(form.zorunlu_bozdurma, form.doviz)}</span>
              </DialogDescription>
            )}
          </DialogHeader>
          {form && (
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="IBKB No" v={form.ibkb_no} t="ibkb-no-input" mono
                     on={(v) => setForm({ ...form, ibkb_no: v })} />
              <Field label="IBKB Tarihi" type="date" v={form.ibkb_tarihi} t="ibkb-date-input"
                     on={(v) => setForm({ ...form, ibkb_tarihi: v })} />
              <Field label="Dosya Referansı" v={form.dosya_referansi} t="ibkb-ref-input" mono
                     on={(v) => setForm({ ...form, dosya_referansi: v })} />
              <Field label="TCMB Devir Oranı (%)" type="number" v={form.tcmb_devir_orani} t="ibkb-tcmb-input" mono
                     on={(v) => setForm({ ...form, tcmb_devir_orani: v })} />
              <Field label="ACH IBAN — bozdurulan tutarın geçtiği TL hesabı" v={form.ach_iban}
                     t="ibkb-ach-iban-input" mono on={(v) => setForm({ ...form, ach_iban: v })} />

              <div className="sm:col-span-2 border-t border-border pt-4 space-y-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Döviz Dönüşüm Desteği (%3) — bu bedel için
                </div>
                {form.destek_kapsam_disi ? (
                  <div className="text-sm text-sky-700 dark:text-sky-300 border border-dashed border-border rounded-sm px-3 py-2">
                    Bedel TL geldiği için döviz dönüşüm desteği kapsam dışıdır.
                  </div>
                ) : (
                  <>
                    <div className="grid sm:grid-cols-2 gap-3 text-sm">
                      <div className="border border-dashed border-border rounded-sm px-3 py-2">
                        Beyannameye kullanılan kısım için destek
                        <div className="mono font-semibold" data-testid="ibkb-destek-tutari">
                          {fmt(form.destek_tutari, form.doviz)}
                        </div>
                      </div>
                      <div className="border border-dashed border-border rounded-sm px-3 py-2 text-muted-foreground">
                        Açık kalan kısım (henüz alınmaz)
                        <div className="mono" data-testid="ibkb-destek-bekleyen">
                          {fmt(form.destek_bekleyen, form.doviz)}
                        </div>
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={!!form.destek_talep_edildi} data-testid="ibkb-destek-talep-checkbox"
                             onChange={(e) => setForm({ ...form, destek_talep_edildi: e.target.checked })} />
                      Destek talebi bankaya iletildi
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={!!form.destek_alindi} data-testid="ibkb-destek-alindi-checkbox"
                             onChange={(e) => setForm({ ...form, destek_alindi: e.target.checked })} />
                      Destek ödemesi hesaba geçti
                    </label>
                  </>
                )}
                <div className="text-xs uppercase tracking-wide text-muted-foreground pt-2">
                  IBKB Evrakı — Teşvik / Taahhüt
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <label className="flex items-center gap-2 text-sm border border-border rounded-sm px-3 h-10">
                    <input type="checkbox" checked={!!form.tesvik} data-testid="ibkb-tesvik-checkbox"
                           onChange={(e) => setForm({ ...form, tesvik: e.target.checked })} />
                    Teşvik (EVET)
                  </label>
                  <label className="flex items-center gap-2 text-sm border border-border rounded-sm px-3 h-10">
                    <input type="checkbox" checked={!!form.taahhut} data-testid="ibkb-taahhut-checkbox"
                           onChange={(e) => setForm({ ...form, taahhut: e.target.checked })} />
                    Taahhüt (EVET)
                  </label>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" className="rounded-sm" onClick={() => setForm(null)}>İptal</Button>
            <Button className="rounded-sm" onClick={save} disabled={busy} data-testid="save-ibkb-button">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Kaydet"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
