import { createContext, useContext, useEffect, useState } from "react";
import { api, errMsg } from "@/lib/apiClient";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => setUser(false))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    if (data.two_factor) return data;
    if (data.token) localStorage.setItem("token", data.token);
    setUser(data);
    return data;
  };

  const verifyCode = async (challenge_id, code) => {
    const { data } = await api.post("/auth/verify-code", { challenge_id, code });
    if (data.token) localStorage.setItem("token", data.token);
    setUser(data);
    return data;
  };

  const resendCode = async (challenge_id) => {
    const { data } = await api.post("/auth/resend-code", { challenge_id });
    return data;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {}
    localStorage.removeItem("token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, verifyCode, resendCode, errMsg }}>
      {children}
    </AuthCtx.Provider>
  );
}
