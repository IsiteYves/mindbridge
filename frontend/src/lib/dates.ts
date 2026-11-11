const pad = (value: number) => String(value).padStart(2, "0");

// Converts an ISO timestamp to the value a datetime-local input expects, in the browser's zone.
export function toLocalInput(iso: string): string {
  const date = new Date(iso);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// Converts a datetime-local value to an ISO timestamp with a UTC offset, which the API requires.
export function fromLocalInput(value: string): string {
  return new Date(value).toISOString();
}

export function formatDate(iso: string | null): string {
  if (!iso) return "No deadline";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
