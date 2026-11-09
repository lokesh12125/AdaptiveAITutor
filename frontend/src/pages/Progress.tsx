import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { HintRow } from "@/api/types";
import { ActivityChart, MasteryRange, type ActivityDay } from "@/components/Charts";
import { Button, EmptyState, errorText, ErrorState, HelpDialog, Modal, Notice, PageLoading, Stat, useToast } from "@/components/ui";
import { duration, ESTIMATE_WORDS, percent, PROGRESS_WORDS, roundedRange, timeAgo } from "@/lib/format";
import { useSession } from "@/lib/session";

export type Metrics = { started: number; solved: number; completion_rate: number | null; hints_total: number; hints_per_solved: number | null; median_seconds_to_complete: number | null; time_sample: number; graded_attempts: number; hint_progress_rate: number | null; hints_with_outcome: number };
export type Gain = { available: boolean; mean_normalised_gain: number | null; pairs: number; with_pre_only: number; note: string };
type ProgressData = {
  metrics: Metrics; activity: ActivityDay[]; hints: HintRow[]; learning_gain: Gain; satisfaction: { responses: number; median: number | null };
  topics: { unit_id: string; title: string; optional: boolean; band: string; band_label: string; low: number | null; high: number | null; graded_attempts: number; solved: number; total: number; independent: number; assisted: number }[];
  estimates: null | { at: string; problem_title: string | null; confidence: number | null; confusion: string | null; cognitive_load: string | null; progress: string | null; evidence: { confusion?: string[]; load?: string[]; progress?: string[]; mastery?: string }; method_version: string };
  reflections: { prompt: string; answer: string; at: string; problem_title: string | null }[];
};
const OUTCOME: Record<string, string> = { solved: "Followed by a solve", progress: "Followed by progress", no_progress: "No progress yet" };

function Survey({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const toast = useToast();
  const client = useQueryClient();
  const items = [["usefulness", "The tutor was useful for my learning."], ["clarity", "The hints and explanations were clear."], ["hint_adequacy", "The amount of help felt about right."], ["adaptivity", "The help seemed to fit my current level."]] as const;
  const send = useMutation({
    mutationFn: () => api("/survey", { method: "POST", body: answers }),
    onSuccess: () => { toast({ tone: "ok", title: "Thank you. Your feedback is recorded." }); onOpenChange(false); void client.invalidateQueries({ queryKey: ["progress"] }); },
  });
  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Share your feedback">
      <p className="muted">From 1 (strongly disagree) to 5 (strongly agree).</p>
      {send.isError && <Notice tone="danger">{errorText(send.error)}</Notice>}
      {items.map(([key, text]) => (
        <fieldset key={key} style={{ border: "none", padding: 0, margin: 0 }} className="stack-s">
          <legend style={{ padding: 0, marginBottom: 4 }}>{text}</legend>
          <div className="row" style={{ gap: 4 }}>
            {[1, 2, 3, 4, 5].map((value) => <Button key={value} size="small" aria-pressed={answers[key] === value} variant={answers[key] === value ? "primary" : undefined} aria-label={`${value} of 5`} onClick={() => setAnswers({ ...answers, [key]: value })}>{value}</Button>)}
          </div>
        </fieldset>
      ))}
      <div className="dialog-actions">
        <Button onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant="primary" disabled={Object.keys(answers).length < 4 || send.isPending} onClick={() => send.mutate()} data-testid="send-survey">Send feedback</Button>
      </div>
    </Modal>
  );
}

export function ProgressPage() {
  const { preferences } = useSession();
  const [surveyOpen, setSurveyOpen] = useState(false);
  const query = useQuery<ProgressData>({ queryKey: ["progress"], queryFn: () => api<ProgressData>("/progress") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="Your progress" onRetry={() => void query.refetch()} />;
  const { metrics, topics, activity, hints, estimates, learning_gain: gain, reflections } = query.data;
  const started = topics.filter((t) => t.graded_attempts > 0 || t.solved > 0);
  const notStarted = topics.filter((t) => !(t.graded_attempts > 0 || t.solved > 0) && !t.optional).length;
  return (
    <div className="stack-l">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div><h1>Your progress</h1><p>What you have done, and the tutor's rough estimates of where you are. All of this comes from your own activity.</p></div>
        <Button onClick={() => setSurveyOpen(true)} data-testid="open-survey">Share feedback</Button>
      </div>
      <div className="grid-stats" data-testid="stats">
        <Stat label="Problems solved" value={metrics.solved} note={`of ${metrics.started} attempted`} />
        <Stat label="Completion rate" value={percent(metrics.completion_rate)} note="Solved ÷ attempted" />
        <Stat label="Hints per solved problem" value={metrics.hints_per_solved ?? "No data yet"} note="Hints on problems you solved" />
        <Stat label="Typical time to solve" value={duration(metrics.median_seconds_to_complete)} note={metrics.time_sample ? `Median active time, ${metrics.time_sample} problem${metrics.time_sample === 1 ? "" : "s"}` : "Active time only"} />
      </div>
      <section className="card" aria-labelledby="topics-heading">
        <div className="row" style={{ gap: 2, marginBottom: 6 }}>
          <h2 id="topics-heading">Topic estimates</h2>
          <HelpDialog title="What does this estimate mean?">
            <p>Each bar shows a range where your understanding probably sits, based on how your graded attempts went. More attempts make the range narrower.</p>
            <p>Solving a problem without hints counts for more than solving it with heavy help. Syntax slips count very little, and asking for hints never lowers it.</p>
            <p>It is a rough estimate that helps the tutor choose what to suggest. It is not a grade or a test score.</p>
          </HelpDialog>
        </div>
        {started.length === 0 ? <EmptyState title="Nothing to estimate yet" action={<Link className="btn" to="/">Find a problem to start with</Link>}>Estimates appear after your first graded attempt.</EmptyState> : (
          <>
            {started.map((topic) => (
              <div className="topic-row" key={topic.unit_id} data-testid="topic-row">
                <span><Link to={`/path/${topic.unit_id}`} style={{ color: "inherit" }}>{topic.title}</Link><br /><span className="subtle">{topic.solved} of {topic.total} solved{topic.assisted ? `, ${topic.assisted} with hints` : ""}</span></span>
                <MasteryRange low={topic.low} high={topic.high} label={topic.title} />
                <span className="subtle">{topic.band_label}{topic.band !== "not_enough_evidence" ? ` (${roundedRange(topic.low, topic.high)})` : ""}</span>
              </div>
            ))}
            {notStarted > 0 && <p className="subtle" style={{ marginTop: 8 }}>{notStarted} other topic{notStarted === 1 ? "" : "s"} not started yet. <Link to="/path">See the path</Link>.</p>}
          </>
        )}
      </section>
      <div className="grid-2">
        <section className="card" aria-labelledby="activity-heading"><h2 className="card-title" id="activity-heading">Learning activity</h2><ActivityChart days={activity} /></section>
        {preferences.show_estimates !== false && (
          <section className="card stack-s" aria-labelledby="state-heading">
            <div className="row" style={{ gap: 2 }}>
              <h2 id="state-heading">Latest working estimates</h2>
              <HelpDialog title="Are these measurements of how I feel?">
                <p>No. They are guesses from coding behaviour, such as a repeated error or a hint that did not help. The tutor uses them to adjust how much help to give.</p>
                <p>They are not medical or psychological findings. Anything without enough evidence stays unknown rather than being guessed. Confidence comes only from what you tell the tutor yourself.</p>
                <p>You can hide these in Settings.</p>
              </HelpDialog>
            </div>
            {!estimates ? <p className="muted">These appear after you submit or ask for a hint.</p> : (
              <>
                <p className="subtle">From your work on {estimates.problem_title ?? "a problem"}, {timeAgo(estimates.at)}.</p>
                <dl className="test-detail" style={{ padding: 0, fontSize: "0.95em" }}>
                  <dt>Progress</dt><dd style={{ fontFamily: "inherit" }}>{PROGRESS_WORDS[estimates.progress ?? "unknown"]}</dd>
                  <dt>Signs of confusion</dt><dd style={{ fontFamily: "inherit" }}>{estimates.confusion ? ESTIMATE_WORDS[estimates.confusion] : "Unknown"}</dd>
                  <dt>Workload</dt><dd style={{ fontFamily: "inherit" }}>{estimates.cognitive_load ? ESTIMATE_WORDS[estimates.cognitive_load] : "Unknown"}</dd>
                  <dt>Your confidence</dt><dd style={{ fontFamily: "inherit" }}>{estimates.confidence === null ? "Unknown. Only you can tell us this." : estimates.confidence < 0.4 ? "Not sure" : estimates.confidence < 0.7 ? "Fairly sure" : "Very sure"}</dd>
                </dl>
                {[...(estimates.evidence.confusion ?? []), ...(estimates.evidence.load ?? [])].length > 0 && <ul className="subtle">{[...new Set([...(estimates.evidence.confusion ?? []), ...(estimates.evidence.load ?? [])])].map((line) => <li key={line}>{line}</li>)}</ul>}
              </>
            )}
          </section>
        )}
      </div>
      <section className="card stack-s" aria-labelledby="gain-heading">
        <div className="row" style={{ gap: 2 }}>
          <h2 id="gain-heading">Measured improvement</h2>
          <HelpDialog title="How is this measured?"><p>{gain.note}</p><p>The two checks were written to be similar, but they have not been statistically validated. A change between them is a useful indication and not proof.</p></HelpDialog>
        </div>
        {gain.available ? (
          <p>Normalised gain between your two knowledge checks: <strong data-testid="gain">{gain.mean_normalised_gain}</strong></p>
        ) : gain.with_pre_only ? (
          <div className="stack-s"><p className="muted">You have done the starting check. Take the follow-up check when you have practised, to see your improvement.</p><div><Link to="/check/post" className="btn">Take the follow-up check</Link></div></div>
        ) : (
          <div className="stack-s"><p className="muted">Not available yet. Improvement is only measured with two short knowledge checks, never from the tutor's own estimates.</p><div><Link to="/check/pre" className="btn">Take the starting check</Link></div></div>
        )}
      </section>
      <section className="card" aria-labelledby="hints-heading">
        <h2 className="card-title" id="hints-heading">Hints and help</h2>
        {hints.length === 0 ? <p className="muted">You have not used any hints yet.</p> : (
          <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
            <table className="table">
              <thead><tr><th>Problem</th><th>Help</th><th>Why</th><th>What happened next</th><th>When</th></tr></thead>
              <tbody>{hints.map((hint) => (
                <tr key={hint.id}>
                  <td><Link to={`/problems/${hint.problem_id}`}>{hint.problem_title}</Link></td>
                  <td>{hint.level_name}{hint.requested ? "" : <span className="subtle"> (offered by tutor)</span>}</td>
                  <td className="subtle" style={{ minWidth: 200 }}>{hint.why}</td>
                  <td>{hint.outcome ? OUTCOME[hint.outcome] : <span className="subtle">Not known yet</span>}</td>
                  <td className="nowrap">{timeAgo(hint.created_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
      {reflections.length > 0 && (
        <section className="card stack-s" aria-labelledby="reflections-heading">
          <h2 id="reflections-heading">Your reflections</h2>
          {reflections.map((item, index) => <div key={index}><p className="subtle">{item.problem_title}: {item.prompt}</p><p>{item.answer}</p></div>)}
        </section>
      )}
      <Survey open={surveyOpen} onOpenChange={setSurveyOpen} />
    </div>
  );
}
