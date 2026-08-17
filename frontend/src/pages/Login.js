import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { errMsg } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Login() {
  const { login, verifyCode, resendCode } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [challenge, setChallenge] = useState(null);
  const [code, setCode] = useState("");
  const [info, setInfo] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await login(email, password);
      if (res?.two_factor) {
        setChallenge(res.challenge_id);
        setInfo(res.mesaj || "Doğrulama kodu e-posta adresinize gönderildi.");
      } else {
        nav("/");
      }
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const submitCode = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verifyCode(challenge, code);
      nav("/");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const again = async () => {
    setError("");
    try {
      const res = await resendCode(challenge);
      setChallenge(res.challenge_id);
      setCode("");
      setInfo(res.mesaj || "Yeni kod gönderildi.");
    } catch (err) {
      setError(errMsg(err));
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 relative">
      <div className="flex items-center px-8 sm:px-16 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-12">
            <img src="/assets/logo.jpg" alt="Kalıpsan Alüminyum" data-testid="login-logo"
                 className="h-12 w-auto max-w-[240px] object-contain mb-4" />
            <div className="leading-tight">
              <div className="font-display font-semibold text-sm">İHRACAT BEDELİ</div>
              <div className="text-[10px] tracking-widest text-muted-foreground uppercase">
                Kapatma &amp; Banka Bildirim Sistemi
              </div>
            </div>
          </div>

          {challenge ? (
            <>
              <h1 className="text-3xl font-semibold mb-2">Doğrulama Kodu</h1>
              <p className="text-sm text-muted-foreground mb-8" data-testid="twofa-info">
                {info} <span className="mono">{email}</span>
              </p>
              <form onSubmit={submitCode} className="space-y-4" data-testid="twofa-form">
                <div className="space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide">6 Haneli Kod</Label>
                  <Input
                    inputMode="numeric"
                    maxLength={6}
                    required
                    data-testid="twofa-code-input"
                    className="rounded-sm h-12 mono text-center text-2xl tracking-[0.5em]"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="000000"
                  />
                </div>
                {error && (
                  <div data-testid="login-error"
                       className="text-sm text-destructive border border-destructive/30 bg-destructive/5 px-3 py-2 rounded-sm">
                    {error}
                  </div>
                )}
                <Button type="submit" disabled={busy || code.length !== 6} data-testid="twofa-submit-button"
                        className="w-full h-11 rounded-sm transition-colors duration-200">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Doğrula ve Giriş Yap"}
                </Button>
                <div className="flex justify-between text-xs">
                  <button type="button" onClick={again} data-testid="twofa-resend-button"
                          className="text-primary hover:underline">
                    Kodu tekrar gönder
                  </button>
                  <button type="button" data-testid="twofa-back-button"
                          onClick={() => { setChallenge(null); setCode(""); setError(""); }}
                          className="text-muted-foreground hover:underline">
                    Geri dön
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
          <h1 className="text-3xl font-semibold mb-2">Oturum Aç</h1>
          <p className="text-sm text-muted-foreground mb-8">
            Operasyon paneline erişmek için giriş yapın.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-wide">E-posta</Label>
              <Input
                type="email"
                required
                data-testid="login-email-input"
                className="rounded-sm h-11"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ad@firma.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-wide">Şifre</Label>
              <Input
                type="password"
                required
                data-testid="login-password-input"
                className="rounded-sm h-11"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            {error && (
              <div
                data-testid="login-error"
                className="text-sm text-destructive border border-destructive/30 bg-destructive/5 px-3 py-2 rounded-sm"
              >
                {error}
              </div>
            )}
            <Button
              type="submit"
              disabled={busy}
              data-testid="login-submit-button"
              className="w-full h-11 rounded-sm transition-colors duration-200"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Giriş Yap"}
            </Button>
          </form>
            </>
          )}

          <div className="mt-10 border border-border rounded-sm p-4 text-xs text-muted-foreground">
            Hesabınız yoksa sistem yöneticinizden talep edin. Bazı hesaplarda giriş sırasında
            e-postanıza 6 haneli doğrulama kodu gönderilir.
          </div>
        </div>
      </div>

      <div className="hidden lg:block relative border-l border-border">
        <img
          src="https://images.unsplash.com/photo-1576831371356-d6e9411ae501?crop=entropy&cs=srgb&fm=jpg&q=85&w=1400"
          alt="Kurumsal mimari"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-[#1a1a2e]/80" />
        <div className="absolute bottom-0 p-12 text-white">
          <div className="text-xs tracking-[0.25em] uppercase opacity-70 mb-3">
            Dış Ticaret Operasyon
          </div>
          <div className="font-display text-3xl font-semibold leading-tight max-w-md">
            Beyanname ve ihracat bedellerini TCMB kuruyla eşleştirin, banka bildirimini tek tıkla hazırlayın.
          </div>
        </div>
      </div>

    </div>
  );
}
