import { FormEvent, useState } from "react";

import { apiRequest, errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";

export default function FeedbackPage() {
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await apiRequest("/contact/feedback", {
        method: "POST",
        body: { subject: form.get("subject"), message: form.get("message") },
      });
      event.currentTarget.reset();
      toast.success("Thanks. Your feedback was sent.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div className="stack">
          <h1>Feedback</h1>
          <p className="muted">Tell us what works, what breaks, or what you need.</p>
        </div>
      </header>
      <section className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            Subject
            <input name="subject" required maxLength={150} />
          </label>
          <label className="field">
            Message
            <textarea name="message" required maxLength={5000} rows={6} />
          </label>
          <div>
            <button aria-busy={busy} className="button" type="submit" disabled={busy}>
              {busy ? "Sending…" : "Send feedback"}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
