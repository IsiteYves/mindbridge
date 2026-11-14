import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import AuthLayout from "@/components/AuthLayout";
import PasswordRules from "@/components/PasswordRules";
import { apiRequest, errorMessage } from "@/lib/api";
import { unmetPasswordRules } from "@/lib/password";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const unmet = unmetPasswordRules(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = unmet.length === 0 && confirm === password && !busy;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { name: String(form.get("name") ?? ""), email, password, confirm_password: confirm },
      });
      navigate(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      variant="register"
      title="Create your account"
      subtitle="We will email you a 6-digit code to confirm the address."
    >
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Full name
          <input name="name" autoComplete="name" maxLength={120} required />
        </label>
        <label className="field">
          Email
          <input name="email" type="email" autoComplete="email" maxLength={255} required />
        </label>
        <label className="field">
          Password
          <input
            name="password"
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
          Confirm password
          <input
            name="confirm_password"
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
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="muted">
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
