import { useRef, useState } from "react";
import { toast } from "sonner";
import { Download, Upload, Loader2, DatabaseBackup } from "lucide-react";
import { api, errMsg } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";

export const BackupPanel = () => {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState("");
  const [mode, setMode] = useState("merge");

  const download = async () => {
    setBusy("indir");
    try {
      const { data } = await api.get("/backup", { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ihracat-yedek-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "")}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Yedek dosyası indirildi");
    } catch (e) {
      toast.error(errMsg(e));
    }
    setBusy("");
  };

  const upload = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const uyari =
      mode === "replace"
        ? "MEVCUT TÜM VERİLER SİLİNİP yedekten yüklenecek. Emin misiniz?"
        : "Yedekteki kayıtlar mevcut verilerle birleştirilecek. Devam edilsin mi?";
    if (!window.confirm(uyari)) return;
    setBusy("yukle");
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post(`/backup/restore?mode=${mode}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const özet = Object.entries(data.yuklenen || {})
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      toast.success(`Geri yükleme tamamlandı — ${özet}`);
    } catch (err) {
      toast.error(errMsg(err));
    }
    setBusy("");
  };

  return (
    <div className="border border-border bg-card rounded-sm" data-testid="backup-panel">
      <div className="px-4 py-3 border-b border-border font-display font-semibold text-sm flex items-center gap-2">
        <DatabaseBackup className="h-4 w-4 text-primary" /> Veri Yedekleme ve Taşıma
      </div>
      <div className="p-4 space-y-3 text-sm">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Tüm beyanname, bedel, eşleştirme, kullanıcı ve hareket kayıtlarını tek JSON dosyası
          olarak indirin. PC veya şirket sunucusuna geçtiğinizde aynı dosyayı geri yükleyerek
          verilerinizi kaybetmeden taşıyabilirsiniz.
        </p>
        <Button className="rounded-sm w-full" onClick={download} disabled={!!busy}
                data-testid="backup-download-button">
          {busy === "indir" ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Download className="h-4 w-4 mr-1.5" />}
          Yedek İndir (JSON)
        </Button>

        <div className="pt-2 border-t border-border space-y-2">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Yedekten Geri Yükle</div>
          <div className="flex gap-2">
            {[["merge", "Birleştir"], ["replace", "Sıfırla ve yükle"]].map(([v, l]) => (
              <button key={v} onClick={() => setMode(v)} data-testid={`restore-mode-${v}`}
                      className={`flex-1 text-xs px-2 py-1.5 border rounded-sm transition-colors duration-200 ${
                        mode === v ? "border-primary text-primary bg-primary/5" : "border-border text-muted-foreground hover:bg-secondary"
                      }`}>
                {l}
              </button>
            ))}
          </div>
          <input ref={fileRef} type="file" accept=".json,application/json" className="hidden"
                 onChange={upload} data-testid="restore-file-input" />
          <Button variant="outline" className="rounded-sm w-full" disabled={!!busy}
                  onClick={() => fileRef.current?.click()} data-testid="backup-restore-button">
            {busy === "yukle" ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Upload className="h-4 w-4 mr-1.5" />}
            Yedek Dosyası Seç
          </Button>
          <p className="text-[11px] text-muted-foreground">
            Detaylı adımlar için proje klasöründeki <span className="mono">VERI-TASIMA.md</span> dosyasına bakın.
          </p>
        </div>
      </div>
    </div>
  );
};
