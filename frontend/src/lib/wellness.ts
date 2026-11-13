export const MOODS = [
  { value: "great", label: "Great" },
  { value: "good", label: "Good" },
  { value: "okay", label: "Okay" },
  { value: "low", label: "Low" },
  { value: "stressed", label: "Stressed" },
] as const;

export type Mood = (typeof MOODS)[number]["value"];

export const STRESS_LEVELS = [
  { value: 1, label: "Calm" },
  { value: 2, label: "Mild" },
  { value: 3, label: "Moderate" },
  { value: 4, label: "High" },
  { value: 5, label: "Overwhelmed" },
] as const;

export type Checkin = {
  id: number;
  checkin_date: string;
  mood: Mood;
  stress_level: number;
};

export const MOOD_LABEL = (mood: string) => MOODS.find((m) => m.value === mood)?.label ?? mood;
// The server records check-ins against its UTC calendar date, so "today" is compared the same way.

export const todayUtc = () => new Date().toISOString().slice(0, 10);
