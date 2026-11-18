import { useEffect, useState } from "react";

import { initials, useCurrentUser } from "@/lib/useCurrentUser";
import { useTheme } from "@/lib/useTheme";

// "TUE, 03 NOV 2026 · GMT+2" — the design shows a fixed "CAT" label, but
// hardcoding that would be wrong for a student outside Central Africa Time.
// Intl reports the viewer's own offset instead, so the label is always true
// for whoever is looking at it.
function formatNow(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZoneName: "shortOffset",
  })
    .formatToParts(date)
    .reduce<Record<string, string>>((all, part) => {
      all[part.type] = part.value;
      return all;
    }, {});
  return `${parts.weekday?.toUpperCase()}, ${parts.day} ${parts.month?.toUpperCase()} ${parts.year} · ${parts.timeZoneName}`;
}

export default function AppTopbar() {
  const [now, setNow] = useState(() => new Date());
  const [theme, toggleTheme] = useTheme();
  const user = useCurrentUser();

  useEffect(() => {
    // One-minute tick is enough for a date/time label with no seconds shown.
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="app-topbar">
      <span className="mono-label topbar-meta">{formatNow(now)}</span>
      <div className="topbar-controls">
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to light appearance" : "Switch to dark appearance"}
          title={theme === "dark" ? "Light appearance" : "Dark appearance"}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
        <span className="avatar" aria-hidden="true">
          {user ? initials(user.name) : ""}
        </span>
      </div>
    </header>
  );
}
