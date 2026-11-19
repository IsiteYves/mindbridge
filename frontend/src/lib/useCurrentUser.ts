import { useEffect, useState } from "react";

import { apiRequest, AUTH_EVENT, type CurrentUser, getToken } from "@/lib/api";

// Module-level cache: every consumer of this hook (sidebar, topbar) shares one
// request instead of each firing its own GET /auth/me on mount.
let cached: CurrentUser | null = null;
let inFlight: Promise<CurrentUser> | null = null;

function fetchCurrentUser(): Promise<CurrentUser> {
  if (!inFlight) {
    inFlight = apiRequest<CurrentUser>("/auth/me").finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}

// Returns null while loading or signed out, then the student's name and email
// once loaded. Callers that need an initials-only placeholder before this
// resolves should render their own fallback; this hook never guesses a name.
export function useCurrentUser(): CurrentUser | null {
  const [user, setUser] = useState<CurrentUser | null>(cached);

  useEffect(() => {
    let cancelled = false;

    function load() {
      if (!getToken()) {
        cached = null;
        setUser(null);
        return;
      }
      fetchCurrentUser()
        .then((result) => {
          if (cancelled) return;
          cached = result;
          setUser(result);
        })
        .catch(() => {
          if (!cancelled) setUser(null);
        });
    }

    load();
    window.addEventListener(AUTH_EVENT, load);
    return () => {
      cancelled = true;
      window.removeEventListener(AUTH_EVENT, load);
    };
  }, []);

  return user;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
