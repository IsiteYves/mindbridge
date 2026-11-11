export type ScheduleMilestone = {
  id: number;
  assignment_id: number;
  course: string;
  assignment_title: string;
  title: string;
  status: string;
  target_date: string;
  suggested_date: string;
};

export type Schedule = {
  stress_average: number | null;
  slack_fraction: number;
  milestones: ScheduleMilestone[];
};

export type Reminder = {
  kind: "milestone" | "deadline";
  id: number;
  title: string;
  course: string;
  due_at: string;
  hours_left: number;
};

// Adjusted dates within a minute of the original are not worth flagging as moved.
export function isMoved(milestone: ScheduleMilestone): boolean {
  const difference = Math.abs(new Date(milestone.suggested_date).getTime() - new Date(milestone.target_date).getTime());
  return difference > 60_000;
}

export function timeLeft(hours: number): string {
  if (hours < 1) return "in less than an hour";
  if (hours < 48) return `in ${Math.round(hours)} hours`;
  return `in ${Math.round(hours / 24)} days`;
}
