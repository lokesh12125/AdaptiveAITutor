import type { components } from "./schema";

type S = components["schemas"];
export type User = S["UserOut"];
export type ProblemSummary = S["ProblemSummary"];
export type ProblemDetail = S["ProblemDetail"];
export type Evaluation = S["EvaluationOut"];
export type Run = S["RunOut"];
export type Stage = S["StageOut"];
export type Workspace = S["WorkspaceOut"];
export type HintRow = S["HintRow"];
export type Path = S["PathOut"];
export type PathUnit = S["UnitPathItem"];
export type UnitDetail = S["UnitDetail"];
export type Status = S["StatusOut"];
export type ImportDraft = S["ImportDraft"];
export type TestCase = S["TestCase"];
export type LookupResult = S["LookupOut"];
export type Assessment = S["AssessmentOut"];
export type ClassInfo = S["ClassOut"];

export type Plan = {
  action: string; title: string; reason: string; reason_codes?: string[]; problem_id: string | null; problem_title: string | null;
  unit_id: string | null; unit_title: string | null; keep_current_active: boolean;
  alternatives: { action: string; title: string; unit_id: string | null; problem_id: string | null }[];
};

export type TestResult = {
  id: string; name: string; visibility: "public" | "hidden"; passed: boolean | null; category: string; origin?: string; input?: string; expected?: string | null;
  actual?: string | null; stdout?: string; stderr?: string; truncated?: boolean; duration_ms?: number; status?: string;
  error?: { type: string; message: string; line: number | null; column?: number | null };
};

/** One coordinated tutor response (backend: tutoring/compose.py). */
export type TutorResponse = {
  verdict: string;
  what_happened: { title: string; detail: string };
  next_action: { kind: string; label: string; detail: string; problem_id: string | null };
  tutor: null | { hint_id: string; level: number; level_name: string; format: string; text: string; source: "ai" | "built_in"; source_note: string | null; why: string; one_action: boolean };
  offer: null | { label: string; why: string };
  diagnostics: { category: string; issue_key: string; facts: { text: string; line: number | null; source: string }[]; possible_causes: { text: string; confidence: string }[]; lines: number[]; uncertain: boolean };
  reflection: null | { id: string; prompt: string };
  plan: Plan | null;
  estimates: null | {
    unit_id: string; mastery_low: number; mastery_high: number; mastery_band: string; mastery_note: string; progress: string | null; progress_notes: string[];
    confusion: string | null; confusion_notes: string[]; load: string | null; load_notes: string[]; confidence: number | null;
  };
  retrieval_used: boolean;
  retrieval_demo_data: boolean;
  snapshot_id: string;
  graded: boolean;
};

export type Preferences = {
  theme?: "system" | "light" | "dark"; editor_font_size?: number; editor_tab_size?: number; editor_line_wrap?: boolean; editor_line_numbers?: boolean; motion?: "system" | "reduced";
  density?: "comfortable" | "compact"; show_walkthroughs?: boolean; auto_hints?: boolean; share_anonymous_outcomes?: boolean; show_estimates?: boolean; syntax_feedback?: boolean;
};
