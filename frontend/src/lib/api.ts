export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:5001/api/v1";

let accessToken: string | null = null;

// Fired whenever the signed-in state changes, so the UI can update without a reload.
export const AUTH_EVENT = "mindbridge:auth-changed";

function notifyAuthChanged(): void {
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export type Status = "not_started" | "in_progress" | "done";

export type Assignment = {
  id: number;
  canvas_id: string | null;
  course: string;
  title: string;
  status: Status;
  deadline: string | null;
  rubric: RubricCriterion[];
};

export type Milestone = {
  id: number;
  assignment_id: number;
  title: string;
  description: string | null;
  target_date: string;
  status: Status;
  position?: number;
  weight?: number | null;
};

export type RubricCriterion = {
  title: string;
  description?: string | null;
  points?: number | null;
  weight?: number | null;
};

export type ImportedAssignment = Assignment;

export type ImportCourseStats = {
  id: string;
  name: string;
  found: number;
  created: number;
  updated: number;
  skipped: number;
};

export type ImportResult = {
  created: number;
  updated: number;
  skipped: { canvas_id: string; title: string; reason: string }[];
  courses: ImportCourseStats[];
  assignments: ImportedAssignment[];
};

export type CanvasCourse = { id: string; name: string };

export type CanvasConnectionStatus = {
  provider: "canvas";
  status: "not_connected" | "connected" | "disconnected";
  last_synced_at: string | null;
};

export type CanvasSyncResult = ImportResult & { connection: CanvasConnectionStatus };

export type CurrentUser = { id: number; name: string; email: string };

export type DailyGoalItem = { label: string; done: boolean };

export type DailyGoal = {
  id: number;
  goal_date: string;
  target_count: number;
  items: DailyGoalItem[];
  done_count: number;
  total_count: number;
};

export type FocusSession = {
  id: number;
  milestone_id: number | null;
  planned_minutes: number;
  started_at: string;
  ended_at: string | null;
  completed: boolean;
};

export const REMINDER_OFFSETS = [5, 2, 1, 0] as const;
export type ReminderOffset = (typeof REMINDER_OFFSETS)[number];

export type ReminderPreference = { offset_days: ReminderOffset; enabled: boolean };

export type NotificationItem = {
  id: number;
  assignment_id: number;
  milestone_id: number | null;
  kind: string;
  offset_days: number | null;
  fired_for_date: string;
  sent_at: string | null;
};

export type AgentFinding = { severity: string; milestone_id: number | null; message: string };

export type AgentReview = {
  generated_at: string;
  summary: string;
  findings: AgentFinding[];
  replan_suggestion: { milestone_ids: number[]; new_target_dates: string[] } | null;
};
export class ApiError extends Error {
  status: number;
  details: Record<string, unknown>;

  constructor(message: string, status: number, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

type RequestOptions = { method?: string; body?: unknown };

export function getToken(): string | null {
  return accessToken;
}

export function setToken(token: string): void {
  accessToken = token;
  notifyAuthChanged();
}

export function publishAuthChange(): void {
  notifyAuthChanged();
}

export function clearToken(): void {
  accessToken = null;
  notifyAuthChanged();
}

let refreshing: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const response = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
        if (!response.ok) {
          clearToken();
          return false;
        }
        const data = (await response.json()) as { token: string };
        setToken(data.token);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export function restoreSession(): Promise<boolean> {
  return refreshAccessToken();
}

function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const sentToken = getToken();
  const usesSession = !path.startsWith("/auth/") && !path.startsWith("/canvas/");

  let response: Response;
  try {
    response = await send(path, options, sentToken);
    if (response.status === 401 && sentToken && usesSession && (await refreshAccessToken())) {
      response = await send(path, options, getToken());
    }
  } catch {
    throw new ApiError("Could not reach the MindBridge server", 0);
  }

  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof data.error === "string" ? data.error : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, data);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
