export function timeAgo(value: string | null | undefined): string {
  if (!value) return "never";
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} hr ago`;
  const days = Math.round(seconds / 86400);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "No data yet";
  if (seconds < 60) return `${seconds} sec`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} min` : `${(minutes / 60).toFixed(1)} hr`;
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "No data yet" : `${Math.round(value * 100)}%`;
}

/** Estimates are shown in steps of 5, since finer numbers would imply precision they do not have. */
export function roundedRange(low: number | null | undefined, high: number | null | undefined): string {
  if (low === null || low === undefined || high === null || high === undefined) return "";
  const step = (v: number) => Math.round((v * 100) / 5) * 5;
  return `${step(low)}–${step(high)}%`;
}

export const DIFFICULTY_LABEL: Record<string, string> = { easy: "Easy", medium: "Medium", hard: "Hard" };

export const VERDICT_LABEL: Record<string, string> = {
  accepted: "All tests passed", partial: "Partly correct", wrong_answer: "Wrong answer", syntax_error: "Syntax error", runtime_error: "Error while running", timeout: "Took too long",
  memory_limit: "Too much memory", output_limit: "Too much output", missing_function: "Function not found", public_passed: "Examples pass", ran: "Ran", no_tests: "No tests yet", service_failure: "Could not check", cancelled: "Cancelled",
};

export const CATEGORY_LABEL: Record<string, string> = {
  passed: "Passed", wrong_answer: "Wrong answer", runtime_error: "Error while running", timeout: "Took too long", memory_limit: "Too much memory", output_limit: "Too much output",
  missing_function: "Function not found", syntax_error: "Syntax error", skipped: "Not run", output_only: "Output",
};

export const ESTIMATE_WORDS: Record<string, string> = { low: "Low", moderate: "Moderate", high: "High" };
export const PROGRESS_WORDS: Record<string, string> = { improving: "Improving", steady: "Steady", stalled: "Stalled", regressing: "Fewer tests passing", solved: "Solved", unknown: "Not enough evidence yet" };
