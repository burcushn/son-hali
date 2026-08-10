import { useEffect, useState } from "react";
import { toast } from "sonner";
import { FileDown, Mail, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, errMsg, fmt, can, downloadBankExcel } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";

export default function Reports() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [alert, setAlert] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api.get("/reports/summary").then(({ data }) => setD(data));
    api.get("/alerts/preview").then(({ data }) => setAlert(data));
  }, []);

  const sendAlert = async () => {
    setSending(true);
    try {
      const { data } = await api.post("/alerts/send");
      toast.success(`Uyarı e-postası gönderildi: ${data.to.join(", ")}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSending(false);
    }
  };

  const exportExcel = async () => {
    try {
      const ok = await downloadBankExcel();
      if (ok) toast.success("Excel indirildi");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="reports-page">
      <PageHeader title="Raporlar" desc="Döviz, ülke ve ay bazlı kapatma özetleri">
        <Button className="rounded-sm" onClick={exportExcel} data-testid="reports-export-button">
          <FileDown className="h-4 w-4 mr-1.5" /> Banka Bildirim Excel
        </Button>
      </PageHeader>

      {alert && (
        <div className="border border-border bg-card rounded-sm p-4 mb-4" data-testid="alert-card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 font-display font-semibold text-sm">
                <Mail className="h-4 w-4 text-primary" /> Haftalık E-posta Uyarısı
              </div>
              <div className="text-xs text-muted-foreground mt-1.5">
                Alıcı: <span className="mono">{alert.alicilar.join(", ") || "tanımlı değil"}</span> · {alert.plan}
              </div>
              <div className="flex flex-wrap gap-4 mt-3 text-xs" data-testid="alert-counts">
                <span>Süresi geçmiş: <b className="mono">{alert.sayilar.gecmis}</b></span>
                <span>Süresi yaklaşan: <b className="mono">{alert.sayilar.yaklasan}</b></span>
                <span>IBKB düzenlenmemiş: <b className="mono">{alert.sayilar.ibkb}</b></span>
                <span>Destek alınmamış: <b className="mono">{alert.sayilar.destek}</b></span>
              </div>
            </div>
            {can(user, "match") && (
              <Button variant="outline" className="rounded-sm" onClick={sendAlert} disabled={sending}
                      data-testid="send-alert-button">
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Mail className="h-4 w-4 mr-1.5" /> Şimdi Gönder</>}
              </Button>
            )}
          </div>
        </div>
      )}

      {d && (
        <div className="space-y-4">
          <div className="border border-border bg-card rounded-sm">
            <div className="px-4 py-3 border-b border-border font-display font-semibold text-sm">
              Döviz Bazlı Özet
            </div>
            <table className="w-full text-sm" data-testid="report-currency-table">
              <thead className="bg-secondary/60">
                <tr className="text-left text-xs uppercase text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Döviz</th>
                  <th className="px-4 py-2 font-medium text-right">Adet</th>
                  <th className="px-4 py-2 font-medium text-right">Toplam</th>
                  <th className="px-4 py-2 font-medium text-right">Kapatılan</th>
                  <th className="px-4 py-2 font-medium text-right">Kalan</th>
                </tr>
              </thead>
              <tbody>
                {d.doviz.map((r) => (
                  <tr key={r.doviz} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                    <td className="px-4 py-2 mono font-medium">{r.doviz}</td>
                    <td className="px-4 py-2 mono text-right">{r.adet}</td>
                    <td className="px-4 py-2 mono text-right">{fmt(r.tutar)}</td>
                    <td className="px-4 py-2 mono text-right">{fmt(r.kapatilan)}</td>
                    <td className="px-4 py-2 mono text-right font-semibold">{fmt(r.kalan)}</td>
                  </tr>
                ))}
                {!d.doviz.length && (
                  <tr><td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">Veri yok.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <div className="border border-border bg-card rounded-sm p-4">
              <div className="font-display font-semibold text-sm mb-4">Aylık Beyanname / Kapatma</div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={d.ay}>
                    <CartesianGrid strokeDasharray="2 2" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="ay" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                    <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 2, fontSize: 12 }} />
                    <Bar dataKey="tutar" fill="hsl(var(--primary))" name="Beyanname" />
                    <Bar dataKey="kapatilan" fill="#10b981" name="Kapatılan" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="border border-border bg-card rounded-sm">
              <div className="px-4 py-3 border-b border-border font-display font-semibold text-sm">
                İthalatçı Bazlı Açık Kalan
              </div>
              <table className="w-full text-sm" data-testid="report-importer-table">
                <thead className="bg-secondary/60">
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="px-4 py-2 font-medium">İthalatçı</th>
                    <th className="px-4 py-2 font-medium text-right">Adet</th>
                    <th className="px-4 py-2 font-medium text-right">Kalan</th>
                  </tr>
                </thead>
                <tbody>
                  {d.ithalatci.map((r) => (
                    <tr key={r.ithalatci} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                      <td className="px-4 py-2">{r.ithalatci}</td>
                      <td className="px-4 py-2 mono text-right">{r.adet}</td>
                      <td className="px-4 py-2 mono text-right font-semibold">{fmt(r.kalan)}</td>
                    </tr>
                  ))}
                  {!d.ithalatci.length && (
                    <tr><td colSpan={3} className="px-4 py-10 text-center text-muted-foreground">Veri yok.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="border border-border bg-card rounded-sm p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">IBKB Belgesi Düzenlenmeyen</div>
              <div className="mono text-3xl font-semibold mt-2" data-testid="report-ibkb-missing">
                {d.ibkb_alinmadi}
              </div>
            </div>
            <div className="border border-border bg-card rounded-sm p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Destek Ödemesi (%3) Alınmayan</div>
              <div className="mono text-3xl font-semibold mt-2" data-testid="report-destek-missing">
                {d.destek_alinmadi}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
