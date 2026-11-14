import * as Collapsible from "@radix-ui/react-collapsible";
import { useMutation } from "@tanstack/react-query";
import { BookOpen, ChevronRight, Hourglass, Lightbulb, MessageCircleQuestion, RotateCw, Send, ThumbsDown, ThumbsUp, TrendingUp, X } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { HintRow, ReflectionAnswer, Stage, TutorResponse, Workspace } from "@/api/types";
import { InlineCode, Markdown } from "@/components/Markdown";
import { RouteLine } from "@/components/RouteLine";
import { Button, Field, HelpDialog, Spinner, useToast } from "@/components/ui";
import { timeAgo } from "@/lib/format";
import { NewTabLink } from "@/lib/theme";

import { StageList } from "./ResultsPane";
import type { HintOptions } from "./useActions";

const LEVELS = ["Independent attempt", "Conceptual question", "Targeted hint", "Step-by-step outline", "Analogous worked example"];

const QUICK_ASKS = [
  { label: "Why does it fail?", question: "Why does my code fail?" },
  { label: "Where is it wrong?", question: "Where is my code wrong?" },
  { label: "How do I start?", question: "How do I start this problem?" },
  { label: "What does this error mean?", question: "What does this error mean?" },
];

type Lines = { start: number; end: number };

function linesLabel({ start, end }: Lines): string {
  return start === end ? `Line ${start}` : `Lines ${start}–${end}`;
}

/** A small picture of the help ladder, so the amount of help is visible at a glance. */
function Rungs({ level }: { level: number }) {
  return (
    <span className="rungs" role="img" aria-label={`Help level ${level} of 4`}>
      {[1, 2, 3, 4].map((rung) => <i key={rung} data-on={rung <= level} style={{ height: 4 + rung * 3 }} />)}
    </span>
  );
}

function Asked({ text, lines }: { text: string; lines: Lines | null }) {
  return (
    <div className="learner-bubble" data-testid="asked">
      {lines && <span className="line-chip" style={{ marginRight: 6 }}>{linesLabel(lines)}</span>}
      {text}
    </div>
  );
}

/** One reasoning question. When the learner answers, the tutor replies to what they wrote, never with a grade. */
function ReflectionCard({ reflection, onDone }: { reflection: { id: string; prompt: string }; onDone: () => void }) {
  const [answer, setAnswer] = useState("");
  const [reply, setReply] = useState<ReflectionAnswer | null>(null);
  const toast = useToast();
  const save = useMutation({
    mutationFn: () => api<ReflectionAnswer>(`/reflections/${reflection.id}/answer`, { method: "POST", body: { answer } }),
    onSuccess: (result) => setReply(result),
    onError: () => toast({ tone: "error", title: "Your answer could not be saved", detail: "Please try again." }),
  });
  const skip = useMutation({ mutationFn: () => api(`/reflections/${reflection.id}/dismiss`, { method: "POST" }), onSuccess: onDone });
  if (reply) {
    return (
      <section className="card card-tight stack-s" data-testid="reflection" aria-live="polite">
        <h3 className="row" style={{ gap: 6 }}><MessageCircleQuestion size={16} aria-hidden /> A question to think about</h3>
        <p className="subtle"><InlineCode text={reflection.prompt} /></p>
        <p data-testid="reflection-your-answer"><span className="subtle">You wrote:</span> {answer}</p>
        <div className="reflection-reply" data-testid="reflection-reply" data-quality={reply.quality}><p><InlineCode text={reply.feedback} /></p></div>
        {reply.next && (
          <div className="stack-s" data-testid="reflection-next">
            <p><strong>{reply.next.title}</strong></p>
            <p className="subtle" style={{ color: "var(--text-2)" }}>{reply.next.reason}</p>
            {reply.next.problem_id && <div><Link className="btn btn-small btn-primary" to={`/problems/${reply.next.problem_id}`}>Go to {reply.next.problem_title ?? "that problem"}</Link></div>}
          </div>
        )}
        <div><Button size="small" variant="ghost" onClick={onDone} data-testid="reflection-done">Done</Button></div>
      </section>
    );
  }
  return (
    <section className="card card-tight stack-s" data-testid="reflection">
      <h3 className="row" style={{ gap: 6 }}><MessageCircleQuestion size={16} aria-hidden /> A question to think about</h3>
      <form className="stack-s" onSubmit={(event) => { event.preventDefault(); if (answer.trim()) save.mutate(); }}>
        <Field label={<InlineCode text={reflection.prompt} />} help="Optional. There is no grade, and only you and your teacher can see it.">
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

/** Ask anything. Every question runs through all six agents again, with the selected lines as the focus. */
function Composer({ busy, selection, onClearSelection, onAsk, inputRef }: {
  busy: boolean; selection: Lines | null; onClearSelection: () => void; onAsk: (options: HintOptions, shown: string | null) => void; inputRef: React.RefObject<HTMLTextAreaElement>;
}) {
  const [text, setText] = useState("");
  const focus = selection ? { focus_start: selection.start, focus_end: selection.end } : {};
  const send = (question: string) => {
    const clean = question.trim() || (selection ? "Help me understand these lines." : "");
    if (!clean || busy) return;
    onAsk({ question: clean, ...focus }, clean);
    setText("");
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(text); }
  };
  return (
    <form className="composer" onSubmit={(event) => { event.preventDefault(); send(text); }} aria-label="Ask the tutor" data-testid="composer">
      <div className="composer-focus" data-testid="ask-focus">
        {selection
          ? <><span>Asking about</span><span className="line-chip">{linesLabel(selection)}</span><button type="button" onClick={onClearSelection} aria-label="Stop pointing at these lines"><X size={13} aria-hidden /></button></>
          : <span>Select lines in your code to ask about them.</span>}
      </div>
      <div className="composer-box">
        <textarea
          ref={inputRef} className="textarea" rows={1} maxLength={500} aria-label="Ask the tutor" data-testid="ask-input" value={text}
          placeholder="What is confusing you?" onChange={(event) => setText(event.target.value)} onKeyDown={onKeyDown}
        />
        <Button type="submit" variant="hint" icon aria-label="Send your question" disabled={busy || (!text.trim() && !selection)} data-testid="ask-send"><Send size={16} aria-hidden /></Button>
      </div>
      <div className="quick-asks">
        {QUICK_ASKS.map((ask) => <button key={ask.label} type="button" className="quick-ask" data-testid="quick-ask" disabled={busy} onClick={() => send(ask.question)}>{ask.label}</button>)}
        <button type="button" className="quick-ask" data-testid="quick-ask-lot" disabled={busy} onClick={() => onAsk({ self_state: "overwhelmed", ...focus }, "This feels like a lot.")}>This feels like a lot</button>
      </div>
    </form>
  );
}

export function TutorPane(props: {
  response: TutorResponse | null; workspace: Workspace; busy: boolean; runBusy: boolean; stages: Stage[]; codeChanged: boolean; unitId: string;
  onHint: (options: HintOptions) => void; selection: Lines | null; onClearSelection: () => void;
  selfConfidence: "low" | "medium" | "high" | null; onSelfConfidence: (value: "low" | "medium" | "high" | null) => void;
}) {
  const { response, workspace, busy, runBusy, onHint, codeChanged, stages, selection, onClearSelection } = props;
  const [asked, setAsked] = useState<{ text: string; lines: Lines | null } | null>(null);
  const [feedback, setFeedback] = useState<Record<string, boolean>>({});
  const [reflectionDone, setReflectionDone] = useState<string | null>(null);
  const toast = useToast();
  const thread = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  const hint = response?.tutor ?? null;
  const waiting = response?.waiting ?? null;
  const reflection = (response?.reflection ?? workspace.pending_reflection) as { id: string; prompt: string } | null;
  const earlier = workspace.hints.filter((h: HintRow) => h.id !== hint?.hint_id);
  const plan = response?.plan;

  // The newest answer is what the learner came for, so keep it in view.
  const newest = runBusy ? "busy" : hint?.hint_id ?? waiting?.snapshot_id ?? "";
  useEffect(() => { if (thread.current) thread.current.scrollTop = thread.current.scrollHeight; }, [newest]);

  const sendFeedback = async (id: string, helpful: boolean) => {
    setFeedback((current) => ({ ...current, [id]: helpful }));
    await api(`/hints/${id}/feedback`, { method: "POST", body: { helpful } }).catch(() => toast({ tone: "error", title: "That feedback could not be saved" }));
  };
  const ask = (options: HintOptions, shown: string | null) => {
    setAsked(shown ? { text: shown, lines: options.focus_start != null ? { start: options.focus_start, end: options.focus_end ?? options.focus_start } : null } : null);
    onHint(options);
  };
  const plain = (options: HintOptions) => ask(options, null);

  // What the learner asked, shown above its answer. The saved question is used after a page reload.
  const bubble = runBusy || waiting ? asked : hint?.question ? { text: hint.question, lines: hint.focus && !hint.focus.auto ? { start: hint.focus.start, end: hint.focus.end } : null } : null;

  return (
    <div className="pane" aria-label="Tutor">
      <div className="pane-head">
        <span className="pane-title"><Lightbulb size={15} aria-hidden /> Tutor</span>
        <HelpDialog title="How the tutor helps">
          <p>Help comes in steps, and the tutor starts small:</p>
          <ol>{LEVELS.slice(1).map((name) => <li key={name}>{name}</li>)}</ol>
          <p>Each time you ask about the same issue you get a different kind of help, so the tutor never just repeats itself. It eases off when you are making progress, and starts small again on a new issue.</p>
          <p><strong>You can always ask it something specific.</strong> Type what confuses you, and select the lines you mean in your code. Your question goes through the same six agents, which run your code on an example and look at what those lines really did.</p>
          <p>It will not write the solution to this problem for you, because working it out is how you learn it.</p>
        </HelpDialog>
      </div>
      <div className="tutor-pane">
        <div className="tutor-thread" data-testid="tutor-pane" ref={thread}>
          {earlier.length > 0 && (
            <Collapsible.Root>
              <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Earlier help ({earlier.length})</Collapsible.Trigger>
              <Collapsible.Content className="stack-s" style={{ paddingTop: 6 }}>
                {earlier.map((row: HintRow) => (
                  <div key={row.id} className="stack-s" style={{ gap: 4, borderLeft: "2px solid var(--border)", paddingLeft: 10 }}>
                    {row.question && <Asked text={row.question} lines={row.focus_start ? { start: row.focus_start, end: row.focus_end ?? row.focus_start } : null} />}
                    <span className="subtle row" style={{ gap: 6 }}><Rungs level={row.level} /> {row.level_name} · {timeAgo(row.created_at)}</span>
                    <Markdown>{row.text}</Markdown>
                  </div>
                ))}
              </Collapsible.Content>
            </Collapsible.Root>
          )}

          {!runBusy && response?.progress_note && <p className="progress-note" role="status" data-testid="progress-note"><TrendingUp size={16} aria-hidden /> {response.progress_note}</p>}

          {bubble && <Asked text={bubble.text} lines={bubble.lines} />}

          {runBusy && (
            <section className="stack-s" role="status" data-testid="tutor-working">
              <div className="row muted"><Spinner /> <strong>The tutor is working on this</strong></div>
              {stages.length > 1 && <StageList stages={stages} />}
            </section>
          )}

          {!runBusy && hint && (
            <section className="tutor-hint" data-testid="hint" data-level={hint.level} data-strategy={hint.strategy} aria-live="polite">
              <div className="row-between">
                <strong className="row" style={{ gap: 7 }}><Rungs level={hint.level} /> {hint.strategy_label ?? hint.level_name}</strong>
                {hint.source === "ai" ? <span className="badge">AI-worded</span> : hint.strategy !== "answer_question" ? <span className="badge">Standard hint</span> : null}
              </div>
              {hint.hint_number ? <p className="subtle" data-testid="hint-number">Hint {hint.hint_number} on this issue · {hint.level_name}</p> : null}
              {hint.focus?.auto && <p className="subtle" data-testid="hint-auto-focus">Looking at {linesLabel(hint.focus).toLowerCase()} of your code.</p>}
              <Markdown>{hint.text}</Markdown>
              {hint.source_note && <p className="subtle">{hint.source_note}</p>}
              {codeChanged && <p className="stale" style={{ flexWrap: "nowrap" }} data-testid="hint-stale"><RotateCw size={14} style={{ flex: "none" }} aria-hidden /> <span>You have changed your code since this hint.</span></p>}
              {(hint.concept || hint.topic_id) && (
                <p className="row subtle hint-concept" style={{ gap: 6 }} data-testid="hint-concept">
                  {hint.concept && <span>Concept: <strong>{hint.concept}</strong></span>}
                  {hint.concept && hint.topic_id && <span aria-hidden>·</span>}
                  {hint.topic_id && <NewTabLink to={`/path/${hint.topic_id}?tab=lesson`} className="row" style={{ gap: 5 }} data-testid="hint-lesson"><BookOpen size={14} aria-hidden /> Read the lesson</NewTabLink>}
                </p>
              )}
              <Collapsible.Root>
                <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Why this hint?</Collapsible.Trigger>
                <Collapsible.Content className="stack-s" style={{ paddingTop: 2 }}>
                  <p className="subtle" data-testid="hint-why" style={{ color: "var(--text-2)" }}>{hint.why}</p>
                  {(hint.why_details ?? []).length > 0 && (
                    <dl className="why-details" data-testid="hint-why-details">
                      {hint.why_details.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
                    </dl>
                  )}
                </Collapsible.Content>
              </Collapsible.Root>
              <div className="row-between">
                <span className="row" style={{ gap: 2 }}>
                  <span className="subtle">Helpful?</span>
                  <Button size="small" variant="ghost" icon aria-label="This hint was helpful" aria-pressed={feedback[hint.hint_id] === true} onClick={() => void sendFeedback(hint.hint_id, true)}><ThumbsUp size={14} aria-hidden fill={feedback[hint.hint_id] === true ? "currentColor" : "none"} /></Button>
                  <Button size="small" variant="ghost" icon aria-label="This hint was not helpful" aria-pressed={feedback[hint.hint_id] === false} onClick={() => void sendFeedback(hint.hint_id, false)}><ThumbsDown size={14} aria-hidden fill={feedback[hint.hint_id] === false ? "currentColor" : "none"} /></Button>
                </span>
                <Button size="small" disabled={busy} onClick={() => plain({ request_size: "more" })}>I need more help</Button>
              </div>
            </section>
          )}

          {!runBusy && waiting && (
            <section className="tutor-wait stack-s" data-testid="hint-waiting" aria-live="polite">
              <h3 className="row" style={{ gap: 7, flexWrap: "nowrap" }}><Hourglass size={16} style={{ flex: "none" }} aria-hidden /> {waiting.title}</h3>
              <p>{waiting.detail}</p>
              <p><strong>Try this next:</strong> {waiting.try_next}</p>
              {codeChanged
                ? <div><Button variant="hint" disabled={busy} onClick={() => plain({})} data-testid="ask-after-change"><Lightbulb size={15} aria-hidden /> Ask about your new code</Button></div>
                : <div><Button size="small" onClick={() => input.current?.focus()} data-testid="hint-locked">Ask about a specific line</Button></div>}
            </section>
          )}

          {!runBusy && !hint && response?.offer && (
            <section className="stack-s" data-testid="offer">
              {response.offer.lead !== null && <p>{response.offer.lead ?? "You may want to try again by yourself first. A hint is here if you'd like one."}</p>}
              <p className={response.offer.lead === null ? undefined : "subtle"}>{response.offer.why}</p>
              <div><Button variant="hint" disabled={busy} onClick={() => plain({})}>Get a hint</Button></div>
            </section>
          )}

          {!runBusy && !hint && !waiting && !response?.offer && (!response || response.verdict !== "accepted") && (
            <div className="stack-s" data-testid="tutor-waiting">
              <p className="muted">The tutor is here when you need it. It looks at your work when you submit or ask, and never while you are typing.</p>
              <div><Button variant="hint" disabled={busy} onClick={() => plain({ request_size: "nudge" })} data-testid="nudge"><Lightbulb size={15} aria-hidden /> Just a small nudge</Button></div>
            </div>
          )}
          {!runBusy && !hint && response?.verdict === "accepted" && <p className="muted">No hint needed here. Nice work.</p>}

          {!runBusy && reflection && reflectionDone !== reflection.id && <ReflectionCard key={reflection.id} reflection={reflection} onDone={() => setReflectionDone(reflection.id)} />}

          {!runBusy && plan && (plan.action !== "continue_current" || response?.verdict === "accepted") && (
            <section className="card card-tight stack-s" data-testid="plan">
              <h3>Suggested next step</h3>
              <p><strong>{plan.title}</strong></p>
              <p className="subtle" style={{ color: "var(--text-2)" }}>{plan.reason}</p>
              <RouteLine route={plan.route} />
              <div className="row">
                {plan.problem_id && <Link className="btn btn-small btn-primary" to={`/problems/${plan.problem_id}`}>Go to {plan.problem_title ?? "problem"}</Link>}
                <Link className="btn btn-small btn-ghost" to={plan.unit_id ? `/path/${plan.unit_id}?tab=lesson` : "/path"}>{plan.unit_id ? "Review this topic" : "See the path"}</Link>
                <Link className="btn btn-small btn-ghost" to="/problems">Choose something else</Link>
              </div>
            </section>
          )}

          {response?.verdict !== "accepted" && (
            <Collapsible.Root>
              <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> How sure are you about your approach?</Collapsible.Trigger>
              <Collapsible.Content style={{ paddingTop: 6 }}>
                <fieldset className="row" style={{ border: "none", padding: 0, margin: 0, gap: 6 }}>
                  <legend className="field-help" style={{ padding: 0, marginBottom: 4 }}>Optional. It helps tailor hints on your next action.</legend>
                  {(["low", "medium", "high"] as const).map((value) => (
                    <Button key={value} size="small" aria-pressed={props.selfConfidence === value} variant={props.selfConfidence === value ? "primary" : undefined} onClick={() => props.onSelfConfidence(props.selfConfidence === value ? null : value)}>
                      {value === "low" ? "Not sure" : value === "medium" ? "Fairly sure" : "Very sure"}
                    </Button>
                  ))}
                </fieldset>
              </Collapsible.Content>
            </Collapsible.Root>
          )}
        </div>
        <Composer busy={busy} selection={selection} onClearSelection={onClearSelection} onAsk={ask} inputRef={input} />
      </div>
    </div>
  );
}
