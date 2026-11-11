import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router";

import PasswordRules from "@/components/PasswordRules";
import { apiRequest, errorMessage } from "@/lib/api";
import { unmetPasswordRules } from "@/lib/password";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const unmet = unmetPasswordRules(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = code.length === 6 && unmet.length === 0 && confirm === password && !busy;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/auth/reset-password", {
        method: "POST",
        body: { email, code, password, confirm_password: confirm },
      });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <section className="card">
        <h1>Password updated</h1>
        <p className="muted">You can now sign in with your new password.</p>
        <div className="form-row">
          <Link to="/login" className="button">
            Sign in
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="card">
      <h1>Choose a new password</h1>
      <p className="muted">Enter the code from your email and your new password.</p>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="field">
          Reset code
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
        <label className="field">
          New password
          <input
            type="password"
            autoComplete="new-password"
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <PasswordRules password={password} />
        <label className="field">
          Confirm new password
          <input
            type="password"
            autoComplete="new-password"
            maxLength={128}
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
        </label>
        {mismatch && <p className="error">Passwords do not match.</p>}
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={!canSubmit}>
          {busy ? "Saving…" : "Reset password"}
        </button>
      </form>
      <p className="muted">
        Need a new code? <Link to={`/forgot-password?email=${encodeURIComponent(email)}`}>Request one</Link>
      </p>
    </section>
  );
}
