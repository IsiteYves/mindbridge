import { FormEvent, useEffect, useState } from "react";

import { apiRequest, errorMessage } from "@/lib/api";
import { Checkin, MOOD_LABEL, MOODS, Mood, STRESS_LEVELS, todayUtc } from "@/lib/wellness";

const HISTORY_PATH = "/wellness/checkins?days=7";

export default function CheckInPage() {
  const [history, setHistory] = useState<Checkin[] | null>(null);
  // Choices start empty and fall back to today's saved check-in, so the form never needs an effect to prefill.
  const [moodChoice, setMoodChoice] = useState<Mood | null>(null);
  const [stressChoice, setStressChoice] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiRequest<Checkin[]>(HISTORY_PATH)
      .then((list) => {
        if (!cancelled) setHistory(list);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today = history?.find((checkin) => checkin.checkin_date === todayUtc()) ?? null;
  const mood = moodChoice ?? today?.mood ?? null;
  const stress = stressChoice ?? today?.stress_level ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mood || stress === null) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await apiRequest("/wellness/checkins", { method: "POST", body: { mood, stress_level: stress } });
      setSaved(true);
      setHistory(await apiRequest<Checkin[]>(HISTORY_PATH));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <h1>Daily check-in</h1>
        <p className="muted">
          Two quick questions. MindBridge uses them to plan your study time, not to assess your mental health.
        </p>

        <form className="form" onSubmit={handleSubmit}>
          <fieldset className="choice-set">
            <legend>How do you feel today?</legend>
            <div className="choice-group">
              {MOODS.map((option) => (
                <label key={option.value} className="choice">
                  <input
                    type="radio"
                    name="mood"
                    value={option.value}
                    checked={mood === option.value}
                    onChange={() => setMoodChoice(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="choice-set">
            <legend>How stressed do you feel?</legend>
            <div className="choice-group">
              {STRESS_LEVELS.map((option) => (
                <label key={option.value} className="choice">
                  <input
                    type="radio"
                    name="stress_level"
                    value={option.value}
                    checked={stress === option.value}
                    onChange={() => setStressChoice(option.value)}
                  />
                  {option.value}. {option.label}
                </label>
              ))}
            </div>
          </fieldset>

          {error && <p className="error">{error}</p>}
          {saved && <p className="muted">Saved. Your study plan will use this check-in.</p>}
          <div className="form-row">
            <button className="button" type="submit" disabled={busy || !mood || stress === null}>
              {busy ? "Saving…" : today ? "Update today's check-in" : "Save check-in"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Last 7 days</h2>
        {history === null && !error && <p className="muted">Loading…</p>}
        {history !== null && history.length === 0 && <p className="muted">No check-ins yet.</p>}
        {history !== null && history.length > 0 && (
          <ul className="list">
            {history.map((checkin) => (
              <li key={checkin.id}>
                <strong>{checkin.checkin_date}</strong> · {MOOD_LABEL(checkin.mood)} · stress{" "}
                {checkin.stress_level} of 5
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
