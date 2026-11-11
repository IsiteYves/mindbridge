// Mirrors backend/app/services/passwords.py. The server is the authority; this only gives instant feedback.
export const PASSWORD_RULES: { label: string; test: (password: string) => boolean }[] = [
  { label: "At least 6 characters", test: (password) => password.length >= 6 },
  { label: "An uppercase letter", test: (password) => /[A-Z]/.test(password) },
  { label: "A lowercase letter", test: (password) => /[a-z]/.test(password) },
  { label: "A special character (for example ! or #)", test: (password) => /[^A-Za-z0-9]/.test(password) },
];

export function unmetPasswordRules(password: string): string[] {
  return PASSWORD_RULES.filter((rule) => !rule.test(password)).map((rule) => rule.label);
}
