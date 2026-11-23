import type { Assignment } from "@/lib/api";

export function isPending(assignment: Pick<Assignment, "status" | "deadline">, now: number = Date.now()): boolean {
  return assignment.status !== "done" && assignment.deadline !== null && new Date(assignment.deadline).getTime() > now;
}

export function stateLabel(assignment: Pick<Assignment, "status" | "deadline">): string {
  if (isPending(assignment)) return "Pending";
  return assignment.status === "done" ? "Submitted" : "Closed";
}
