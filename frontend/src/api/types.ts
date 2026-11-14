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
  route?: RouteStep[];
};

/** Where the learner is, then the topics ahead. "secure" means the planner considers the topic done. */
export type RouteStep = { unit_id: string; title: string; solved: number; total: number; status: "now" | "secure" | "next" };

export type ReflectionAnswer = { status: string; quality: "specific" | "partial" | "unsure" | "brief"; feedback: string; matched: string[]; next: Plan | null };

export type TestResult = {
  id: string; name: string; visibility: "public" | "hidden"; passed: boolean | null; category: string; origin?: string; input?: string; expected?: string | null;
  actual?: string | null; stdout?: string; stderr?: string; truncated?: boolean; duration_ms?: number; status?: string; note?: string;
  error?: { type: string; message: string; line: number | null; column?: number | null };
};

/** One coordinated tutor response (backend: tutoring/compose.py). */
export type TutorResponse = {
  verdict: string;
  what_happened: { title: string; detail: string };
  next_action: { kind: string; label: string; detail: string; problem_id: string | null };
  progress_note: string | null;
  tutor: null | {
    hint_id: string; level: number; level_name: string; format: string; text: string; source: "ai" | "built_in"; source_note: string | null; why: string; why_details: { label: string; value: string }[];
    one_action_at_a_time: boolean; strategy: string; strategy_label: string; hint_number: number | null; question: string | null; focus: { start: number; end: number; auto: boolean } | null; topic_id: string | null; concept?: string | null;
  };
  waiting: null | { title: string; detail: string; try_next: string; snapshot_id: string };
  offer: null | { label: string; why: string; lead?: string | null };
  diagnostics: {
    category: string; issue_key: string; facts: { text: string; line: number | null; source: string }[]; possible_causes: { text: string; confidence: string }[]; lines: number[]; uncertain: boolean;
    diagnosis?: null | { error_class: string; location: number | null; confidence: number; explanation: string; evidence: string[]; likely_cause?: string; concept?: string };
    comparison?: { has_previous?: boolean; same_issue?: boolean; changed_lines?: number[]; moved_further?: boolean; tests_delta?: number | null };
  };
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

/** A topic's lesson (content/guides). */
export type Guide = {
  reading_minutes: number; overview: string; you_will_learn: string[]; before_you_start: string[];
  sections: { id: string; title: string; body: string; examples?: { title: string; code: string; note?: string }[] }[];
  patterns: { name: string; when: string; how: string }[]; mistakes: { mistake: string; fix: string }[]; key_ideas: string[];
  why?: string; definitions?: Term[]; how_it_works?: string[]; diagram?: { caption: string; text: string }; edge_cases?: string[];
  complexity?: { operation: string; cost: string }[]; when_to_use?: string[]; related?: string[]; summary?: string; glossary?: Term[];
  checks?: { question: string; options: string[]; answer: number; why: string }[];
};
export type Term = { term: string; meaning: string };
export type LearningMode = "guided" | "practice" | "revision" | "interview";

/** The Learn panel beside a problem (backend: learning.py). */
export type ProblemLearning = {
  summary: string; asking: string;
  shape: { mode: "function" | "program"; inputs: { name: string; kind: string }[]; output: { kind: string; example: string | null } };
  observations: string[]; constraints: { text: string; means: string }[];
  worked_example: null | { input: string; expected: string | null; facts: string[]; steps: string[] };
  technique: { name: string; idea: string | null; when: string | null; how: string | null };
  approaches: { level: string; idea: string; intuition: string[]; steps: string[]; time: string; space: string; time_reason: string | null; space_reason: string | null; main: boolean }[];
  mistakes: string[]; edge_cases: string[];
  concept: { unit_id: string; unit_title: string; section: { id: string; title: string } | null; definitions: Term[]; key_ideas: string[] };
  prerequisites: { topics: { id: string; title: string }[]; know_first: string[] };
  related: { id: string; title: string; difficulty: string | null; pattern: string | null; same_technique: boolean; status: ProblemSummary["status"] }[];
  hint_stages: { name: string; detail: string }[];
  revision: { idea: string | null; summary: string | null };
};
/** A learner's profile (backend: profile.py). */
export type Profile = {
  user: { name: string; joined: string; experience: string | null; goal: string | null; is_demo: boolean };
  totals: {
    solved: number; started: number; submitted: number; completion_rate: number | null; submissions: number; accepted_submissions: number; acceptance_rate: number | null; runs: number;
    hints_total: number; hints_per_solved: number | null; first_try_solves: number; solved_without_hints: number; solved_by_difficulty: Record<"easy" | "medium" | "hard", [number, number]>;
    questions_added: number; active_minutes: number; days_active: number; current_streak: number; longest_streak: number; topics_with_solves: number;
  };
  calendar: { date: string; count: number }[];
  improvement: {
    then_now: null | { count: number; rows: { label: string; early: number | null; recent: number | null; better: boolean | null; unit: string }[] };
    weekly: { week_start: string; solved: number; submissions: number }[];
    knowledge_checks: { available: boolean; mean_normalised_gain: number | null };
  };
  state_matrix: {
    unit_id: string; title: string; solved: number; total: number; graded_attempts: number; independent_solved: number; assisted_solved: number; mastery: number | null; mastery_low: number | null;
    mastery_high: number | null; band: string; evidence_weight: number; starting_mastery: number | null; confidence: number | null; confusion: string | null; load: string | null; progress: string | null; updated_at: string | null;
  }[];
  vector: null | { version: string; problem: string | null; at: string; features: { name: string; meaning: string; value: number; raw: string | null }[] };
  similar: null | { matched: boolean; support: number | null; effectiveness: number | null; reason: string | null; demo_data: boolean; at: string };
  milestones: { id: string; title: string; achieved: boolean }[];
  recent: { problem_id: string; title: string | null; verdict: string | null; passed: number; total: number; at: string }[];
};
export type SubmissionRow = {
  id: string; created_at: string; status: string; verdict: string | null; passed: number; total: number; duration_ms: number | null; code: string;
  first_failure: { name: string | null; category: string | null } | null;
};
export type SearchResults = {
  topics: { id: string; title: string; where: string; text: string; section: string | null }[];
  problems: { id: string; title: string; difficulty: string | null; pattern: string | null; unit_title: string; unit_id: string }[];
};
export type TopicNotes = { key_ideas: string[]; pattern: { name: string; when: string; how: string } | null; mistakes: { mistake: string; fix: string }[] };

export type Preferences = {
  theme?: "system" | "light" | "dark"; editor_font_size?: number; editor_tab_size?: number; editor_line_wrap?: boolean; editor_line_numbers?: boolean; motion?: "system" | "reduced";
  density?: "comfortable" | "compact"; learning_mode?: LearningMode; show_walkthroughs?: boolean; auto_hints?: boolean; share_anonymous_outcomes?: boolean; show_estimates?: boolean; syntax_feedback?: boolean;
};
