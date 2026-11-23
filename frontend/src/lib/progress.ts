const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

export function daysLeftLabel(deadline: Date, now: Date): string {
  if (deadline.getTime() < now.getTime()) return "Overdue";
  const days = Math.round((startOfDay(deadline) - startOfDay(now)) / DAY_MS);
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

export function daysRemaining(deadline: Date, now: Date): number {
  return Math.round((startOfDay(deadline) - startOfDay(now)) / DAY_MS);
}

export function encouragement(done: number, total: number, daysLeft: number | null): { emoji: string; text: string } {
  if (total === 0) return { emoji: "🧭", text: "Add milestones to map the route." };
  if (done === total) return { emoji: "🎉", text: "Every milestone is done. Well done!" };
  if (done / total >= 0.5) return { emoji: "💪", text: "More than halfway. Keep going!" };
  if (done > 0) return { emoji: "🌱", text: "Good progress. Keep the momentum." };
  if (daysLeft !== null && daysLeft <= 2) return { emoji: "⏳", text: "Time is short. Start the next step today." };
  return { emoji: "✨", text: "Plenty of time. Begin with the first step." };
}
