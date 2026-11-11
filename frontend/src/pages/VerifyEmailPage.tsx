import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { apiRequest, errorMessage, setToken } from "@/lib/api";

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="card">
      <h1>Check your email</h1>
      <p className="muted">Enter the 6-digit code we sent. It expires in 10 minutes.</p>
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
        <button className="button secondary" type="button" onClick={resend} disabled={!email}>
          Send a new code
        </button>
      </form>
      <p className="muted">
        Wrong address? <Link to="/register">Start again</Link>
      </p>
    </section>
  );
}
