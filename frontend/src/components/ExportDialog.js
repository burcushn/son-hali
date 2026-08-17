import { useEffect, useState } from "react";
import { toast } from "sonner";
import { FileDown, Loader2, AlertTriangle } from "lucide-react";
import { api, errMsg, fmt, fmtDate, downloadBankExcel } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

export const ExportDialog = ({ open, onOpenChange }) => {
  const [rows, setRows] = useState(null);
  const [sel, setSel] = useState({});
  const [busy, setBusy] = useState(false);
  const [hidePast, setHidePast] = useState(true);

  useEffect(() => {
    if (!open) return;
    setRows(null);
    api.get("/export/rows").then(({ data }) => {
      setRows(data);
      const init = {};
      data.forEach((r) => { if (!r.gonderildi) init[r.match_id] = true; });
      setSel(init);
    }).catch((e) => toast.error(errMsg(e)));
  }, [open]);

  const list = (rows || []).filter((r) => !hidePast || !r.gonderildi);
  const ids = Object.keys(sel).filter((k) => sel[k]);
  const toggleAll = (v) => {
    const next = {};
    list.forEach((r) => { next[r.match_id] = v; });
    setSel(next);
  };

  const download = async () => {
    setBusy(true);
    try {
      const ok = await downloadBankExcel({ match_ids: ids.join(",") });
      if (ok) {
        toast.success(`${ids.length} satır Excel'e aktarıldı ve "gönderildi" olarak işaretlendi`);
        onOpenChange(false);
      }
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl rounded-sm max-h-[90vh] overflow-y-auto" data-testid="export-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">Banka Bildirim Excel — Satır Seçimi</DialogTitle>
          <DialogDescription>
            Bankaya göndereceğiniz satırları seçin. Daha önce Excel'e aktarılan satırlar
            "gönderildi" olarak işaretlenir ve varsayılan olarak listede gizlenir.
          </DialogDescription>
        </DialogHeader>

        {!rows ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-10">
            <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <Button variant="outline" size="sm" className="rounded-sm h-7"
                      data-testid="export-select-all" onClick={() => toggleAll(true)}>
                Tümünü seç
              </Button>
              <Button variant="outline" size="sm" className="rounded-sm h-7"
                      data-testid="export-select-none" onClick={() => toggleAll(false)}>
                Seçimi temizle
              </Button>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={hidePast} data-testid="export-hide-sent"
                       onChange={(e) => setHidePast(e.target.checked)} />
                Daha önce gönderilenleri gizle
              </label>
              <span className="ml-auto text-muted-foreground">
                Seçili: <b className="mono text-foreground" data-testid="export-selected-count">{ids.length}</b>
              </span>
            </div>

            <div className="border border-border rounded-sm overflow-x-auto max-h-[46vh] overflow-y-auto mt-2">
              <table className="w-full text-sm">
                <thead className="bg-secondary/60 sticky top-0">
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="px-3 py-2 w-8" />
                    <th className="px-3 py-2 font-medium">GB No</th>
                    <th className="px-3 py-2 font-medium">GB Tarihi</th>
                    <th className="px-3 py-2 font-medium">Dosya Referansı</th>
                    <th className="px-3 py-2 font-medium">Bedel</th>
                    <th className="px-3 py-2 font-medium text-right">Tutar</th>
                    <th className="px-3 py-2 font-medium">Durum</th>
                  </tr>
                </thead>
                <tbody data-testid="export-rows-table">
                  {list.map((r) => (
                    <tr key={r.match_id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                      <td className="px-3 py-2">
                        <input type="checkbox" checked={!!sel[r.match_id]}
                               data-testid={`export-row-${r.match_id}`}
                               onChange={(e) => setSel({ ...sel, [r.match_id]: e.target.checked })} />
                      </td>
                      <td className="px-3 py-2 mono text-xs">{r.beyanname_no}</td>
                      <td className="px-3 py-2 mono text-xs">{fmtDate(r.gb_tarihi)}</td>
                      <td className="px-3 py-2 mono text-xs">{r.dosya_referansi || "-"}</td>
                      <td className="px-3 py-2 text-xs">{r.bedel}</td>
                      <td className="px-3 py-2 mono text-right">{fmt(r.tutar, r.doviz)}</td>
                      <td className="px-3 py-2 text-xs">
                        {r.gonderildi && (
                          <div className="text-muted-foreground">
                            gönderildi {r.gonderim_tarihi ? fmtDate(r.gonderim_tarihi) : ""}
                          </div>
                        )}
                        {!!r.eksikler?.length && (
                          <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                            <AlertTriangle className="h-3 w-3" /> eksik: {r.eksikler.join(", ")}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!list.length && (
                    <tr>
                      <td colSpan={7} className="px-3 py-10 text-center text-sm text-muted-foreground">
                        Gönderilecek yeni satır yok.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        <DialogFooter>
          <Button variant="ghost" className="rounded-sm" onClick={() => onOpenChange(false)}
                  data-testid="export-cancel-button">
            Vazgeç
          </Button>
          <Button className="rounded-sm" disabled={busy || !ids.length} onClick={download}
                  data-testid="export-download-button">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><FileDown className="h-4 w-4 mr-1.5" /> Seçili {ids.length} Satırı İndir</>}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
