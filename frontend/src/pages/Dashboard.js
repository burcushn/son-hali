import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText, FileClock, FileCheck2, Wallet, Landmark, AlertTriangle, Clock, Loader2,
} from "lucide-react";
import { api, fmt, fmtDate, fmtDateTime } from "@/lib/apiClient";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";

const Card = ({ children, className = "" }) => (
  <div className={`border border-border bg-card rounded-sm ${className}`}>{children}</div>
);

const Kpi = ({ icon: Icon, label, value, sub, testid, accent = "text-primary" }) => (
  <Card className="p-4">
    <div className="flex items-start justify-between">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <Icon className={`h-4 w-4 ${accent}`} />
    </div>
    <div className="mono text-3xl font-semibold mt-3" data-testid={testid}>
      {value}
    </div>
    {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
  </Card>
);

const CurList = ({ obj, testid }) => {
  const keys = Object.keys(obj || {});
  if (!keys.length) return <div className="mono text-3xl font-semibold mt-3">0,00</div>;
  return (
    <div className="mt-3 space-y-1" data-testid={testid}>
      {keys.map((k) => (
        <div key={k} className="flex items-baseline justify-between gap-3">
          <span className="mono text-xl font-semibold">{fmt(obj[k])}</span>
          <span className="text-xs text-muted-foreground">{k}</span>
        </div>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [d, setD] = useState(null);

  useEffect(() => {
    api.get("/dashboard").then(({ data }) => setD(data));
  }, []);

  if (!d)
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
      </div>
    );

  return (
    <div data-testid="dashboard-page">
      <PageHeader title="Dashboard" desc="Beyanname kapatma ve bedel bakiyesi genel durumu">
        <Button asChild variant="outline" className="rounded-sm">
          <Link to="/beyannameler" data-testid="dashboard-go-declarations">
            Beyannamelere Git
          </Link>
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi icon={FileText} label="Açık Beyanname" value={d.acik} testid="kpi-acik"
             sub={`Toplam ${d.toplam} beyanname`} accent="text-zinc-500" />
        <Kpi icon={FileClock} label="Kısmi Kapalı" value={d.kismi} testid="kpi-kismi" accent="text-amber-500" />
        <Kpi icon={FileCheck2} label="Kapalı Beyanname" value={d.kapali} testid="kpi-kapali" accent="text-emerald-500" />
        <Card className="p-4">
          <div className="flex items-start justify-between">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Toplam Açık Tutar</div>
            <Wallet className="h-4 w-4 text-primary" />
          </div>
          <CurList obj={d.acik_tutar} testid="kpi-acik-tutar" />
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        <Card className="p-4">
          <div className="flex items-start justify-between">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Kullanılabilir Bedel Bakiyesi
            </div>
            <Landmark className="h-4 w-4 text-primary" />
          </div>
          <CurList obj={d.bedel_bakiye} testid="kpi-bedel-bakiye" />
        </Card>
        <Kpi icon={Clock} label="Süresi Yaklaşan (≤30 gün)" value={d.yaklasan_sayi}
             testid="kpi-yaklasan" accent="text-amber-500" sub="180 günlük süre dolmak üzere" />
        <Kpi icon={AlertTriangle} label="Süresi Geçen" value={d.gecmis_sayi}
             testid="kpi-gecmis" accent="text-red-500" sub="180 gün aşıldı" />
        <Card className="p-4 flex flex-col justify-between">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Kapanma Oranı</div>
          <div className="mono text-3xl font-semibold" data-testid="kpi-oran">
            {d.toplam ? Math.round((d.kapali / d.toplam) * 100) : 0}%
          </div>
          <div className="h-1.5 bg-secondary mt-3">
            <div className="h-full bg-primary transition-[width] duration-500"
                 style={{ width: `${d.toplam ? (d.kapali / d.toplam) * 100 : 0}%` }} />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-8">
        <DeadlineTable title="Süresi Geçen Beyannameler" items={d.gecmis} testid="table-gecmis" danger />
        <DeadlineTable title="Süresi Yaklaşan Beyannameler" items={d.yaklasan} testid="table-yaklasan" />
      </div>

      <Card className="mt-8">
        <div className="px-4 py-3 border-b border-border font-display font-semibold text-sm">
          Son Hareketler
        </div>
        <div className="divide-y divide-border" data-testid="recent-activity">
          {d.son_hareketler?.length ? (
            d.son_hareketler.map((l, i) => (
              <div key={i} className="px-4 py-2.5 flex items-start gap-3 text-sm hover:bg-secondary/50 transition-colors duration-200">
                <span className="mono text-xs text-muted-foreground w-32 shrink-0">
                  {fmtDateTime(l.tarih)}
                </span>
                <span className="text-xs border border-border px-1.5 py-0.5 rounded-sm shrink-0">
                  {l.modul}
                </span>
                <span className="flex-1">{l.aciklama}</span>
                <span className="text-xs text-muted-foreground shrink-0">{l.kullanici_ad}</span>
              </div>
            ))
          ) : (
            <div className="px-4 py-8 text-sm text-muted-foreground">Henüz hareket yok.</div>
          )}
        </div>
      </Card>
    </div>
  );
}

const DeadlineTable = ({ title, items, testid, danger }) => (
  <Card>
    <div className="px-4 py-3 border-b border-border font-display font-semibold text-sm flex items-center gap-2">
      {danger && <AlertTriangle className="h-4 w-4 text-red-500" />}
      {title}
      <span className="text-xs text-muted-foreground font-normal">({items?.length || 0})</span>
    </div>
    <div className="overflow-x-auto" data-testid={testid}>
      {items?.length ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-muted-foreground bg-secondary/60">
              <th className="px-4 py-2 font-medium">Beyanname</th>
              <th className="px-4 py-2 font-medium">Son Tarih</th>
              <th className="px-4 py-2 font-medium text-right">Kalan Tutar</th>
              <th className="px-4 py-2 font-medium text-right">Gün</th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                <td className="px-4 py-2 mono text-xs">{d.beyanname_no}</td>
                <td className="px-4 py-2 mono text-xs">{fmtDate(d.son_kapatma_tarihi)}</td>
                <td className="px-4 py-2 mono text-right">{fmt(d.kalan, d.doviz)}</td>
                <td className={`px-4 py-2 mono text-right font-semibold ${d.kalan_gun < 0 ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}`}>
                  {d.kalan_gun}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="px-4 py-8 text-sm text-muted-foreground">Kayıt yok.</div>
      )}
    </div>
  </Card>
);
