import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import AuthLayout from "@/components/AuthLayout";
import { apiRequest, errorMessage } from "@/lib/api";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/auth/forgot-password", { method: "POST", body: { email } });
      // The same answer is given for every address, so go straight to entering the code.
      navigate(`/reset-password?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      variant="forgot"
      title="Reset your password"
      subtitle="Enter your account email. If it exists, we will send a 6-digit reset code."
    >
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send reset code"}
        </button>
      </form>
      <p className="muted">
        <Link to="/login">Back to sign in</Link>
      </p>
    </AuthLayout>
  );
}
