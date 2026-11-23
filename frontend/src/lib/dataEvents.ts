export const DATA_CHANGED = "mindbridge:data-changed";

export function notifyDataChanged(): void {
  window.dispatchEvent(new Event(DATA_CHANGED));
}

export function onDataChanged(listener: () => void): () => void {
  window.addEventListener(DATA_CHANGED, listener);
  return () => window.removeEventListener(DATA_CHANGED, listener);
}
