import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Layout } from "@/components/Layout";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Declarations from "@/pages/Declarations";
import Payments from "@/pages/Payments";
import Ibkb from "@/pages/Ibkb";
import AuditLog from "@/pages/AuditLog";
import Reports from "@/pages/Reports";
import Users from "@/pages/Users";

const Protected = ({ children, adminOnly }) => {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  if (!user) return <Navigate to="/giris" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
};

const Guest = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : children;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/giris" element={<Guest><Login /></Guest>} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/beyannameler" element={<Declarations />} />
            <Route path="/bedeller" element={<Payments />} />
            <Route path="/ibkb" element={<Ibkb />} />
            <Route path="/hareketler" element={<AuditLog />} />
            <Route path="/raporlar" element={<Reports />} />
            <Route path="/kullanicilar" element={<Protected adminOnly><Users /></Protected>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </AuthProvider>
  );
}
