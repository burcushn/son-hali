import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Link2, Loader2, Trash2, RefreshCw } from "lucide-react";
import { api, errMsg, fmt, fmtDate, fmtDateTime, P_STATUS, can } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { Badge2 } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

export const MatchDialog = ({ declaration, open, onOpenChange, onChanged }) => {
  const { user } = useAuth();
  const allowed = can(user, "match");
  const [payments, setPayments] = useState([]);
  const [matches, setMatches] = useState([]);
  const [sel, setSel] = useState(null);
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState(null);
  const [manualRate, setManualRate] = useState("");
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");

  const load = async () => {
    const [p, m] = await Promise.all([
      api.get("/payments", { params: { only_available: true } }),
      api.get(`/declarations/${declaration.id}/matches`),
    ]);
    setPayments(p.data);
    setMatches(m.data);
  };

  useEffect(() => {
    if (open && declaration) {
      setSel(null); setAmount(""); setRate(null); setManualRate("");
      load();
    }
    // eslint-disable-next-line
  }, [open, declaration?.id]);

  const kalan = declaration ? declaration.tutar - declaration.kapatilan : 0;

  const pickPayment = async (p) => {
    setSel(p);
    setRate(null);
    setManualRate("");
    const need = Math.max(0, kalan);
    if (p.doviz === declaration.doviz) {
      setRate({ kur: 1, kaynak: "AYNI_DOVIZ", kur_tarihi: declaration.tescil_tarihi?.slice(0, 10) });
      setAmount(String(Math.min(need, p.bakiye).toFixed(2)));
      return;
    }
    try {
      const { data } = await api.get("/rates", {
        params: { date: declaration.tescil_tarihi, from_cur: p.doviz, to_cur: declaration.doviz },
      });
      setRate(data);
      setAmount(String(Math.min(need, p.bakiye * data.kur).toFixed(2)));
    } catch (e) {
      toast.error(errMsg(e));
      setAmount(String(need.toFixed(2)));
    }
  };

  const effRate = manualRate ? Number(manualRate) : rate?.kur;
  const bedelKullanim = effRate && amount ? Number(amount) / effRate : 0;
  const eksik = kalan - Number(amount || 0);

  const save = async () => {
    setBusy(true);
    try {
      await api.post("/matches", {
        declaration_id: declaration.id,
        payment_id: sel.id,
        kapatilan_tutar: Number(amount),
        kur: manualRate ? Number(manualRate) : null,
      });
      toast.success("Eşleştirme kaydedildi");
      setSel(null); setAmount(""); setRate(null); setManualRate("");
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const removeMatch = async (id) => {
    try {
      await api.delete(`/matches/${id}`);
      toast.success("Eşleştirme geri alındı");
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const editMatch = async (m) => {
    const v = window.prompt("Yeni kapatma tutarı", m.kapatilan_tutar);
    if (!v) return;
    try {
      await api.put(`/matches/${m.id}`, null, { params: { kapatilan_tutar: Number(v) } });
      toast.success("Eşleştirme güncellendi");
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  if (!declaration) return null;
  const filtered = payments.filter(
    (p) =>
      !q ||
      p.gonderen?.toLowerCase().includes(q.toLowerCase()) ||
      p.banka?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl rounded-sm max-h-[92vh] overflow-y-auto" data-testid="match-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">Bedel Bağla — {declaration.beyanname_no}</DialogTitle>
          <DialogDescription>
            Beyanname tutarı {fmt(declaration.tutar, declaration.doviz)} · Kapatılan{" "}
            {fmt(declaration.kapatilan, declaration.doviz)} · Kalan{" "}
            <span className="font-semibold text-foreground mono" data-testid="match-remaining">
              {fmt(kalan, declaration.doviz)}
            </span>
            {" · "}Kur: GB tescil tarihi ({fmtDate(declaration.tescil_tarihi)}) TCMB kuru
          </DialogDescription>
        </DialogHeader>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="border border-border rounded-sm">
            <div className="px-3 py-2 border-b border-border flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide font-medium">Kullanılabilir Bedeller</span>
              <Input
                placeholder="Ara..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="h-7 rounded-sm text-xs ml-auto w-36"
                data-testid="match-payment-search"
              />
            </div>
            <div className="max-h-72 overflow-y-auto">
              {filtered.length ? (
                <table className="w-full text-sm">
                  <tbody>
                    {filtered.map((p) => (
                      <tr
                        key={p.id}
                        data-testid={`match-payment-row-${p.id}`}
                        onClick={() => allowed && pickPayment(p)}
                        className={`border-b border-border cursor-pointer transition-colors duration-200 ${
                          sel?.id === p.id ? "bg-accent" : "hover:bg-secondary/60"
                        }`}
                      >
                        <td className="px-3 py-2">
                          <div className="font-medium">{p.gonderen}</div>
                          <div className="text-xs text-muted-foreground">
                            {p.banka} · <span className="mono">{fmtDate(p.tarih)}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="mono font-semibold">{fmt(p.bakiye, p.doviz)}</div>
                          <div className="text-xs text-muted-foreground">
                            toplam <span className="mono">{fmt(p.tutar)}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-6 text-sm text-muted-foreground">Bakiyesi olan bedel yok.</div>
              )}
            </div>
          </div>

          <div className="border border-border rounded-sm p-4">
            <div className="text-xs uppercase tracking-wide font-medium mb-3">Kapatma İşlemi</div>
            {!allowed ? (
              <div className="text-sm text-muted-foreground">
                Eşleştirme yetkiniz yok. Bu işlem Onaylayan (Şef) veya Admin tarafından yapılır.
              </div>
            ) : !sel ? (
              <div className="text-sm text-muted-foreground">Soldan bir bedel seçin.</div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm">
                  Seçilen bedel: <span className="font-medium">{sel.gonderen}</span> —{" "}
                  <span className="mono">{fmt(sel.bakiye, sel.doviz)}</span> bakiye
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Kapatılacak Tutar ({declaration.doviz})</Label>
                    <Input
                      type="number"
                      step="0.01"
                      className="rounded-sm mono"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      data-testid="match-amount-input"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">
                      Kur (1 {sel.doviz} = ? {declaration.doviz})
                    </Label>
                    <Input
                      type="number"
                      step="0.000001"
                      className="rounded-sm mono"
                      placeholder={rate ? String(rate.kur) : "TCMB"}
                      value={manualRate}
                      onChange={(e) => setManualRate(e.target.value)}
                      data-testid="match-rate-input"
                    />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground border border-border rounded-sm p-2 space-y-1">
                  <div>
                    Kur kaynağı:{" "}
                    <span className="mono">
                      {manualRate ? "MANUEL" : rate ? `${rate.kaynak} (${fmtDate(rate.kur_tarihi)})` : "-"}
                    </span>
                  </div>
                  <div>
                    Bedelden düşecek:{" "}
                    <span className="mono font-semibold text-foreground" data-testid="match-usage-preview">
                      {fmt(bedelKullanim, sel.doviz)}
                    </span>
                  </div>
                  <div>
                    İşlem sonrası eksik bakiye:{" "}
                    <span
                      className={`mono font-semibold ${eksik > 0.01 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}
                      data-testid="match-missing-preview"
                    >
                      {fmt(Math.max(0, eksik), declaration.doviz)}
                    </span>
                    {eksik > 0.01 ? " — beyanname KISMİ KAPALI kalacak" : " — beyanname KAPANACAK"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={save}
                    disabled={busy || !amount || Number(amount) <= 0}
                    className="rounded-sm"
                    data-testid="match-save-button"
                  >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Link2 className="h-4 w-4 mr-1.5" /> Kapat</>}
                  </Button>
                  <Button variant="ghost" className="rounded-sm" onClick={() => setSel(null)}
                          data-testid="match-cancel-button">
                    Vazgeç
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="border border-border rounded-sm mt-2">
          <div className="px-3 py-2 border-b border-border text-xs uppercase tracking-wide font-medium">
            Mevcut Eşleştirmeler ({matches.length})
          </div>
          <div className="overflow-x-auto">
            {matches.length ? (
              <table className="w-full text-sm" data-testid="existing-matches-table">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground bg-secondary/60">
                    <th className="px-3 py-2 font-medium">Bedel</th>
                    <th className="px-3 py-2 font-medium text-right">Kullanılan</th>
                    <th className="px-3 py-2 font-medium text-right">Kur</th>
                    <th className="px-3 py-2 font-medium text-right">Kapatılan</th>
                    <th className="px-3 py-2 font-medium">Tarih / Kullanıcı</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {matches.map((m) => (
                    <tr key={m.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                      <td className="px-3 py-2">
                        {m.payment?.gonderen || "-"}
                        <span className="text-xs text-muted-foreground"> · {m.payment?.banka}</span>
                      </td>
                      <td className="px-3 py-2 mono text-right">{fmt(m.bedel_kullanilan, m.payment?.doviz)}</td>
                      <td className="px-3 py-2 mono text-right text-xs">
                        {m.kur} <span className="text-muted-foreground">{m.kur_kaynak}</span>
                      </td>
                      <td className="px-3 py-2 mono text-right font-semibold">
                        {fmt(m.kapatilan_tutar, declaration.doviz)}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {fmtDateTime(m.tarih)} · {m.kullanici_ad}
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        {allowed && (
                          <>
                            <Button variant="ghost" size="sm" className="rounded-sm h-7"
                                    data-testid={`match-edit-${m.id}`} onClick={() => editMatch(m)}>
                              <RefreshCw className="h-3.5 w-3.5" />
                            </Button>
                            <Button variant="ghost" size="sm" className="rounded-sm h-7 text-destructive"
                                    data-testid={`match-delete-${m.id}`} onClick={() => removeMatch(m.id)}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-4 text-sm text-muted-foreground">Bu beyannameye bağlı eşleştirme yok.</div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export const PaymentBadge = ({ p }) => <Badge2 cfg={P_STATUS[p.durum]} testid={`payment-status-${p.id}`} />;
