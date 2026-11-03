"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiRequest, errorMessage } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { username: form.get("username"), password: form.get("password") },
      });
      router.push("/login");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h1>Create an account</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Username
          <input name="username" autoComplete="username" maxLength={64} required />
        </label>
        <label className="field">
          Password (at least 8 characters)
          <input name="password" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="muted">
        Already registered? <Link href="/login">Sign in</Link>
      </p>
    </section>
  );
}
