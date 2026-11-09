import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, Plus, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { ClassInfo, HintRow } from "@/api/types";
import { ActivityChart, MasteryRange, ShareBar, type ActivityDay } from "@/components/Charts";
import { Button, EmptyState, errorText, ErrorState, Field, HelpDialog, Modal, Notice, PageLoading, Select, Stat, useToast } from "@/components/ui";
import { duration, percent, roundedRange, timeAgo, VERDICT_LABEL } from "@/lib/format";

import type { Gain, Metrics } from "./Progress";

type Flag = { kind: string; title: string; evidence: string[]; uncertainty: string; strength: string };
type Overview = {
  class: { id: string; name: string; join_code: string; is_synthetic: boolean; members: number };
  metrics: Metrics; activity: ActivityDay[]; learning_gain: Gain; satisfaction: { responses: number; median: number | null; items: Record<string, number> | null };
  topics: { unit_id: string; title: string; attempts: number; problems_started: number; first_try_rate: number | null; completion_rate: number | null; attempts_per_problem: number | null }[];
  common_errors: { total: number; items: { issue_key: string; label: string; count: number; share: number | null; learners: number }[] };
  assistance: { total: number; requested: number; automatic: number; feedback_helpful: number; feedback_total: number; by_level: { level: number; count: number; resolved: number; progress: number; progress_rate: number | null }[] };
  learners: { id: string; name: string; solved: number; started: number; completion_rate: number | null; hints_per_solved: number | null; last_active: string | null; flags: Flag[] }[];
  needs_support: { id: string; name: string; flags: Flag[] }[];
  definitions: Record<string, string>;
};
const LEVELS = ["", "Conceptual question", "Targeted hint", "Step-by-step outline", "Analogous example"];

function FlagCard({ flag }: { flag: Flag }) {
  return (
    <div className="stack-s" style={{ gap: 2 }}>
      <strong className="row" style={{ gap: 6 }}><TriangleAlert size={14} aria-hidden style={{ color: "var(--warn)" }} /> {flag.title}</strong>
      <ul className="subtle" style={{ color: "var(--text-2)" }}>{flag.evidence.map((line) => <li key={line}>{line}</li>)}</ul>
      <p className="subtle">{flag.uncertainty}</p>
    </div>
  );
}

function NewClass({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const client = useQueryClient();
  const create = useMutation({
    mutationFn: () => api<ClassInfo>("/teacher/classes", { method: "POST", body: { name } }),
    onSuccess: (created) => { void client.invalidateQueries({ queryKey: ["classes"] }); setOpen(false); setName(""); onCreated(created.id); },
  });
  return (
    <>
      <Button onClick={() => setOpen(true)} data-testid="new-class"><Plus size={15} aria-hidden /> New class</Button>
      <Modal open={open} onOpenChange={setOpen} title="Create a class">
        <form className="stack" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
          {create.isError && <Notice tone="danger">{errorText(create.error)}</Notice>}
          <Field label="Class name">{(p) => <input {...p} className="input" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={120} data-testid="class-name" />}</Field>
          <p className="subtle">Learners join with a code. You will only see learners who choose to join.</p>
          <div className="dialog-actions"><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" disabled={create.isPending} data-testid="create-class">Create class</Button></div>
        </form>
      </Modal>
    </>
  );
}

export function TeacherPage() {
  const classes = useQuery<ClassInfo[]>({ queryKey: ["classes"], queryFn: () => api<ClassInfo[]>("/teacher/classes") });
  const [selected, setSelected] = useState<string | null>(null);
  const toast = useToast();
  useEffect(() => { if (!selected && classes.data?.length) setSelected(classes.data[0].id); }, [classes.data, selected]);
  const overview = useQuery<Overview>({ queryKey: ["overview", selected], enabled: !!selected, queryFn: () => api<Overview>(`/teacher/classes/${selected}/overview`) });
  if (classes.isLoading) return <PageLoading />;
  if (classes.isError) return <ErrorState error={classes.error} what="Your classes" onRetry={() => void classes.refetch()} />;
  const data = overview.data;
  const copy = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast({ tone: "ok", title: "Join code copied" });
    } catch {
      toast({ tone: "info", title: `The join code is ${code}` });
    }
  };
  return (
    <div className="stack-l">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div><h1>Class</h1><p>Where learners are getting stuck, and who may need a conversation. Flags are prompts for you to look, not conclusions.</p></div>
        <div className="row">
          {(classes.data?.length ?? 0) > 1 && <div style={{ minWidth: 220 }}><Select label="Choose a class" value={selected ?? ""} onChange={setSelected} options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))} /></div>}
          <NewClass onCreated={setSelected} />
        </div>
      </div>
      {(classes.data?.length ?? 0) === 0 && <EmptyState title="No classes yet">Create a class, then share its join code with your learners.</EmptyState>}
      {overview.isLoading && selected && <PageLoading label="Loading the class" />}
      {overview.isError && <ErrorState error={overview.error} what="This class" onRetry={() => void overview.refetch()} />}
      {data && (
        <>
          {data.class.is_synthetic && <Notice tone="warn" title="Synthetic demonstration data" >Every learner and number in this class was generated to demonstrate the dashboard. None of it is real, and it is not evidence that the tutor works.</Notice>}
          <div className="row-between">
            <span className="row"><strong>{data.class.name}</strong><span className="subtle">{data.class.members} learner{data.class.members === 1 ? "" : "s"}</span></span>
            {!data.class.is_synthetic && <Button size="small" onClick={() => void copy(data.class.join_code)} data-testid="copy-code"><Copy size={14} aria-hidden /> Join code: <span className="mono" data-testid="join-code">{data.class.join_code}</span></Button>}
          </div>
          {data.class.members === 0 ? <EmptyState title="No learners yet">Share the join code. Learners enter it in Settings.</EmptyState> : (
            <>
              <div className="grid-stats" data-testid="class-stats">
                <Stat label="Completion rate" value={percent(data.metrics.completion_rate)} note={`${data.metrics.solved} solved of ${data.metrics.started} attempted`} />
                <Stat label="Hints per solved problem" value={data.metrics.hints_per_solved ?? "No data"} note={`${data.metrics.hints_total} hints in total`} />
                <Stat label="Median time to solve" value={duration(data.metrics.median_seconds_to_complete)} note={`${data.metrics.time_sample} solves with a recorded time`} />
                <Stat label="Satisfaction" value={data.satisfaction.median ? `${data.satisfaction.median} / 5` : "No data"} note={`Median of ${data.satisfaction.responses} survey${data.satisfaction.responses === 1 ? "" : "s"}`} />
                <Stat label="Learning gain" value={data.learning_gain.available ? data.learning_gain.mean_normalised_gain : "Not available"} note={data.learning_gain.available ? `${data.learning_gain.pairs} learners with both checks` : "Needs both knowledge checks"} />
              </div>
              <HelpDialog title="How are these calculated?" label="How are these calculated?">
                {Object.values(data.definitions).map((line) => <p key={line}>{line}</p>)}
                <p>{data.learning_gain.note}</p>
              </HelpDialog>
              <section className="card" aria-labelledby="support-heading" data-testid="needs-support">
                <h2 className="card-title" id="support-heading">Learners who may need support</h2>
                {data.needs_support.length === 0 ? <p className="muted">No flags right now. This does not mean everyone is fine, only that the signals tracked here were not triggered.</p> : (
                  <div className="stack">
                    {data.needs_support.map((learner) => (
                      <div key={learner.id} className="stack-s" style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
                        <Link to={`/teacher/${data.class.id}/students/${learner.id}`}><strong>{learner.name}</strong></Link>
                        {learner.flags.map((flag) => <FlagCard key={flag.title} flag={flag} />)}
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <div className="grid-2">
                <section className="card" aria-labelledby="topic-heading">
                  <h2 className="card-title" id="topic-heading">Topic difficulties</h2>
                  {data.topics.length === 0 ? <p className="muted">No graded attempts yet.</p> : (
                    <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
                      <table className="table">
                        <thead><tr><th>Topic</th><th>Passed first try</th><th className="num">Attempts per problem</th></tr></thead>
                        <tbody>{data.topics.map((topic) => (
                          <tr key={topic.unit_id}>
                            <td>{topic.title}<br /><span className="subtle">{topic.problems_started} started</span></td>
                            <td style={{ minWidth: 120 }}><div className="stack-s" style={{ gap: 2 }}><span>{percent(topic.first_try_rate)}</span><ShareBar value={topic.first_try_rate} label={`${topic.title}: passed first try`} /></div></td>
                            <td className="num">{topic.attempts_per_problem ?? "–"}</td>
                          </tr>
                        ))}</tbody>
                      </table>
                    </div>
                  )}
                </section>
                <section className="card" aria-labelledby="errors-heading">
                  <h2 className="card-title" id="errors-heading">Common errors</h2>
                  {data.common_errors.items.length === 0 ? <p className="muted">No errors recorded yet.</p> : (
                    <div className="stack-s">
                      {data.common_errors.items.map((item) => (
                        <div key={item.issue_key} className="stack-s" style={{ gap: 2 }}>
                          <div className="row-between"><span>{item.label}</span><span className="subtle">{item.count} times, {item.learners} learner{item.learners === 1 ? "" : "s"}</span></div>
                          <ShareBar value={item.share} label={`${item.label}: share of errors`} />
                        </div>
                      ))}
                      <p className="subtle">Bars show each issue's share of {data.common_errors.total} recorded errors.</p>
                    </div>
                  )}
                </section>
                <section className="card" aria-labelledby="assist-heading">
                  <div className="row" style={{ gap: 2 }}>
                    <h2 id="assist-heading">Assistance usage</h2>
                    <HelpDialog title="What does 'followed by progress' mean?"><p>{data.definitions.hint_progress}</p></HelpDialog>
                  </div>
                  {data.assistance.total === 0 ? <p className="muted">No hints yet.</p> : (
                    <>
                      <p className="subtle" style={{ margin: "6px 0" }}>{data.assistance.requested} requested, {data.assistance.automatic} shown by the tutor.{data.assistance.feedback_total > 0 ? ` Learners marked ${data.assistance.feedback_helpful} of ${data.assistance.feedback_total} rated hints as helpful.` : ""}</p>
                      <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
                        <table className="table">
                          <thead><tr><th>Level</th><th className="num">Hints</th><th className="num">Followed by progress</th></tr></thead>
                          <tbody>{data.assistance.by_level.map((row) => <tr key={row.level}><td>{LEVELS[row.level] ?? row.level}</td><td className="num">{row.count}</td><td className="num">{row.resolved ? `${percent(row.progress_rate)} of ${row.resolved}` : "Not known yet"}</td></tr>)}</tbody>
                        </table>
                      </div>
                    </>
                  )}
                </section>
                <section className="card" aria-labelledby="class-activity"><h2 className="card-title" id="class-activity">Activity</h2><ActivityChart days={data.activity} /></section>
              </div>
              <section className="card" aria-labelledby="learners-heading">
                <h2 className="card-title" id="learners-heading">Learners</h2>
                <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
                  <table className="table" data-testid="learners-table">
                    <thead><tr><th>Name</th><th className="num">Solved</th><th className="num">Hints per solve</th><th>Last active</th><th>Flags</th></tr></thead>
                    <tbody>{data.learners.map((learner) => (
                      <tr key={learner.id}>
                        <td><Link to={`/teacher/${data.class.id}/students/${learner.id}`}>{learner.name}</Link></td>
                        <td className="num">{learner.solved} of {learner.started}</td>
                        <td className="num">{learner.hints_per_solved ?? "–"}</td>
                        <td className="nowrap">{timeAgo(learner.last_active)}</td>
                        <td>{learner.flags.length ? <span className="badge badge-warn">{learner.flags.length} to review</span> : <span className="subtle">None</span>}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}

type Detail = {
  id: string; name: string; metrics: Metrics; flags: Flag[]; activity: ActivityDay[]; hints: HintRow[]; learning_gain: Gain; is_synthetic: boolean;
  topics: { unit_id: string; title: string; band_label: string; low: number; high: number; attempts: number; independent: number; assisted: number }[];
  recent: { problem_id: string; title: string | null; verdict: string | null; passed: number; total: number; at: string }[];
};

export function TeacherStudentPage() {
  const { classId = "", studentId = "" } = useParams();
  const query = useQuery<Detail>({ queryKey: ["student", classId, studentId], queryFn: () => api<Detail>(`/teacher/classes/${classId}/students/${studentId}`) });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="This learner" />;
  const data = query.data;
  return (
    <div className="stack-l">
      <div className="stack-s"><Link to="/teacher" className="row" style={{ gap: 4 }}><ArrowLeft size={14} aria-hidden /> Back to class</Link><h1>{data.name}</h1></div>
      {data.is_synthetic && <Notice tone="warn" title="Synthetic record">This learner was generated for the demo. Nothing here is real.</Notice>}
      <div className="grid-stats">
        <Stat label="Solved" value={data.metrics.solved} note={`of ${data.metrics.started} attempted`} />
        <Stat label="Completion rate" value={percent(data.metrics.completion_rate)} />
        <Stat label="Hints per solve" value={data.metrics.hints_per_solved ?? "No data"} />
        <Stat label="Median time to solve" value={duration(data.metrics.median_seconds_to_complete)} note={`${data.metrics.time_sample} recorded`} />
      </div>
      {data.flags.length > 0 && <section className="card stack"><h2>Possible reasons to check in</h2>{data.flags.map((flag) => <FlagCard key={flag.title} flag={flag} />)}</section>}
      <section className="card">
        <h2 className="card-title">Topic estimates</h2>
        {data.topics.length === 0 && <p className="muted">No graded attempts yet.</p>}
        {data.topics.map((topic) => (
          <div className="topic-row" key={topic.unit_id}>
            <span>{topic.title}<br /><span className="subtle">{topic.attempts} attempts, {topic.independent} solved alone, {topic.assisted} with hints</span></span>
            <MasteryRange low={topic.low} high={topic.high} label={topic.title} />
            <span className="subtle">{topic.band_label} ({roundedRange(topic.low, topic.high)})</span>
          </div>
        ))}
        <p className="subtle" style={{ marginTop: 8 }}>Estimates from coding activity. They are not test scores.</p>
      </section>
      <div className="grid-2">
        <section className="card"><h2 className="card-title">Activity</h2><ActivityChart days={data.activity} /></section>
        <section className="card">
          <h2 className="card-title">Recent submissions</h2>
          {data.recent.length === 0 ? <p className="muted">None yet.</p> : (
            <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table"><table className="table"><thead><tr><th>Problem</th><th>Result</th><th>When</th></tr></thead><tbody>{data.recent.map((row, index) => <tr key={index}><td>{row.title}</td><td>{VERDICT_LABEL[row.verdict ?? ""] ?? row.verdict} {row.total ? `(${row.passed}/${row.total})` : ""}</td><td className="nowrap">{timeAgo(row.at)}</td></tr>)}</tbody></table></div>
          )}
        </section>
      </div>
      <section className="card">
        <h2 className="card-title">Help received</h2>
        {data.hints.length === 0 ? <p className="muted">No hints yet.</p> : <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table"><table className="table"><thead><tr><th>Problem</th><th>Level</th><th>Requested</th><th>Next</th></tr></thead><tbody>{data.hints.map((hint) => <tr key={hint.id}><td>{hint.problem_title}</td><td>{hint.level_name}</td><td>{hint.requested ? "Yes" : "No"}</td><td>{hint.outcome ?? "Not known yet"}</td></tr>)}</tbody></table></div>}
      </section>
    </div>
  );
}
