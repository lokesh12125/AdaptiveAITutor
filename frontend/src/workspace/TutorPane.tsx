import * as Collapsible from "@radix-ui/react-collapsible";
import { useMutation } from "@tanstack/react-query";
import { ChevronRight, Lightbulb, MessageCircleQuestion, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { HintRow, TutorResponse, Workspace } from "@/api/types";
import { Markdown } from "@/components/Markdown";
import { Button, Field, HelpDialog, Spinner, useToast } from "@/components/ui";
import { timeAgo } from "@/lib/format";

const LEVELS = ["Independent attempt", "Conceptual question", "Targeted hint", "Step-by-step outline", "Analogous worked example"];

/** A small picture of the help ladder, so the amount of help is visible at a glance. */
function Rungs({ level }: { level: number }) {
  return (
    <span className="rungs" role="img" aria-label={`Help level ${level} of 4`}>
      {[1, 2, 3, 4].map((rung) => <i key={rung} data-on={rung <= level} style={{ height: 4 + rung * 3 }} />)}
    </span>
  );
}

function ReflectionCard({ reflection, onDone }: { reflection: { id: string; prompt: string }; onDone: () => void }) {
  const [answer, setAnswer] = useState("");
  const toast = useToast();
  const save = useMutation({
    mutationFn: () => api(`/reflections/${reflection.id}/answer`, { method: "POST", body: { answer } }),
    onSuccess: () => { toast({ tone: "ok", title: "Your answer is saved" }); onDone(); },
    onError: () => toast({ tone: "error", title: "Your answer could not be saved", detail: "Please try again." }),
  });
  const skip = useMutation({ mutationFn: () => api(`/reflections/${reflection.id}/dismiss`, { method: "POST" }), onSuccess: onDone });
  return (
    <section className="card card-tight stack-s" data-testid="reflection">
      <h3 className="row" style={{ gap: 6 }}><MessageCircleQuestion size={16} aria-hidden /> A question to think about</h3>
      <form className="stack-s" onSubmit={(event) => { event.preventDefault(); if (answer.trim()) save.mutate(); }}>
        <Field label={reflection.prompt} help="Optional. There is no grade, and only you and your teacher can see it.">
          {(props) => <textarea {...props} className="textarea" rows={3} value={answer} onChange={(e) => setAnswer(e.target.value)} />}
        </Field>
        <div className="row">
          <Button type="submit" size="small" disabled={!answer.trim() || save.isPending}>Save answer</Button>
          <Button size="small" variant="ghost" onClick={() => skip.mutate()}>Not now</Button>
        </div>
      </form>
    </section>
  );
}

export function TutorPane(props: {
  response: TutorResponse | null; workspace: Workspace; busy: boolean; runBusy: boolean; canAskMore: boolean;
  onHint: (options: { request_size?: "nudge" | "more"; question?: string; self_state?: "stuck" | "overwhelmed" }) => void;
  selfConfidence: "low" | "medium" | "high" | null; onSelfConfidence: (value: "low" | "medium" | "high" | null) => void;
}) {
  const { response, workspace, busy, runBusy, onHint } = props;
  const [question, setQuestion] = useState("");
  const [askOpen, setAskOpen] = useState(false);
  const [feedback, setFeedback] = useState<Record<string, boolean>>({});
  const [reflectionDone, setReflectionDone] = useState<string | null>(null);
  const toast = useToast();

  const hint = response?.tutor ?? null;
  const reflection = (response?.reflection ?? workspace.pending_reflection) as { id: string; prompt: string } | null;
  useEffect(() => setQuestion(""), [hint?.hint_id]);
  const earlier = workspace.hints.filter((h: HintRow) => h.id !== hint?.hint_id);
  const plan = response?.plan;

  const sendFeedback = async (id: string, helpful: boolean) => {
    setFeedback((current) => ({ ...current, [id]: helpful }));
    await api(`/hints/${id}/feedback`, { method: "POST", body: { helpful } }).catch(() => toast({ tone: "error", title: "That feedback could not be saved" }));
  };

  return (
    <div className="pane" aria-label="Tutor">
      <div className="pane-head">
        <span className="pane-title"><Lightbulb size={15} aria-hidden /> Tutor</span>
        <HelpDialog title="How the tutor helps">
          <p>Help comes in steps, and the tutor starts small:</p>
          <ol>{LEVELS.slice(1).map((name) => <li key={name}>{name}</li>)}</ol>
          <p>It moves up a step if you stay stuck on the same issue, and eases off when you are making progress. It will not write the solution to this problem for you, because working it out is how you learn it.</p>
        </HelpDialog>
      </div>
      <div className="pane-body stack" data-testid="tutor-pane">
        {runBusy && <div className="row muted"><Spinner /> Thinking about what would help…</div>}

        {!runBusy && hint && (
          <section className="tutor-hint" data-testid="hint" data-level={hint.level} aria-live="polite">
            <div className="row-between">
              <strong className="row" style={{ gap: 7 }}><Rungs level={hint.level} /> {hint.level_name}</strong>
              {hint.source === "built_in" ? <span className="badge">Standard hint</span> : <span className="badge">AI-worded</span>}
            </div>
            <Markdown>{hint.text}</Markdown>
            {hint.source_note && <p className="subtle">{hint.source_note}</p>}
            <Collapsible.Root>
              <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Why this hint?</Collapsible.Trigger>
              <Collapsible.Content><p className="subtle" data-testid="hint-why" style={{ color: "var(--text-2)" }}>{hint.why}</p></Collapsible.Content>
            </Collapsible.Root>
            <div className="row-between">
              <span className="row" style={{ gap: 2 }}>
                <span className="subtle">Helpful?</span>
                <Button size="small" variant="ghost" icon aria-label="This hint was helpful" aria-pressed={feedback[hint.hint_id] === true} onClick={() => void sendFeedback(hint.hint_id, true)}><ThumbsUp size={14} aria-hidden fill={feedback[hint.hint_id] === true ? "currentColor" : "none"} /></Button>
                <Button size="small" variant="ghost" icon aria-label="This hint was not helpful" aria-pressed={feedback[hint.hint_id] === false} onClick={() => void sendFeedback(hint.hint_id, false)}><ThumbsDown size={14} aria-hidden fill={feedback[hint.hint_id] === false ? "currentColor" : "none"} /></Button>
              </span>
              <Button size="small" disabled={busy} onClick={() => onHint({ request_size: "more" })}>I need more help</Button>
            </div>
          </section>
        )}

        {!runBusy && !hint && response?.offer && (
          <section className="stack-s" data-testid="offer">
            <p>You may want to try again by yourself first. A hint is here if you'd like one.</p>
            <p className="subtle">{response.offer.why}</p>
            <div><Button variant="hint" disabled={busy} onClick={() => onHint({})}>Get a hint</Button></div>
          </section>
        )}

        {!runBusy && !hint && !response?.offer && (!response || response.verdict !== "accepted") && (
          <p className="muted" data-testid="tutor-waiting">The tutor is here when you need it. It looks at your work when you submit or ask for a hint, and never while you are typing.</p>
        )}
        {!runBusy && !hint && response?.verdict === "accepted" && <p className="muted">No hint needed here. Nice work.</p>}

        {!hint && !response?.offer && response?.verdict !== "accepted" && (
          <div className="row">
            <Button variant="hint" disabled={busy} onClick={() => onHint({ request_size: "nudge" })} data-testid="nudge"><Lightbulb size={15} aria-hidden /> Just a small nudge</Button>
          </div>
        )}

        {response?.verdict !== "accepted" && (
          <Collapsible.Root open={askOpen} onOpenChange={setAskOpen}>
            <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Tell the tutor what's going on</Collapsible.Trigger>
            <Collapsible.Content className="stack-s" style={{ paddingTop: 6 }}>
              <form className="stack-s" onSubmit={(event) => { event.preventDefault(); onHint({ question: question.trim() || undefined }); setAskOpen(false); }}>
                <Field label="What are you stuck on?" help="The tutor will guide you towards the answer rather than give it.">
                  {(p) => <textarea {...p} className="textarea" rows={2} maxLength={500} value={question} onChange={(e) => setQuestion(e.target.value)} />}
                </Field>
                <div className="row">
                  <Button type="submit" size="small" variant="hint" disabled={busy}>Ask for help</Button>
                  <Button size="small" disabled={busy} onClick={() => { onHint({ self_state: "overwhelmed", question: question.trim() || undefined }); setAskOpen(false); }}>This feels like a lot</Button>
                </div>
              </form>
              <fieldset className="row" style={{ border: "none", padding: 0, margin: 0, gap: 6 }}>
                <legend className="field-help" style={{ padding: 0, marginBottom: 4 }}>How sure are you about your approach? Optional. It helps tailor hints on your next action.</legend>
                {(["low", "medium", "high"] as const).map((value) => (
                  <Button key={value} size="small" aria-pressed={props.selfConfidence === value} variant={props.selfConfidence === value ? "primary" : undefined} onClick={() => props.onSelfConfidence(props.selfConfidence === value ? null : value)}>
                    {value === "low" ? "Not sure" : value === "medium" ? "Fairly sure" : "Very sure"}
                  </Button>
                ))}
              </fieldset>
            </Collapsible.Content>
          </Collapsible.Root>
        )}

        {!runBusy && reflection && reflectionDone !== reflection.id && <ReflectionCard key={reflection.id} reflection={reflection} onDone={() => setReflectionDone(reflection.id)} />}

        {!runBusy && plan && (plan.action !== "continue_current" || response?.verdict === "accepted") && (
          <section className="card card-tight stack-s" data-testid="plan">
            <h3>Suggested next step</h3>
            <p><strong>{plan.title}</strong></p>
            <p className="subtle" style={{ color: "var(--text-2)" }}>{plan.reason}</p>
            <div className="row">
              {plan.problem_id && <Link className="btn btn-small btn-primary" to={`/problems/${plan.problem_id}`}>Go to {plan.problem_title ?? "problem"}</Link>}
              <Link className="btn btn-small btn-ghost" to={plan.unit_id ? `/path/${plan.unit_id}` : "/path"}>{plan.unit_id ? "Review this topic" : "See the path"}</Link>
              <Link className="btn btn-small btn-ghost" to="/problems">Choose something else</Link>
            </div>
          </section>
        )}

        {earlier.length > 0 && (
          <Collapsible.Root>
            <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Earlier hints ({earlier.length})</Collapsible.Trigger>
            <Collapsible.Content className="stack-s" style={{ paddingTop: 6 }}>
              {earlier.map((row: HintRow) => (
                <div key={row.id} className="stack-s" style={{ gap: 2, borderLeft: "2px solid var(--border)", paddingLeft: 10 }}>
                  <span className="subtle row" style={{ gap: 6 }}><Rungs level={row.level} /> {row.level_name} · {timeAgo(row.created_at)}</span>
                  <Markdown>{row.text}</Markdown>
                </div>
              ))}
            </Collapsible.Content>
          </Collapsible.Root>
        )}
      </div>
    </div>
  );
}
