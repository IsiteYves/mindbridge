import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import AuthLayout from "@/components/AuthLayout";
import { apiRequest, ApiError, errorMessage, setToken } from "@/lib/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const { token } = await apiRequest<{ token: string }>("/auth/login", {
        method: "POST",
        body: { email, password: String(form.get("password") ?? "") },
      });
      setToken(token);
      navigate("/assignments", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(errorMessage(err), 0));
      setBusy(false);
    }
  }

  const needsVerification = error?.status === 403;

  return (
    <AuthLayout variant="login" title="Sign in" subtitle="Use the email and password you registered with.">
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label className="field">
          Password
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && (
          <p className="error">
            {error.message}
            {needsVerification && (
              <>
                {" "}
                <Link to={`/verify-email?email=${encodeURIComponent(email)}`}>Enter your code</Link>
              </>
            )}
          </p>
        )}
        <button className="button" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted">
        <Link to={`/forgot-password?email=${encodeURIComponent(email)}`}>Forgot password?</Link>
      </p>
      <p className="muted">
        New here? <Link to="/register">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
