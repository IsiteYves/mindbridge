import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import AuthLayout from "@/components/AuthLayout";
import { ApiError, apiRequest, errorMessage, setToken } from "@/lib/api";

const RESEND_COOLDOWN_SECONDS = 300;

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resendAt, setResendAt] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (resendAt <= Date.now()) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [resendAt]);

  const secondsLeft = Math.max(0, Math.ceil((resendAt - now) / 1000));
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = String(secondsLeft % 60).padStart(2, "0");

  function startCooldown(duration: number) {
    const start = Date.now();
    setNow(start);
    setResendAt(start + duration * 1000);
  }

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { token } = await apiRequest<{ token: string }>("/auth/verify-email", {
        method: "POST",
        body: { email, code },
      });
      setToken(token);
      navigate("/assignments", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    setNotice(null);
    try {
      const { message } = await apiRequest<{ message: string }>("/auth/resend-code", {
        method: "POST",
        body: { email },
      });
      setNotice(message);
      startCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(errorMessage(err));
      if (err instanceof ApiError && typeof err.details.retry_after === "number") {
        startCooldown(err.details.retry_after);
      }
    }
  }

  return (
    <AuthLayout variant="verify" title="Check your email" subtitle="Enter the 6-digit code we sent. It expires in 10 minutes.">
      <form className="form" onSubmit={verify}>
        <label className="field">
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="field">
          Verification code
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
            required
          />
        </label>
        {notice && <p className="notice">{notice}</p>}
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={busy || code.length !== 6}>
          {busy ? "Verifying…" : "Verify and continue"}
        </button>
        <button className="button secondary" type="button" onClick={resend} disabled={!email || secondsLeft > 0}>
          {secondsLeft > 0 ? `Send a new code in ${minutes}:${seconds}` : "Send a new code"}
        </button>
      </form>
      <p className="muted">
        Wrong address? <Link to="/register">Start again</Link>
      </p>
    </AuthLayout>
  );
}
