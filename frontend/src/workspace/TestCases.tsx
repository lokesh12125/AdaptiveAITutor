import { EyeOff, Plus, RotateCcw, X } from "lucide-react";
import { useState } from "react";

import type { ProblemDetail } from "@/api/types";
import { Button } from "@/components/ui";

export type CaseState = { key: string; testId: string | null; values: string[]; expected: string | null; editable: boolean; edited: boolean };
export const MAX_CASES = 8;

export function initialCases(problem: ProblemDetail): CaseState[] {
  return (problem.sample_cases ?? []).map((sample) => ({
    key: sample.id, testId: sample.id, values: sample.params.map((param) => param.value), expected: sample.expected, editable: sample.editable, edited: false,
  }));
}

/** Whether the learner changed anything, so Run should use these cases rather than the stored examples. */
export function casesChanged(problem: ProblemDetail, cases: CaseState[]): boolean {
  const samples = problem.sample_cases ?? [];
  return cases.length !== samples.length || cases.some((item, index) => item.edited || item.testId !== samples[index]?.id);
}

/** The cases to send with Run: an unchanged example by id, or the learner's own values. */
export function casesForRun(problem: ProblemDetail, cases: CaseState[]): { test_id?: string; args?: string[]; stdin?: string }[] {
  return cases.map((item) => {
    if (item.testId && !item.edited) return { test_id: item.testId };
    return problem.mode === "stdio" ? { stdin: item.values[0] ?? "" } : { args: item.values };
  });
}

/** The test cases, shown before running, as on most coding sites. Examples can be edited, and new cases added. */
export function TestCases({ problem, cases, onChange, disabled }: { problem: ProblemDetail; cases: CaseState[]; onChange: (cases: CaseState[]) => void; disabled: boolean }) {
  const [view, setView] = useState<"sample" | "hidden">("sample");
  const [selected, setSelected] = useState(0);
  const index = Math.min(selected, Math.max(0, cases.length - 1));
  const current = cases[index];
  const names = problem.param_names?.length ? problem.param_names : current?.values.map((_, i) => `input ${i + 1}`) ?? [];
  const editable = (problem.sample_cases ?? []).some((sample) => sample.editable) || (problem.sample_cases ?? []).length === 0 && names.length > 0;
  const changed = casesChanged(problem, cases);

  const update = (position: number, value: string) => {
    onChange(cases.map((item, i) => (i === index ? { ...item, values: item.values.map((old, j) => (j === position ? value : old)), edited: true } : item)));
  };
  const add = () => {
    const base = current ?? { values: names.map(() => ""), editable: true };
    onChange([...cases, { key: `new-${Date.now()}`, testId: null, values: [...base.values], expected: null, editable: true, edited: true }]);
    setSelected(cases.length);
  };
  const remove = (position: number) => {
    onChange(cases.filter((_, i) => i !== position));
    setSelected(Math.max(0, position - 1));
  };

  return (
    <section className="testcases" aria-label="Test cases" data-testid="testcases">
      <div className="testcase-views" role="tablist" aria-label="Which tests">
        <button type="button" role="tab" aria-selected={view === "sample"} className="testcase-view" onClick={() => setView("sample")} data-testid="cases-sample">Sample</button>
        <button type="button" role="tab" aria-selected={view === "hidden"} className="testcase-view" onClick={() => setView("hidden")} data-testid="cases-hidden">Hidden <span className="tab-count">{problem.hidden_test_count}</span></button>
      </div>
      {view === "hidden" ? (
        <div className="stack-s" data-testid="hidden-note">
          <div className="testcase-hidden">
            <EyeOff size={18} aria-hidden />
            <p>{problem.hidden_test_count} hidden test{problem.hidden_test_count === 1 ? "" : "s"} check your code when you press <strong>Submit</strong>. You will see how many pass, but not their inputs, so passing them shows your code works in general, not just on the examples.</p>
          </div>
          {(problem.hidden_test_categories ?? []).length > 0 && (
            <>
              <p className="field-label">What they cover</p>
              <ul className="hidden-categories" data-testid="hidden-categories">
                {(problem.hidden_test_categories ?? []).map((item) => (
                  <li key={String(item.category)} data-testid="hidden-category">
                    <span className="hidden-category-name">{String(item.category)[0].toUpperCase() + String(item.category).slice(1)} <span className="tab-count">{String(item.count)}</span></span>
                    <span className="subtle">{String(item.purpose)}</span>
                  </li>
                ))}
              </ul>
              <p className="subtle">Most were generated from the task's own examples, with answers from a checked solution. They are this site's tests, not any other platform's.</p>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="case-tabs" role="group" aria-label="Cases">
            {cases.map((item, i) => (
              <span key={item.key} className="case-tab-wrap">
                <button type="button" aria-pressed={i === index} className="case-tab" onClick={() => setSelected(i)} data-testid="case-tab">
                  Case {i + 1}{item.edited ? <span className="case-dot" aria-label="changed" /> : null}
                </button>
                {cases.length > 1 && (!item.testId || item.edited) && <button type="button" className="case-remove" aria-label={`Remove case ${i + 1}`} onClick={() => remove(i)}><X size={12} aria-hidden /></button>}
              </span>
            ))}
            {editable && <Button variant="ghost" size="small" icon aria-label="Add a test case" disabled={disabled || cases.length >= MAX_CASES} onClick={add} data-testid="add-case"><Plus size={16} aria-hidden /></Button>}
            <span className="grow" />
            {changed && <Button variant="ghost" size="small" onClick={() => { onChange(initialCases(problem)); setSelected(0); }} data-testid="reset-cases"><RotateCcw size={13} aria-hidden /> Reset</Button>}
          </div>
          {current ? (
            <div className="case-body stack-s">
              <span className="row-between">
                <span className="field-label">Input</span>
                <span className="badge" data-testid="case-source">{current.testId && !current.edited ? "Example from the task" : "Your own case"}</span>
              </span>
              {names.map((name, position) => (
                <label key={name} className="case-field">
                  <span className="case-name">{name}</span>
                  {current.editable ? (
                    <textarea
                      className="textarea mono case-input" rows={Math.min(6, Math.max(1, (current.values[position] ?? "").split("\n").length))} spellCheck={false}
                      value={current.values[position] ?? ""} onChange={(event) => update(position, event.target.value)} data-testid="case-input" aria-label={`Case ${index + 1}, ${name}`}
                    />
                  ) : <pre className="case-readonly">{current.values[position]}</pre>}
                </label>
              ))}
              {current.expected !== null && !current.edited
                ? <p className="subtle">Expected: <code data-testid="case-expected">{current.expected}</code></p>
                : <p className="subtle" data-testid="case-expected-later">The expected answer for this case is worked out when you press Run.</p>}
              {!current.editable && <p className="subtle">This example uses a structure built for you, so it cannot be edited here.</p>}
            </div>
          ) : <p className="muted">This problem has no examples to show yet.</p>}
        </>
      )}
    </section>
  );
}
