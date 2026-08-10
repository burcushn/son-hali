import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { api, errMsg, fmtDateTime } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";

const MODULES = ["", "Beyanname", "Bedel", "IBKB", "Eşleştirme", "Kullanıcı", "Excel", "Uyarı", "Hareket"];

export default function AuditLog() {
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [modul, setModul] = useState("");

  const load = () =>
    api.get("/audit-logs", { params: { modul } }).then(({ data }) => setLogs(data));

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [modul]);

  const clean = async () => {
    const v = window.prompt(
      "Kaç günden eski hareket kayıtları silinsin? (örn. 365 = 1 yıldan eski. 0 yazarsanız tüm geçmiş silinir)",
      "365"
    );
    if (v === null) return;
    try {
      const { data } = await api.delete("/audit-logs", { params: { older_than_days: Number(v) } });
      toast.success(`${data.silinen} kayıt silindi`);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="audit-page">
      <PageHeader
        title="Hareket Geçmişi"
        desc="Tüm ekleme, güncelleme, silme ve eşleştirme işlemleri · kayıtlar çok az yer kaplar, saklamanız önerilir"
      >
        {user?.role === "admin" && (
          <Button variant="outline" className="rounded-sm" onClick={clean} data-testid="clear-audit-button">
            <Trash2 className="h-4 w-4 mr-1.5" /> Eski Kayıtları Temizle
          </Button>
        )}
      </PageHeader>

      <div className="flex flex-wrap gap-2 mb-4">
        {MODULES.map((m) => (
          <Button key={m || "all"} variant={modul === m ? "default" : "outline"} className="rounded-sm"
                  data-testid={`filter-modul-${m || "all"}`} onClick={() => setModul(m)}>
            {m || "Tümü"}
          </Button>
        ))}
      </div>

      <div className="border border-border bg-card rounded-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60">
            <tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2.5 font-medium">Tarih</th>
              <th className="px-3 py-2.5 font-medium">Modül</th>
              <th className="px-3 py-2.5 font-medium">İşlem</th>
              <th className="px-3 py-2.5 font-medium">Açıklama</th>
              <th className="px-3 py-2.5 font-medium">Kullanıcı</th>
            </tr>
          </thead>
          <tbody data-testid="audit-table">
            {logs.map((l, i) => (
              <tr key={i} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                <td className="px-3 py-2 mono text-xs whitespace-nowrap">{fmtDateTime(l.tarih)}</td>
                <td className="px-3 py-2 text-xs">{l.modul}</td>
                <td className="px-3 py-2">
                  <span className="text-[11px] border border-border px-1.5 py-0.5 rounded-sm">{l.islem}</span>
                </td>
                <td className="px-3 py-2">{l.aciklama}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">{l.kullanici_ad}</td>
              </tr>
            ))}
            {!logs.length && (
              <tr><td colSpan={5} className="px-3 py-12 text-center text-sm text-muted-foreground">Hareket yok.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
