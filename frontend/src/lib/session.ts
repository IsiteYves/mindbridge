import { apiRequest, clearToken } from "@/lib/api";

export async function endSession(): Promise<void> {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch {
    clearToken();
    return;
  }
  clearToken();
}
