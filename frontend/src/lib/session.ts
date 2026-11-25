import { apiRequest, clearToken } from "@/lib/api";

export async function endSession(): Promise<void> {
  // Local sign-out still runs if the server logout call fails.
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch {
    clearToken();
    return;
  }
  clearToken();
}
