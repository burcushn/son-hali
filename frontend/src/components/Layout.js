import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, Landmark, History, BarChart3, Users, LogOut,
  Moon, Sun, Menu, X, ShieldCheck, FileCheck2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { ROLE_LABELS } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, id: "nav-dashboard" },
  { to: "/beyannameler", label: "Beyanname Yönetimi", icon: FileText, id: "nav-declarations" },
  { to: "/bedeller", label: "Bedel Yönetimi", icon: Landmark, id: "nav-payments" },
  { to: "/ibkb", label: "IBKB İşlemleri", icon: FileCheck2, id: "nav-ibkb" },
  { to: "/hareketler", label: "Hareket Geçmişi", icon: History, id: "nav-audit" },
  { to: "/raporlar", label: "Raporlar", icon: BarChart3, id: "nav-reports" },
  { to: "/kullanicilar", label: "Kullanıcı Yönetimi", icon: Users, id: "nav-users", adminOnly: true },
];

export const Layout = () => {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  const items = NAV.filter((n) => !n.adminOnly || user?.role === "admin");

  return (
    <div className="min-h-screen flex bg-background">
      <aside
        className={`fixed lg:sticky top-0 z-40 h-screen w-72 shrink-0 border-r border-border bg-card flex flex-col transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="h-16 flex items-center gap-3 px-5 border-b border-border">
          <div className="h-8 w-8 bg-primary flex items-center justify-center rounded-sm">
            <ShieldCheck className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="leading-tight">
            <div className="font-display font-semibold text-sm">İHRACAT BEDELİ</div>
            <div className="text-[10px] tracking-widest text-muted-foreground uppercase">
              Kapatma Sistemi
            </div>
          </div>
        </div>

        <nav className="flex-1 py-4 overflow-y-auto">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={n.id}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm border-l-2 transition-colors duration-200 ${
                  isActive
                    ? "border-primary bg-accent text-accent-foreground font-medium"
                    : "border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`
              }
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-4 space-y-3">
          <div data-testid="current-user-info">
            <div className="text-sm font-medium truncate">{user?.name}</div>
            <div className="text-xs text-primary">{ROLE_LABELS[user?.role] || user?.role}</div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm flex-1"
              data-testid="theme-toggle"
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm flex-1"
              data-testid="logout-button"
              onClick={async () => {
                await logout();
                nav("/giris");
              }}
            >
              <LogOut className="h-4 w-4 mr-1" /> Çıkış
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <div className="lg:hidden h-14 border-b border-border flex items-center px-4 sticky top-0 bg-card z-30">
          <Button variant="ghost" size="sm" data-testid="sidebar-toggle" onClick={() => setOpen(!open)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <span className="ml-2 font-display font-semibold text-sm">İhracat Bedeli Kapatma</span>
        </div>
        <main className="p-6 lg:p-8 max-w-[1800px]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const PageHeader = ({ title, desc, children }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
    <div>
      <h1 className="text-3xl sm:text-4xl font-semibold">{title}</h1>
      {desc && <p className="text-sm text-muted-foreground mt-1.5">{desc}</p>}
    </div>
    <div className="flex flex-wrap gap-2">{children}</div>
  </div>
);

export const Badge2 = ({ cfg, testid }) => (
  <span
    data-testid={testid}
    className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-[11px] font-medium rounded-sm whitespace-nowrap ${cfg?.cls || ""}`}
  >
    <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
    {cfg?.label}
  </span>
);
