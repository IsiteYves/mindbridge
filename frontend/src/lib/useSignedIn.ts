import { useSyncExternalStore } from "react";

import { AUTH_EVENT, getToken } from "@/lib/api";

function subscribe(onChange: () => void): () => void {
  window.addEventListener(AUTH_EVENT, onChange);
  return () => window.removeEventListener(AUTH_EVENT, onChange);
}

export function useSignedIn(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => getToken() !== null,
    () => false,
  );
}
