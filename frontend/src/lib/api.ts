export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5001/api/v1";

const TOKEN_KEY = "mindbridge.token";

export type Status = "not_started" | "in_progress" | "done";

export type Assignment = {
  id: number;
  canvas_id: string | null;
  course: string;
  title: string;
  status: Status;
  deadline: string | null;
};

export type Milestone = {
  id: number;
  assignment_id: number;
  title: string;
  description: string | null;
  target_date: string;
  status: Status;
};

export type RubricCriterion = { title: string; points?: number | null };

export type ImportedAssignment = Assignment & { rubric: RubricCriterion[] };

export type ImportResult = {
  created: number;
  updated: number;
  skipped: { canvas_id: string; title: string; reason: string }[];
  assignments: ImportedAssignment[];
};

export type CanvasCourse = { id: string; name: string };

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage is unavailable (private mode or blocked), so the user will be asked to sign in again.
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}

export async function apiRequest<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError("Could not reach the MindBridge server", 0);
  }

  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) clearToken();
    const message = typeof data.error === "string" ? data.error : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
