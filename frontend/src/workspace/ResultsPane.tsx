import * as Collapsible from "@radix-ui/react-collapsible";
import { Ban, Check, CheckCircle2, ChevronRight, CircleAlert, Clock, EyeOff, RotateCw, ServerCrash, Terminal, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { Evaluation, ProblemDetail, Run, Stage, TestResult, TutorResponse } from "@/api/types";
import { Button, CopyButton, HelpDialog, Notice, Spinner } from "@/components/ui";
import { CATEGORY_LABEL, ESTIMATE_WORDS, PROGRESS_WORDS, roundedRange, VERDICT_LABEL } from "@/lib/format";
import { useSession } from "@/lib/session";

import { type CaseState, TestCases } from "./TestCases";

export const STAGE_LABEL: Record<string, string> = {
  intake: "Reading your request", evaluate: "Running your code in the sandbox", diagnostic: "Working out what happened", cognitive_state: "Updating your progress estimates", retrieval: "Looking for similar situations",
  dsda: "Choosing how much help fits", generate_hint: "Writing the hint", validate_hint: "Checking the hint is safe and on topic", reflection: "Deciding whether to ask a question", planner: "Planning your next step", finalize: "Saving the results",
};

function toneFor(verdict: string | null | undefined): { tone: string; Icon: typeof Check } {
  if (verdict === "accepted") return { tone: "ok", Icon: CheckCircle2 };
  if (verdict === "public_passed" || verdict === "partial" || verdict === "ran") return { tone: "progress", Icon: CheckCircle2 };
  if (verdict === "service_failure") return { tone: "service", Icon: ServerCrash };
  if (verdict === "cancelled") return { tone: "service", Icon: Ban };
  if (verdict === "timeout") return { tone: "fail", Icon: Clock };
  return { tone: "fail", Icon: CircleAlert };
}

function TestRow({ test, defaultOpen }: { test: TestResult; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const expandable = test.visibility === "public";
  const passedKnown = test.passed !== null && test.passed !== undefined;
  const StateIcon = test.visibility === "hidden" && test.passed ? Check : test.passed ? Check : passedKnown ? X : Terminal;
  return (
    <li className="test-row">
      <button type="button" className="test-row-head" data-pass={passedKnown ? String(test.passed) : undefined} disabled={!expandable} aria-expanded={expandable ? open : undefined} onClick={() => setOpen(!open)}>
        <StateIcon size={15} className="state" aria-hidden />
        <span className="grow">{test.name}</span>
        <span className="subtle">{passedKnown ? (test.passed ? "Passed" : CATEGORY_LABEL[test.category] ?? "Did not pass") : "Output"}</span>
        {test.origin === "generated" && <span className="badge badge-info">Generated</span>}
        {test.origin === "learner" && test.passed !== null && <span className="badge">Added by you</span>}
        {expandable ? <ChevronRight size={14} className="chevron" style={{ transform: open ? "rotate(90deg)" : undefined }} aria-hidden /> : <EyeOff size={13} aria-label="Hidden test" />}
      </button>
      {expandable && open && (
        <dl className="test-detail">
          <dt>Input</dt><dd>{test.input}</dd>
          {test.expected !== null && test.expected !== undefined && <><dt>Expected</dt><dd>{test.expected}</dd></>}
          {test.actual !== null && test.actual !== undefined && <><dt>Your result</dt><dd>{test.actual}</dd></>}
          {test.error && <><dt>Error</dt><dd>{test.error.type}{test.error.message ? `: ${test.error.message}` : ""}{test.error.line ? ` (line ${test.error.line})` : ""}</dd></>}
          {test.stdout && <><dt>Printed <CopyButton text={test.stdout} label="Copy the output" /></dt><dd>{test.stdout}{test.truncated ? "\n… output was cut off at the limit" : ""}</dd></>}
          {test.stderr && <><dt>Error output</dt><dd>{test.stderr}</dd></>}
          {test.note && <><dt>Note</dt><dd style={{ fontFamily: "var(--font-ui)" }}>{test.note}</dd></>}
        </dl>
      )}
    </li>
  );
}

export function StageList({ stages }: { stages: Stage[] }) {
  const visible = stages.filter((s) => s.stage !== "intake");
  return (
    <ul className="stages">
      {visible.map((stage, index) => (
        <li key={`${stage.stage}-${index}`} data-status={stage.status}>
          {stage.status === "running" ? <span className="spinner" aria-hidden /> : stage.status === "completed" ? <Check aria-hidden /> : stage.status === "failed" || stage.status === "fallback" ? <CircleAlert aria-hidden /> : <ChevronRight aria-hidden />}
          <span className="grow">{STAGE_LABEL[stage.stage] ?? stage.stage}{stage.reason ? <span className="subtle"> · {stage.reason}</span> : null}</span>
          {stage.status === "skipped" && <span className="subtle">Skipped</span>}
          {stage.status === "deferred" && <span className="subtle">Later</span>}
        </li>
      ))}
    </ul>
  );
}

function Tests({ results }: { results: TestResult[] }) {
  const visible = results.filter((r) => r.visibility === "public");
  const hidden = results.filter((r) => r.visibility === "hidden");
  const hiddenPassed = hidden.filter((r) => r.passed).length;
  const firstFail = visible.find((r) => r.passed === false)?.id;
  const hiddenFailures = hidden.filter((r) => !r.passed);
  if (results.length === 0) return null;
  return (
    <section className="stack-s" aria-label="Test results">
      <div className="row" style={{ gap: 2 }}>
        <h3>Tests</h3>
        <HelpDialog title="What do these results mean?">
          <p><strong>Examples</strong> show the input, the expected answer and your result, so you can compare them.</p>
          <p><strong>Hidden tests</strong> only show whether they passed and the broad kind of problem, so passing them shows your code handles the general task.</p>
        </HelpDialog>
      </div>
      <ul className="stack-s" style={{ listStyle: "none", padding: 0, gap: 6 }}>
        {visible.map((test) => <TestRow key={test.id} test={test} defaultOpen={test.id === firstFail || test.passed === null} />)}
      </ul>
      {hidden.length > 0 && (
        <Collapsible.Root>
          <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Hidden tests: {hiddenPassed} of {hidden.length} passed</Collapsible.Trigger>
          <Collapsible.Content>
            <ul className="stack-s" style={{ listStyle: "none", padding: 0, gap: 6 }}>{hidden.map((test) => <TestRow key={test.id} test={test} defaultOpen={false} />)}</ul>
          </Collapsible.Content>
        </Collapsible.Root>
      )}
      {hiddenFailures.length > 0 && visible.every((r) => r.passed) && <p className="subtle">Your examples pass, so try unusual inputs such as empty, one item, or repeated values.</p>}
    </section>
  );
}

function Details({ response, run, evaluation }: { response: TutorResponse | null; run: Run | null; evaluation: Evaluation | null }) {
  const { preferences } = useSession();
  const diagnostics = response?.diagnostics;
  const estimates = response?.estimates;
  const hasDiagnostics = !!diagnostics && (diagnostics.facts.length > 0 || diagnostics.possible_causes.length > 0);
  return (
    <Collapsible.Root>
      <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> More detail</Collapsible.Trigger>
      <Collapsible.Content className="stack" style={{ paddingTop: 6 }}>
        {hasDiagnostics && (
          <section className="stack-s">
            <h3>What we observed</h3>
            <ul>{diagnostics.facts.map((fact, i) => <li key={i}>{fact.text}</li>)}</ul>
            {diagnostics.possible_causes.length > 0 && (
              <>
                <h3 style={{ marginTop: 6 }}>Possible cause</h3>
                <ul>{diagnostics.possible_causes.map((cause, i) => <li key={i}>{cause.text} <span className="subtle">({cause.confidence === "high" ? "likely" : cause.confidence === "medium" ? "possible" : "just a guess"})</span></li>)}</ul>
              </>
            )}
          </section>
        )}
        {estimates && preferences.show_estimates !== false && (
          <section className="stack-s" data-testid="estimates">
            <div className="row" style={{ gap: 2 }}>
              <h3>Tutor's estimates</h3>
              <HelpDialog title="What do these estimates mean?">
                <p>The tutor uses these to decide how much help to offer. They are rough guesses from your coding activity, and not tests, grades, or medical or psychological findings.</p>
                <p><strong>Topic understanding</strong> is shown as a range, which narrows as there is more evidence. One success or one mistake moves it only a little.</p>
                <p><strong>Confusion</strong> and <strong>workload</strong> need at least two signs, such as a repeated issue and a hint that did not help. Until then they stay unknown. You can hide these in Settings.</p>
              </HelpDialog>
            </div>
            <ul>
              <li>Topic understanding: {estimates.mastery_band === "not_enough_evidence" ? "not enough evidence yet" : `about ${roundedRange(estimates.mastery_low, estimates.mastery_high)}`}. <span className="subtle">{estimates.mastery_note}</span></li>
              <li>Progress on this problem: {PROGRESS_WORDS[estimates.progress ?? "unknown"]}. {estimates.progress_notes.length > 0 && <span className="subtle">{estimates.progress_notes.join(" ")}</span>}</li>
              <li>Signs of confusion: {estimates.confusion ? ESTIMATE_WORDS[estimates.confusion] : "Unknown"}. {estimates.confusion_notes.length > 0 && <span className="subtle">{estimates.confusion_notes.join(" ")}</span>}</li>
              <li>Workload: {estimates.load ? ESTIMATE_WORDS[estimates.load] : "Unknown"}. {estimates.load_notes.length > 0 && <span className="subtle">{estimates.load_notes.join(" ")}</span>}</li>
            </ul>
          </section>
        )}
        {run && run.stages.length > 0 && (
          <section className="stack-s">
            <h3>What the tutor did</h3>
            <StageList stages={run.stages} />
            <p className="subtle">Reference: <span className="mono">{run.correlation_id.slice(0, 12)}</span></p>
          </section>
        )}
        {evaluation?.runner_backend && <p className="subtle">Checked in: {evaluation.runner_secure ? "isolated container" : `${evaluation.runner_backend} (not isolated)`}{evaluation.duration_ms ? `, ${(evaluation.duration_ms / 1000).toFixed(1)}s` : ""}.</p>}
      </Collapsible.Content>
    </Collapsible.Root>
  );
}

export function ResultsPane(props: {
  problem: ProblemDetail; code: string; focus: "evaluation" | "run" | null; evaluation: Evaluation | null; run: Run | null; response: TutorResponse | null; evaluationBusy: boolean; runBusy: boolean; starting: string | null;
  onRetrySubmit: (code: string) => void; onSubmit: () => void; onCancel: () => void; busy: boolean;
  cases: CaseState[]; onCasesChange: (cases: CaseState[]) => void;
}) {
  const { problem, code, focus, evaluation, run, response, evaluationBusy, runBusy, starting } = props;
  const showingRun = focus === "run";
  const shownEvaluation = showingRun ? run?.evaluation ?? null : evaluation;
  const results = (shownEvaluation?.results ?? []) as TestResult[];
  const snapshotCode = showingRun ? run?.code : evaluation?.code;
  const stale = !!shownEvaluation && snapshotCode !== undefined && snapshotCode !== code;
  const busy = (showingRun ? runBusy : evaluationBusy) || !!starting;

  const running = useMemo(() => {
    if (starting) return "Sending your code";
    if (showingRun && run) {
      const active = [...run.stages].reverse().find((s) => s.status === "running");
      if (active) return STAGE_LABEL[active.stage] ?? "Working";
      return run.status === "queued" ? "Waiting in line" : "Working";
    }
    if (evaluation?.status === "queued") return "Waiting in line";
    return "Running your code in the sandbox";
  }, [starting, showingRun, run, evaluation?.status]);

  const verdict = showingRun ? response?.verdict : evaluation?.verdict;
  const headline = showingRun && response ? response.what_happened : null;
  const { tone, Icon } = toneFor(verdict);
  const passedLine = shownEvaluation && shownEvaluation.total > 0 ? `${shownEvaluation.passed} of ${shownEvaluation.total} tests passed.` : null;
  const runFailed = showingRun && run?.status === "failed" && !response;
  const empty = !busy && !shownEvaluation && !response && !runFailed;
  // Before anything has run, the test cases are what matters. Once something runs, its result is.
  const [view, setView] = useState<"cases" | "result">(empty ? "cases" : "result");
  useEffect(() => { if (busy) setView("result"); }, [busy]);

  return (
    <div className="pane" aria-label="Results">
      <div className="pane-head" style={{ paddingTop: 0, paddingBottom: 0 }}>
        <div className="result-views" role="tablist" aria-label="Test cases or result">
          <button type="button" role="tab" aria-selected={view === "cases"} className="result-view" onClick={() => setView("cases")} data-testid="view-cases">Test cases</button>
          <button type="button" role="tab" aria-selected={view === "result"} className="result-view" onClick={() => setView("result")} data-testid="view-result">Test result</button>
        </div>
        {busy && !starting && <Button size="small" variant="ghost" onClick={props.onCancel}>Cancel</Button>}
      </div>
      <div className="pane-body stack" data-testid="results-pane">
        {view === "cases" ? <TestCases problem={problem} cases={props.cases} onChange={props.onCasesChange} disabled={props.busy} /> : <div className="stack" aria-live="polite">
        {busy && (
          <div className="stack-s" data-testid="running">
            <div className="row"><Spinner /><span>{running}…</span></div>
            {showingRun && run && run.stages.length > 1 && (
              <Collapsible.Root>
                <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> What the tutor is doing</Collapsible.Trigger>
                <Collapsible.Content style={{ paddingTop: 4 }}><StageList stages={run.stages} /></Collapsible.Content>
              </Collapsible.Root>
            )}
          </div>
        )}
        {empty && <p className="muted">Press <strong>Run</strong> to try the test cases, or <strong>Submit</strong> to check all the tests. Results will appear here.</p>}
        {!busy && stale && (
          <div className="stale" role="status" data-testid="stale-result"><RotateCw size={14} aria-hidden /> These results are for an earlier version of your code. Run it again to check your latest changes.</div>
        )}
        {runFailed && <Notice tone="warn" title="The tutor could not finish">Your code is safe in the editor. Please try again.</Notice>}
        {!busy && verdict && (
          <div className="verdict" data-tone={tone} data-testid="verdict" data-verdict={verdict}>
            <Icon size={20} aria-hidden />
            <div className="grow stack-s" style={{ gap: 2 }}>
              <h3>{headline?.title ?? VERDICT_LABEL[verdict] ?? "Result"}</h3>
              <p>{headline?.detail ?? evaluation?.message ?? passedLine ?? (verdict === "ran" ? "Your program ran." : "")}</p>
              {!headline && verdict === "public_passed" && <p className="subtle">Run only tries the examples. Submit to check every test.</p>}
              {!headline && verdict === "service_failure" && <p className="subtle">This is a problem on our side, not with your code. Nothing was counted.</p>}
            </div>
          </div>
        )}
        {!busy && showingRun && response?.progress_note && <p className="progress-note show-mobile" role="status">{response.progress_note}</p>}
        {!busy && showingRun && response?.diagnostics?.diagnosis?.likely_cause && (response.tutor?.level ?? 0) >= 2 && response.verdict !== "accepted" && (
          <p className="diagnosis-note" data-testid="diagnosis">
            <strong>{response.diagnostics.diagnosis.confidence >= 0.8 ? "Likely cause" : "Possible cause"}:</strong> {response.diagnostics.diagnosis.likely_cause}
            {response.diagnostics.diagnosis.concept && <span className="subtle"> · {response.diagnostics.diagnosis.concept}</span>}
          </p>
        )}
        {!busy && showingRun && response && response.next_action.label && (
          <section className="stack-s" data-testid="next-action">
            {response.next_action.kind === "next_problem" && response.next_action.problem_id ? (
              <Link to={`/problems/${response.next_action.problem_id}`} className="btn btn-primary">{response.next_action.label}</Link>
            ) : response.next_action.kind === "retry" ? (
              <div><Button variant="primary" onClick={() => props.onRetrySubmit(run?.code ?? code)}><RotateCw size={15} aria-hidden /> Try again</Button></div>
            ) : response.next_action.kind === "submit" ? (
              <div><Button variant="primary" onClick={props.onSubmit}>Submit your code</Button></div>
            ) : response.next_action.kind === "edit_tests" ? (
              <Link to={`/problems/${problem.id}/edit`} className="btn btn-primary">Add or enable a test</Link>
            ) : (
              <p><strong>Next:</strong> {response.next_action.label}</p>
            )}
            {response.next_action.detail && <p className="subtle">{response.next_action.detail}</p>}
          </section>
        )}
        {!busy && <Tests results={results} />}
        {!busy && (response || shownEvaluation) && <Details response={showingRun ? response : null} run={showingRun ? run : null} evaluation={shownEvaluation} />}
        </div>}
      </div>
    </div>
  );
}
