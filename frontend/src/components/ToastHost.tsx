import { useSyncExternalStore } from "react";

import { dismissToast, getToasts, subscribeToasts } from "@/lib/toast";

export default function ToastHost() {
  const items = useSyncExternalStore(subscribeToasts, getToasts, getToasts);
  if (items.length === 0) return null;

  return (
    <div className="toast-host" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={`toast toast-${item.kind}`} role={item.kind === "error" ? "alert" : "status"}>
          <span>{item.message}</span>
          <button type="button" className="toast-close" aria-label="Dismiss" onClick={() => dismissToast(item.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
