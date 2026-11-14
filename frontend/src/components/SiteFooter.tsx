import { FormEvent, useState } from "react";
import { Link } from "react-router";

import { apiRequest, errorMessage } from "@/lib/api";

export const CONTACT_EMAIL = "t.mtakiwa@alustudent.com";

export default function SiteFooter() {
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setError(null);
    setSent(false);
    try {
      await apiRequest("/support", {
        method: "POST",
        body: {
          name: String(data.get("name") ?? ""),
          email: String(data.get("email") ?? ""),
          message: String(data.get("message") ?? ""),
        },
      });
      form.reset();
      setSent(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <footer className="site-footer">
      <div className="footer-grid">
        <div className="footer-brand">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              M
            </span>
            MindBridge
          </Link>
          <p className="muted">Turn every rubric into a plan you can actually finish.</p>
          <nav className="footer-links" aria-label="Footer">
            <Link to="/login">Sign in</Link>
            <Link to="/register">Create account</Link>
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          </nav>
        </div>

        <form className="support-form" onSubmit={handleSubmit} aria-labelledby="support-heading">
          <h2 id="support-heading">Contact support</h2>
          <label className="field">
            Name
            <input name="name" autoComplete="name" maxLength={120} required />
          </label>
          <label className="field">
            Email
            <input name="email" type="email" autoComplete="email" maxLength={255} required />
          </label>
          <label className="field">
            Message
            <textarea name="message" rows={3} minLength={10} maxLength={2000} required />
          </label>
          {sent && <p className="notice">Thanks. Your message was sent to the MindBridge team.</p>}
          {error && <p className="error">{error}</p>}
          <button className="button" type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send message"}
          </button>
        </form>
      </div>
      <p className="footer-legal">
        © {new Date().getFullYear()} MindBridge. MindBridge does not diagnose or treat mental health.
      </p>
    </footer>
  );
}
