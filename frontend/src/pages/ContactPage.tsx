import { FormEvent, useState } from "react";

import { apiRequest, errorMessage } from "@/lib/api";

export default function ContactPage() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/contact", {
        method: "POST",
        body: {
          name: form.get("name"),
          email: form.get("email"),
          subject: form.get("subject"),
          message: form.get("message"),
        },
      });
      setSent(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-header">
      <div className="stack">
        <h1>Contact us</h1>
        <p className="muted">Send us a question or a problem. We reply to the email you give us.</p>
      </div>
      <section className="card">
        {sent ? (
          <p className="notice">Thanks. Your message was sent.</p>
        ) : (
          <form className="form" onSubmit={handleSubmit}>
            <div className="form-row">
              <label className="field">
                Name
                <input name="name" required maxLength={120} autoComplete="name" />
              </label>
              <label className="field">
                Email
                <input name="email" type="email" required autoComplete="email" />
              </label>
            </div>
            <label className="field">
              Subject
              <input name="subject" required maxLength={150} />
            </label>
            <label className="field">
              Message
              <textarea name="message" required maxLength={5000} rows={6} />
            </label>
            {error && <p className="error">{error}</p>}
            <div>
              <button aria-busy={busy} className="button" type="submit" disabled={busy}>
                {busy ? "Sending…" : "Send message"}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
