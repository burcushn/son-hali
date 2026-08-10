import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, ShieldCheck } from "lucide-react";
import { api, errMsg, ROLE_LABELS } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/Layout";
import { Field } from "@/pages/Declarations";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

const PERMS = [
  ["Beyanname ekle / düzenle / sil", "ihracat"],
  ["Bedel ekle / düzenle / sil", "banka"],
  ["Eşleştirme yap / düzelt / geri al", "onaylayan"],
  ["Kullanıcı yönetimi", "admin"],
];

export default function Users() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(null);

  const load = () => api.get("/users").then(({ data }) => setItems(data));
  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    try {
      if (form.id) {
        const body = { name: form.name, role: form.role, active: form.active, two_factor: form.two_factor };
        if (form.password) body.password = form.password;
        await api.put(`/users/${form.id}`, body);
      } else {
        await api.post("/users", {
          email: form.email, name: form.name, role: form.role, password: form.password,
        });
      }
      toast.success("Kullanıcı kaydedildi");
      setForm(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const remove = async (u) => {
    if (!window.confirm(`${u.name} silinsin mi?`)) return;
    try {
      await api.delete(`/users/${u.id}`);
      toast.success("Kullanıcı silindi");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="users-page">
      <PageHeader title="Kullanıcı Yönetimi" desc="Roller ve yetkiler — her personel yalnızca kendi işlemini yapabilir">
        <Button className="rounded-sm" data-testid="add-user-button"
                onClick={() => setForm({ email: "", name: "", role: "ihracat", password: "", active: true })}>
          <Plus className="h-4 w-4 mr-1.5" /> Yeni Kullanıcı
        </Button>
      </PageHeader>

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 border border-border bg-card rounded-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-secondary/60">
              <tr className="text-left text-xs uppercase text-muted-foreground">
                <th className="px-3 py-2.5 font-medium">Ad Soyad</th>
                <th className="px-3 py-2.5 font-medium">E-posta</th>
                <th className="px-3 py-2.5 font-medium">Rol</th>
                <th className="px-3 py-2.5 font-medium">2FA</th>
                <th className="px-3 py-2.5 font-medium">Durum</th>
                <th className="px-3 py-2.5 font-medium text-right">İşlem</th>
              </tr>
            </thead>
            <tbody data-testid="users-table">
              {items.map((u) => (
                <tr key={u.id} className="border-t border-border hover:bg-secondary/50 transition-colors duration-200">
                  <td className="px-3 py-2 font-medium">{u.name}</td>
                  <td className="px-3 py-2 mono text-xs">{u.email}</td>
                  <td className="px-3 py-2">{ROLE_LABELS[u.role] || u.role}</td>
                  <td className="px-3 py-2 text-xs" data-testid={`user-2fa-${u.id}`}>
                    {u.two_factor ? "Kod istenir" : "Kapalı"}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-[11px] border px-1.5 py-0.5 rounded-sm ${
                      u.active
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800"
                        : "bg-zinc-100 text-zinc-600 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700"
                    }`}>
                      {u.active ? "AKTİF" : "PASİF"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <Button variant="ghost" size="sm" className="rounded-sm h-7"
                            data-testid={`edit-user-${u.id}`}
                            onClick={() => setForm({ ...u, password: "" })}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    {u.id !== user?.id && (
                      <Button variant="ghost" size="sm" className="rounded-sm h-7 text-destructive"
                              data-testid={`delete-user-${u.id}`} onClick={() => remove(u)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="border border-border bg-card rounded-sm p-4">
          <div className="flex items-center gap-2 font-display font-semibold text-sm mb-4">
            <ShieldCheck className="h-4 w-4 text-primary" /> Yetki Matrisi
          </div>
          <div className="space-y-3 text-sm">
            {PERMS.map(([label, role]) => (
              <div key={label} className="border-b border-border pb-2 last:border-0">
                <div>{label}</div>
                <div className="text-xs text-primary mt-0.5">
                  {ROLE_LABELS[role]}{role !== "admin" ? " + Admin" : ""}
                </div>
              </div>
            ))}
            <div className="text-xs text-muted-foreground pt-1">
              Tüm roller her modülü görüntüleyebilir, rapor ve Excel alabilir; ancak yalnızca kendi
              yetki alanındaki kayıtlar üzerinde işlem yapabilir.
            </div>
          </div>
        </div>
      </div>

      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)}>
        <DialogContent className="max-w-lg rounded-sm" data-testid="user-form-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">{form?.id ? "Kullanıcı Düzenle" : "Yeni Kullanıcı"}</DialogTitle>
          </DialogHeader>
          {form && (
            <div className="space-y-4">
              <Field label="Ad Soyad *" v={form.name} t="user-name-input" on={(v) => setForm({ ...form, name: v })} />
              {!form.id && (
                <Field label="E-posta *" v={form.email} t="user-email-input" mono
                       on={(v) => setForm({ ...form, email: v })} />
              )}
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wide">Rol *</Label>
                <select className="w-full h-10 border border-input bg-background rounded-sm px-3 text-sm"
                        value={form.role} data-testid="user-role-select"
                        onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <Field label={form.id ? "Yeni Şifre (boş bırakılırsa değişmez)" : "Şifre *"}
                     v={form.password} t="user-password-input" on={(v) => setForm({ ...form, password: v })} />
              {form.id && (
                <>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!!form.active} data-testid="user-active-checkbox"
                         onChange={(e) => setForm({ ...form, active: e.target.checked })} />
                  Aktif
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!!form.two_factor} data-testid="user-2fa-checkbox"
                         onChange={(e) => setForm({ ...form, two_factor: e.target.checked })} />
                  Girişte e-posta doğrulama kodu istensin (2 adımlı doğrulama)
                </label>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" className="rounded-sm" onClick={() => setForm(null)}>İptal</Button>
            <Button className="rounded-sm" onClick={save} data-testid="save-user-button">Kaydet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
