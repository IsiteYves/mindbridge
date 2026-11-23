import type { Assignment } from "@/lib/api";

export function isPending(assignment: Pick<Assignment, "status" | "deadline">, now: number = Date.now()): boolean {
  return assignment.status !== "done" && assignment.deadline !== null && new Date(assignment.deadline).getTime() > now;
}
