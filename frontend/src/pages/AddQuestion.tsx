import * as Collapsible from "@radix-ui/react-collapsible";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, ClipboardPaste, Link2, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, api } from "@/api/client";
import type { ImportDraft, LookupResult, ProblemSummary, TestCase } from "@/api/types";
import { StatusIcon } from "@/pages/Library";
import { Button, Confirm, errorText, ErrorState, Field, HelpDialog, Notice, PageLoading, Select, Spinner, Toggle, useToast } from "@/components/ui";

type Editable = TestCase & { argsText: string; expectedText: string; localId: string; problem?: string };
const ORIGIN_LABEL: Record<string, string> = { example: "Imported example", provided: "Provided", generated: "Generated suggestion", learner: "Added by you" };
const STEPS = ["Choose how", "Add the question", "Review", "Tests"];
/** What each kind of generated test checks. Matches CATEGORY_PURPOSE in backend/app/imports/testgen.py. */
const CATEGORY: Record<string, { name: string; purpose: string }> = {
  normal: { name: "Typical", purpose: "An ordinary input, like the examples." },
  minimal: { name: "Smallest input", purpose: "The smallest input the task allows, where loops and boundaries often go wrong." },
  boundary: { name: "Boundary", purpose: "A value at the edge of what the constraints allow." },
  negative: { name: "Negative numbers", purpose: "Negative numbers, which catch code that assumes everything is positive." },
  zero: { name: "Zero", purpose: "A zero, which catches mistakes with starting values and division." },
  repeated: { name: "All the same", purpose: "The same value again and again, which catches code that assumes values differ." },
  duplicates: { name: "Duplicates", purpose: "Some values appear twice, which catches code that assumes they are all different." },
  sorted: { name: "Sorted", purpose: "Values already in order." },
  reverse_sorted: { name: "Reverse sorted", purpose: "Values in descending order, the opposite of what code often expects." },
  unsorted: { name: "Different order", purpose: "The same values in a different order, to check the order does not change the answer when it should not." },
  large: { name: "Large input", purpose: "A large input that only checks your code finishes in time." },
};
const FIELD_LABEL: Record<string, string> = { title: "title", description: "description", constraints: "constraints", input_format: "input format", output_format: "output format", examples: "examples", difficulty: "difficulty", tags: "topic tags" };
const fieldList = (fields: string[] | undefined) => (fields ?? []).map((field) => FIELD_LABEL[field] ?? field);

const toEditable = (test: TestCase, index: number): Editable => ({
  ...test, localId: test.id ?? `new-${index}-${Math.random().toString(36).slice(2, 7)}`,
  argsText: test.kind === "args" ? JSON.stringify(test.args ?? []) : test.stdin ?? "",
  expectedText: test.expected === null || test.expected === undefined ? "" : test.kind === "stdio" ? String(test.expected) : JSON.stringify(test.expected),
});

/** Turn the editable rows back into the API's format. Returns row errors rather than guessing. */
export function fromEditable(rows: Editable[]): { tests: TestCase[]; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const tests = rows.map((row) => {
    let args: unknown[] | null = null;
    let expected: unknown = null;
    if (row.kind === "args") {
      try {
        const parsed = JSON.parse(row.argsText || "[]");
        if (!Array.isArray(parsed)) throw new Error();
        args = parsed;
      } catch {
        errors[row.localId] = 'Arguments must be a JSON list, for example [1, 2] or ["abc"].';
      }
      if (row.expectedText.trim() && row.compare !== "completes") {
        try {
          expected = JSON.parse(row.expectedText);
        } catch {
          errors[row.localId] = 'The expected output must be JSON, for example 5, "abc", [1, 2] or null.';
        }
      }
    } else {
      expected = row.expectedText || null;
    }
    const hasExpected = row.compare === "completes" || row.expectedText.trim() !== "";
    return {
      id: row.id ?? null, label: row.label, origin: row.origin, category: row.category, kind: row.kind, args: row.kind === "args" ? args : null, stdin: row.kind === "stdio" ? row.argsText : null,
      expected, compare: row.compare, needs_expected: !hasExpected, enabled: hasExpected ? row.enabled : false, expected_source: row.expected_source ?? null,
    } as TestCase;
  });
  return { tests, errors };
}

function Stepper({ step }: { step: number }) {
  return (
    <ol className="stepper" aria-label="Progress">
      {STEPS.map((name, index) => (
        <li key={name} aria-current={index === step ? "step" : undefined} data-done={index < step}><span className="num">{index + 1}</span>{name}</li>
      ))}
    </ol>
  );
}

function ReviewForm({ draft, onChange }: { draft: ImportDraft; onChange: (draft: ImportDraft) => void }) {
  const units = useQuery<{ id: string; title: string }[]>({ queryKey: ["unit-options"], queryFn: () => api("/units/options"), staleTime: 300_000 });
  const set = <K extends keyof ImportDraft>(key: K, value: ImportDraft[K]) => onChange({ ...draft, [key]: value });
  const missing = draft.missing_fields ?? [];
  return (
    <div className="stack">
      {(draft.extracted_fields ?? []).length > 0 && <p className="muted" data-testid="found-fields"><strong>Found:</strong> {fieldList(draft.extracted_fields).join(", ")}.</p>}
      {missing.length > 0 && <Notice tone="warn" title="Some details are still needed"><span data-testid="missing-fields">Please add or check: {fieldList(missing).join(", ")}.</span> Nothing has been made up, so anything missing stays blank until you fill it in.</Notice>}
      {(draft.warnings ?? []).length > 0 && (
        <Notice tone="info" title="Please check">
          {(draft.warnings ?? []).length === 1 ? draft.warnings?.[0] : <ul style={{ paddingLeft: "1.1em", margin: 0 }}>{(draft.warnings ?? []).map((warning) => <li key={warning}>{warning}</li>)}</ul>}
        </Notice>
      )}
      {draft.source_url && <p className="subtle" data-testid="draft-source" style={{ overflowWrap: "anywhere" }}>Source: {draft.source_name}, {draft.source_url}{draft.source_retrieved_at ? `, retrieved ${new Date(draft.source_retrieved_at).toLocaleString()}` : ""}.</p>}
      <Field label="Title">{(p) => <input {...p} className="input" value={draft.title ?? ""} maxLength={160} onChange={(e) => set("title", e.target.value)} data-testid="draft-title" />}</Field>
      <Field label="Description" help="Formatting with Markdown is fine.">{(p) => <textarea {...p} className="textarea" rows={7} value={draft.description ?? ""} onChange={(e) => set("description", e.target.value)} data-testid="draft-description" />}</Field>
      <div className="grid-2">
        <Field label="Input format (optional)">{(p) => <textarea {...p} className="textarea" rows={2} value={draft.input_format ?? ""} onChange={(e) => set("input_format", e.target.value || null)} />}</Field>
        <Field label="Output format (optional)">{(p) => <textarea {...p} className="textarea" rows={2} value={draft.output_format ?? ""} onChange={(e) => set("output_format", e.target.value || null)} />}</Field>
      </div>
      <Field label="Constraints (optional)" help="Used to suggest edge cases, for example 1 <= n <= 100.">{(p) => <textarea {...p} className="textarea mono" rows={2} value={draft.constraints ?? ""} onChange={(e) => set("constraints", e.target.value || null)} />}</Field>
      <div className="grid-2">
        <div className="field"><span className="field-label">Difficulty</span><Select label="Difficulty" value={draft.difficulty ?? "unset"} onChange={(value) => set("difficulty", value === "unset" ? null : (value as ImportDraft["difficulty"]))} options={[{ value: "unset", label: "Not rated" }, { value: "easy", label: "Easy" }, { value: "medium", label: "Medium" }, { value: "hard", label: "Hard" }]} /></div>
        <div className="field"><span className="field-label">Topic</span><Select label="Topic" value={draft.unit_id ?? "arrays-two-pointers"} onChange={(value) => set("unit_id", value)} options={(units.data ?? []).map((u) => ({ value: u.id, label: u.title }))} /></div>
      </div>
      <div className="grid-2">
        <div className="field"><span className="field-label">How is it solved?</span><Select label="How is it solved?" value={draft.mode ?? "function"} onChange={(value) => set("mode", value as ImportDraft["mode"])} options={[{ value: "function", label: "Write a function" }, { value: "stdio", label: "Read input and print output" }]} /></div>
        <div className="field"><span className="field-label">Language</span><input className="input" value="Python" disabled aria-label="Language" /></div>
      </div>
      {draft.mode !== "stdio" && (
        <div className="grid-2">
          <Field label="Function name">{(p) => <input {...p} className="input mono" value={draft.function_name ?? ""} onChange={(e) => set("function_name", e.target.value || null)} data-testid="draft-function" />}</Field>
          <Field label="Parameters" help="Separated by commas.">{(p) => <input {...p} className="input mono" value={(draft.parameters ?? []).join(", ")} onChange={(e) => set("parameters", e.target.value.split(",").map((v) => v.trim()).filter(Boolean))} />}</Field>
        </div>
      )}
      <Field label="Tags (optional)" help="Separated by commas.">{(p) => <input {...p} className="input" value={(draft.tags ?? []).join(", ")} onChange={(e) => set("tags", e.target.value.split(",").map((v) => v.trim()).filter(Boolean))} />}</Field>
      <Field label="Your notes (optional)" help="A reminder for yourself. It is shown beside the question, and only to you.">{(p) => <textarea {...p} className="textarea" rows={2} maxLength={2000} value={draft.learner_notes ?? ""} onChange={(e) => set("learner_notes", e.target.value || null)} data-testid="draft-notes" />}</Field>
    </div>
  );
}

function TestsEditor({ rows, onChange, mode }: { rows: Editable[]; onChange: (rows: Editable[]) => void; mode: string }) {
  const update = (id: string, patch: Partial<Editable>) => onChange(rows.map((row) => (row.localId === id ? { ...row, ...patch } : row)));
  const remove = (id: string) => onChange(rows.filter((row) => row.localId !== id));
  const add = () => onChange([...rows, toEditable({ label: "My test", origin: "learner", kind: mode === "stdio" ? "stdio" : "args", args: mode === "stdio" ? null : [], stdin: mode === "stdio" ? "" : null, expected: null, compare: "exact", needs_expected: true, enabled: false, category: "normal" } as TestCase, rows.length)]);
  const needing = rows.filter((row) => row.compare !== "completes" && !row.expectedText.trim()).length;
  const count = (origin: string) => rows.filter((row) => row.origin === origin).length;
  const active = rows.filter((row) => row.enabled && (row.compare === "completes" || row.expectedText.trim())).length;
  return (
    <div className="stack">
      <Notice tone="info" title="These are your practice tests">
        Imported examples come from what you provided, and generated tests are only suggestions. These are <strong>not</strong> the original platform's hidden tests, so passing them does not mean the original site would accept your code.
      </Notice>
      <p className="muted" data-testid="test-summary"><strong>{active} test{active === 1 ? "" : "s"} will run:</strong> {count("example")} imported, {count("generated")} generated, {count("learner")} added by you.</p>
      {needing > 0 && <p className="muted">{needing} test{needing === 1 ? " needs" : "s need"} an expected output, and {needing === 1 ? "it stays" : "they stay"} off until you enter one. It is also fine to delete them.</p>}
      {rows.map((row) => {
        const missing = row.compare !== "completes" && !row.expectedText.trim();
        return (
          <div className="test-card" key={row.localId} data-enabled={row.enabled && !missing} data-testid="test-card">
            <div className="row-between">
              <div className="row">
                <strong>{row.label || "Test"}</strong>
                <span className={`badge ${row.origin === "generated" ? "badge-info" : ""}`}>{ORIGIN_LABEL[row.origin ?? "learner"]}</span>
                {missing && <span className="badge badge-warn" data-testid="needs-expected">Needs expected output</span>}
                {row.compare === "completes" && <span className="badge">Only checks it finishes in time</span>}
              </div>
              <div className="row">
                <label className="row subtle" style={{ gap: 6 }}>
                  On
                  <Toggle checked={row.enabled && !missing} onChange={(value) => update(row.localId, { enabled: value })} label={`Use test: ${row.label ?? "Test"}`} />
                </label>
                <Button size="small" variant="ghost" icon aria-label={`Delete test: ${row.label ?? "Test"}`} onClick={() => remove(row.localId)}><Trash2 size={14} aria-hidden /></Button>
              </div>
            </div>
            {row.origin === "generated" && row.category && CATEGORY[row.category] && (
              <p className="subtle test-purpose" data-testid="test-purpose"><strong>{CATEGORY[row.category].name}:</strong> {CATEGORY[row.category].purpose}</p>
            )}
            {row.compare === "completes" ? (
              <p className="subtle">Input with {row.argsText.length > 200 ? "a large list" : row.argsText}. Large inputs are not shown in full.</p>
            ) : (
              <div className="grid-2">
                <Field label={row.kind === "stdio" ? "Input (standard input)" : "Arguments (JSON list)"} error={row.problem ?? null}>
                  {(p) => <textarea {...p} className="textarea mono" rows={2} value={row.argsText} onChange={(e) => update(row.localId, { argsText: e.target.value, problem: undefined })} spellCheck={false} />}
                </Field>
                <Field label={row.kind === "stdio" ? "Expected output" : "Expected output (JSON)"}>
                  {(p) => <textarea {...p} className="textarea mono" rows={2} value={row.expectedText} onChange={(e) => update(row.localId, { expectedText: e.target.value, enabled: e.target.value.trim() ? true : row.enabled, problem: undefined })} spellCheck={false} data-testid="expected-input" />}
                </Field>
              </div>
            )}
          </div>
        );
      })}
      <div><Button onClick={add} data-testid="add-test"><Plus size={15} aria-hidden /> Add a test</Button></div>
    </div>
  );
}

function apiProblems(error: unknown): string[] {
  if (error instanceof ApiError && Array.isArray(error.details)) return (error.details as { message: string; label?: string; field?: string }[]).map((d) => (d.label ? `${d.label}: ${d.message}` : d.message));
  return [];
}

/** Every question this learner has added, in one place. They also appear in their topic on the Practice page. */
const PREVIOUS_OPEN_KEY = "codepath.add-question.previous-open";

/** Whether the list was left open earlier in this visit. A convenience only, so any storage failure means closed. */
function previousOpenAtStart(): boolean {
  try { return sessionStorage.getItem(PREVIOUS_OPEN_KEY) === "1"; } catch { return false; }
}

/** The learner's earlier questions, below the import area and closed until asked for. */
function PreviousQuestions() {
  const query = useQuery<ProblemSummary[]>({ queryKey: ["problems", "mine=true"], queryFn: () => api<ProblemSummary[]>("/problems?mine=true") });
  const [open, setOpen] = useState(previousOpenAtStart);
  const change = (next: boolean) => {
    setOpen(next);
    try { sessionStorage.setItem(PREVIOUS_OPEN_KEY, next ? "1" : "0"); } catch { /* remembering is optional */ }
  };
  const rows = query.data ?? [];
  const solved = rows.filter((r) => r.status === "solved").length;
  return (
    <Collapsible.Root open={open} onOpenChange={change} asChild>
      <section className="card previous-questions" data-testid="your-questions" data-open={open} aria-labelledby="previous-questions-heading">
        <h2 className="previous-heading" id="previous-questions-heading">
          <Collapsible.Trigger className="previous-trigger" data-testid="previous-toggle">
            <ChevronRight size={18} className="chevron" aria-hidden />
            <span className="grow">
              Previously added questions <span className="previous-count" data-testid="previous-count">({query.data ? rows.length : "…"})</span>{" "}
              <span className="subtle previous-summary">{query.data ? (rows.length ? `${solved} solved. Only you can see them.` : "None yet. Questions you add are kept here.") : "Loading…"}</span>
            </span>
          </Collapsible.Trigger>
        </h2>
        <Collapsible.Content className="previous-content">
          {query.isError && <ErrorState error={query.error} what="Your questions" onRetry={() => void query.refetch()} />}
          {query.data && rows.length === 0 && <p className="muted">Questions you paste or import are listed here, and in their topic on the Practice page.</p>}
          {rows.length > 0 && (
            <div className="practice-list">
              {rows.map((problem) => (
                <div key={problem.id} className="problem-row" data-testid="your-question">
                  <StatusIcon status={problem.status} />
                  <span className="grow">
                    <Link to={`/problems/${problem.id}`} className="problem-row-title">{problem.title}</Link><br />
                    <span className="subtle">{problem.unit_title}{problem.source_name && problem.source_name !== "Added by you" ? ` · from ${problem.source_name}` : ""}{problem.created_at ? ` · added ${new Date(problem.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}` : ""}</span>
                  </span>
                  {problem.difficulty && <span className={`badge badge-${problem.difficulty}`}>{problem.difficulty[0].toUpperCase() + problem.difficulty.slice(1)}</span>}
                  <Link to={`/problems/${problem.id}/edit`} className="btn btn-ghost btn-small" aria-label={`Edit ${problem.title}`}><Pencil size={14} aria-hidden /> Edit</Link>
                </div>
              ))}
            </div>
          )}
        </Collapsible.Content>
      </section>
    </Collapsible.Root>
  );
}

export function AddQuestion() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [method, setMethod] = useState<"paste" | "link">("paste");
  const [text, setText] = useState("");
  const [link, setLink] = useState("");
  const [lookupNote, setLookupNote] = useState<LookupResult | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [topic, setTopic] = useState("auto");
  const [learnerNotes, setLearnerNotes] = useState("");
  const units = useQuery<{ id: string; title: string }[]>({ queryKey: ["unit-options"], queryFn: () => api("/units/options"), staleTime: 300_000 });
  const [draft, setDraft] = useState<ImportDraft | null>(null);
  const [rows, setRows] = useState<Editable[]>([]);
  const [notes, setNotes] = useState<string[]>([]);

  const parse = useMutation({
    mutationFn: () => api<ImportDraft>("/imports/parse", { method: "POST", body: { text, source_url: sourceUrl.trim() || undefined, unit_id: topic === "auto" ? undefined : topic, notes: learnerNotes.trim() || undefined } }),
    onSuccess: (result) => {
      // Details from a link lookup, such as tags and rating, are kept when the pasted text does not have them.
      setDraft((current) => (current?.source_url ? {
        ...result, source_name: result.source_name ?? current.source_name, source_url: result.source_url ?? current.source_url, source_retrieved_at: current.source_retrieved_at, tags: current.tags?.length ? current.tags : result.tags,
        difficulty: result.difficulty ?? current.difficulty, title: result.title || current.title, unit_id: topic === "auto" ? current.unit_id ?? result.unit_id : result.unit_id,
      } : result));
      setStep(2);
    },
  });
  const lookup = useMutation({
    mutationFn: () => api<LookupResult>("/imports/lookup", { method: "POST", body: { query: link } }),
    onSuccess: (result) => { setLookupNote(result); setDraft(result.draft ?? null); setSourceUrl(result.draft?.source_url ?? ""); },
  });
  const generate = useMutation({
    mutationFn: (value: ImportDraft) => api<{ tests: TestCase[]; notes: string[] }>("/imports/generate-tests", { method: "POST", body: { draft: value } }),
    onSuccess: (result) => { setRows(result.tests.map(toEditable)); setNotes(result.notes); setStep(3); },
  });
  const save = useMutation({
    mutationFn: (payload: { draft: ImportDraft; tests: TestCase[] }) => api<{ id: string }>("/imports", { method: "POST", body: payload }),
    onSuccess: (result) => { void client.invalidateQueries({ queryKey: ["problems"] }); toast({ tone: "ok", title: "Question added", detail: "It is private to you." }); navigate(`/problems/${result.id}`); },
  });
  const saveAll = () => {
    if (!draft) return;
    const { tests, errors } = fromEditable(rows);
    if (Object.keys(errors).length) { setRows(rows.map((row) => ({ ...row, problem: errors[row.localId] }))); return; }
    save.mutate({ draft, tests });
  };
  const toPaste = () => { setMethod("paste"); setLookupNote(null); };
  const readable = lookupNote?.status === "extracted" || lookupNote?.status === "partial";
  const noteTitle: Record<string, string> = {
    extracted: `Read from ${lookupNote?.source_name}`, partial: `Partly read from ${lookupNote?.source_name}`, metadata_only: `Found: ${lookupNote?.draft?.title}`,
    url_only: lookupNote?.source_name ? `${lookupNote.source_name}: please paste the question` : "Please paste the question", failed: "That could not be imported just now", invalid: "That link could not be used",
  };
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}><div><h1>Add a question</h1><p>Bring in a problem from anywhere, and practise it with the same tutor. Only you can see it.</p></div></div>
      <Stepper step={step} />
      {step === 0 && (
        <section className="stack-s">
          <button type="button" className="choice" aria-pressed={method === "paste"} onClick={() => { setMethod("paste"); setStep(1); }} data-testid="method-paste">
            <ClipboardPaste size={20} aria-hidden /><span><strong>Paste question</strong><br /><span className="subtle">Always works, for a problem from any site. Copy the description, examples and constraints.</span></span>
          </button>
          <button type="button" className="choice" aria-pressed={method === "link"} onClick={() => { setMethod("link"); setStep(1); }} data-testid="method-link">
            <Link2 size={20} aria-hidden /><span><strong>Import from a link</strong><br /><span className="subtle">Enter any link or problem ID. CodePath reads what a site allows, shows you what it found and what is missing, and you finish the rest. Many coding sites do not allow automated reading, so you may be asked to paste.</span></span>
          </button>
        </section>
      )}
      {step === 1 && method === "paste" && (
        <form className="stack" onSubmit={(event) => { event.preventDefault(); parse.mutate(); }}>
          {draft?.source_url && <Notice tone="info" title={draft.title ? `Source saved: ${draft.title}` : "Source saved"}>Now paste the problem statement from {draft.source_name}, including its examples and constraints.</Notice>}
          {parse.isError && <Notice tone="danger">{errorText(parse.error)}</Notice>}
          <Field label="Problem text" help="Include the title, description, examples and constraints. You will be able to check and fix everything in the next step.">
            {(p) => <textarea {...p} className="textarea" rows={14} value={text} onChange={(e) => setText(e.target.value)} placeholder={"Two Sum\nGiven an array of integers nums and an integer target...\n\nExample 1:\nInput: nums = [2,7,11,15], target = 9\nOutput: [0,1]\n\nConstraints:\n2 <= nums.length <= 10^4"} data-testid="paste-text" />}
          </Field>
          <Collapsible.Root defaultOpen={false}>
            <Collapsible.Trigger className="collapsible-trigger" data-testid="optional-details"><ChevronRight size={15} className="chevron" aria-hidden /> Add a source, topic or notes (optional)</Collapsible.Trigger>
            <Collapsible.Content className="stack" style={{ paddingTop: 8 }}>
              <Field label="Source link" help="Where the question came from, for your reference. The page is not opened.">{(p) => <input {...p} className="input" type="url" inputMode="url" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="https://" data-testid="paste-source" />}</Field>
              <div className="field"><span className="field-label">Topic</span><Select label="Topic" value={topic} onChange={setTopic} options={[{ value: "auto", label: "Choose for me" }, ...(units.data ?? []).map((u) => ({ value: u.id, label: u.title }))]} /></div>
              <Field label="Notes" help="A reminder for yourself. It is shown only to you.">{(p) => <textarea {...p} className="textarea" rows={2} maxLength={2000} value={learnerNotes} onChange={(e) => setLearnerNotes(e.target.value)} data-testid="paste-notes" />}</Field>
            </Collapsible.Content>
          </Collapsible.Root>
          <div className="row"><Button variant="primary" type="submit" disabled={text.trim().length < 20 || parse.isPending} data-testid="parse">{parse.isPending ? "Reading…" : "Read this question"}</Button><Button variant="ghost" onClick={() => setStep(0)}>Back</Button></div>
        </form>
      )}
      {step === 1 && method === "link" && (
        <form className="stack" onSubmit={(event) => { event.preventDefault(); lookup.mutate(); }}>
          <Field label="Link or problem ID" help="A full link from any site, or an ID such as 1872A (Codeforces) or abc300_a (AtCoder). Only pages a site allows are read.">
            {(p) => <input {...p} className="input" value={link} onChange={(e) => { setLink(e.target.value); setLookupNote(null); }} data-testid="link-input" />}
          </Field>
          {lookup.isError && <Notice tone="danger">{errorText(lookup.error)}</Notice>}
          {lookup.isPending && <p className="row muted" role="status"><Spinner /> Checking what this site allows, then reading the page…</p>}
          {lookupNote && !lookup.isPending && (
            <Notice tone={readable && lookupNote.status === "extracted" ? "ok" : readable || lookupNote.status === "metadata_only" ? "info" : "warn"} title={noteTitle[lookupNote.status ?? "failed"]}>
              <div data-testid="lookup-result" data-status={lookupNote.status} data-reason={lookupNote.reason_code ?? undefined} className="stack-s">
                <p>{lookupNote.message}</p>
                {(lookupNote.extracted_fields ?? []).length > 0 && <p><strong>Found:</strong> {fieldList(lookupNote.extracted_fields).join(", ")}.</p>}
                {(lookupNote.missing_fields ?? []).length > 0 && <p><strong>Still needed:</strong> {fieldList(lookupNote.missing_fields).join(", ")}.</p>}
                {!readable && lookupNote.guidance && <p>{lookupNote.guidance}</p>}
                <div className="row">
                  {readable
                    ? <Button size="small" variant="primary" onClick={() => setStep(2)} data-testid="continue-review">Review and complete</Button>
                    : lookupNote.draft
                      ? <Button size="small" variant="primary" onClick={toPaste} data-testid="continue-paste">Paste the statement</Button>
                      : <Button size="small" variant="primary" onClick={toPaste} data-testid="switch-to-paste">Paste the question instead</Button>}
                  {readable && <Button size="small" variant="ghost" onClick={toPaste}>Paste it myself instead</Button>}
                </div>
              </div>
            </Notice>
          )}
          <div className="row"><Button variant={lookupNote ? undefined : "primary"} type="submit" disabled={link.trim().length < 2 || lookup.isPending} data-testid="lookup">{lookup.isPending ? "Looking up…" : lookupNote ? "Try again" : "Look up"}</Button><Button variant="ghost" onClick={() => setStep(0)}>Back</Button></div>
        </form>
      )}
      {step === 2 && draft && (
        <section className="stack">
          <h2>Check the details</h2>
          <ReviewForm draft={draft} onChange={setDraft} />
          {generate.isError && <Notice tone="danger">{errorText(generate.error)}</Notice>}
          <div className="row"><Button variant="primary" onClick={() => generate.mutate(draft)} disabled={generate.isPending} data-testid="to-tests">{generate.isPending ? "Preparing…" : "Continue to tests"}</Button><Button variant="ghost" onClick={() => setStep(1)}>Back</Button></div>
        </section>
      )}
      {step === 3 && draft && (
        <section className="stack">
          <div className="row" style={{ gap: 2 }}>
            <h2>Check the tests</h2>
            <HelpDialog title="How are tests chosen?">
              <p>Examples come straight from what you pasted. Generated tests suggest unusual inputs, such as empty lists or boundary values, based on your examples and constraints.</p>
              <p>A correct answer for a generated input cannot be known for sure, so you enter it yourself. Until then, the test stays off.</p>
            </HelpDialog>
          </div>
          {notes.filter((note) => !note.startsWith("Generated tests are suggestions")).map((note) => <p className="subtle" key={note}>{note}</p>)}
          <TestsEditor rows={rows} onChange={setRows} mode={draft.mode ?? "function"} />
          {save.isError && <Notice tone="danger" title={errorText(save.error)}>{apiProblems(save.error).length > 0 && <ul>{apiProblems(save.error).map((m) => <li key={m}>{m}</li>)}</ul>}</Notice>}
          <div className="row"><Button variant="primary" onClick={saveAll} disabled={save.isPending} data-testid="save-question">{save.isPending ? "Saving…" : "Save and start practising"}</Button><Button variant="ghost" onClick={() => setStep(2)}>Back</Button></div>
        </section>
      )}
      <PreviousQuestions />
    </div>
  );
}

export function EditQuestion() {
  const { problemId = "" } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const toast = useToast();
  const query = useQuery<{ id: string; draft: ImportDraft; tests: TestCase[] }>({ queryKey: ["import", problemId], queryFn: () => api(`/imports/${problemId}`) });
  const [draft, setDraft] = useState<ImportDraft | null>(null);
  const [rows, setRows] = useState<Editable[]>([]);
  useEffect(() => { if (query.data) { setDraft(query.data.draft); setRows(query.data.tests.map(toEditable)); } }, [query.data]);
  const save = useMutation({
    mutationFn: (payload: { draft: ImportDraft; tests: TestCase[] }) => api(`/imports/${problemId}`, { method: "PUT", body: payload }),
    onSuccess: () => { for (const key of ["workspace", "problems", "import"]) void client.invalidateQueries({ queryKey: [key] }); toast({ tone: "ok", title: "Saved" }); navigate(`/problems/${problemId}`); },
  });
  const remove = useMutation({
    mutationFn: () => api(`/imports/${problemId}`, { method: "DELETE" }),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ["problems"] }); toast({ tone: "ok", title: "Question deleted" }); navigate("/problems"); },
    onError: (error) => toast({ tone: "error", title: "It could not be deleted", detail: errorText(error) }),
  });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !draft) return <ErrorState error={query.error} what="This question" onRetry={() => void query.refetch()} />;
  const saveAll = () => {
    const { tests, errors } = fromEditable(rows);
    if (Object.keys(errors).length) { setRows(rows.map((row) => ({ ...row, problem: errors[row.localId] }))); return; }
    save.mutate({ draft, tests });
  };
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}><div><h1>Edit your question</h1><p>Only you can see this question.</p></div>
        <Confirm trigger={<Button data-testid="delete-question"><Trash2 size={15} aria-hidden /> Delete</Button>} title="Delete this question?" description="This removes the question and all your attempts on it. This cannot be undone." confirmLabel="Delete question" onConfirm={() => remove.mutate()} destructive />
      </div>
      <ReviewForm draft={draft} onChange={setDraft} />
      <h2>Tests</h2>
      <TestsEditor rows={rows} onChange={setRows} mode={draft.mode ?? "function"} />
      {save.isError && <Notice tone="danger" title={errorText(save.error)}>{apiProblems(save.error).length > 0 && <ul>{apiProblems(save.error).map((m) => <li key={m}>{m}</li>)}</ul>}</Notice>}
      <div className="row"><Button variant="primary" onClick={saveAll} disabled={save.isPending} data-testid="save-edit">Save changes</Button><Button variant="ghost" onClick={() => navigate(`/problems/${problemId}`)}>Cancel</Button></div>
    </div>
  );
}
