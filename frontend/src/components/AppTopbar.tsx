import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { endSession } from "@/lib/session";
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

export default function AppTopbar({ navOpen, onToggleNav }: { navOpen: boolean; onToggleNav: () => void }) {
  const [now, setNow] = useState(() => new Date());
  const [theme, toggleTheme] = useTheme();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  async function signOut() {
    setMenuOpen(false);
    await endSession();
    navigate("/login", { replace: true });
  }

  useEffect(() => {
    // One-minute tick is enough for a date/time label with no seconds shown.
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="app-topbar">
      <button
        type="button"
        className={`burger${navOpen ? " open" : ""}`}
        aria-label={navOpen ? "Close menu" : "Open menu"}
        aria-expanded={navOpen}
        onClick={onToggleNav}
      >
        <span />
        <span />
        <span />
      </button>
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
        <div className="account-menu" ref={menuRef}>
          <button
            type="button"
            className="avatar avatar-button"
            aria-label="Account menu"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {user ? initials(user.name) : ""}
          </button>
          {menuOpen && (
            <div className="account-menu-panel" role="menu">
              {user && (
                <div className="account-identity">
                  <strong>{user.name}</strong>
                  <span className="muted small">{user.email}</span>
                </div>
              )}
              <Link to="/settings" role="menuitem" onClick={() => setMenuOpen(false)}>
                Settings
              </Link>
              <button type="button" role="menuitem" onClick={signOut}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
