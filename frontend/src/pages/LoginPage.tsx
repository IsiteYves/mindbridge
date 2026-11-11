import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import { apiRequest, errorMessage, setToken } from "@/lib/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const { token } = await apiRequest<{ token: string }>("/auth/login", {
        method: "POST",
        body: { username: form.get("username"), password: form.get("password") },
      });
      setToken(token);
      navigate("/assignments");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h1>Sign in</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Username
          <input name="username" autoComplete="username" required />
        </label>
        <label className="field">
          Password
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted">
        New here? <Link to="/register">Create an account</Link>
      </p>
    </section>
  );
}
