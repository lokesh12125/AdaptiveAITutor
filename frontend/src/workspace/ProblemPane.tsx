import * as Collapsible from "@radix-ui/react-collapsible";
import { BookOpen, ChevronRight, ExternalLink, Pencil, X } from "lucide-react";
import { Link } from "react-router-dom";

import type { ProblemDetail, TopicNotes } from "@/api/types";
import { Markdown } from "@/components/Markdown";
import { Button, CopyButton, HelpDialog } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";
import { NewTabLink } from "@/lib/theme";

function ConceptNotes({ problem }: { problem: ProblemDetail }) {
  const notes = (problem.topic_notes ?? null) as unknown as TopicNotes | null;
  if (!notes) return null;
  return (
    <section className="concept-notes" data-testid="concept-notes">
      <div className="row-between">
        <strong className="row" style={{ gap: 6 }}><BookOpen size={15} aria-hidden /> {problem.unit_title}</strong>
        <NewTabLink to={`/path/${problem.unit_id}?tab=lesson`} className="subtle" data-testid="read-lesson">Read the lesson</NewTabLink>
      </div>
      <Collapsible.Root>
        <Collapsible.Trigger className="collapsible-trigger" data-testid="concept-notes-toggle"><ChevronRight size={15} className="chevron" aria-hidden /> Concept notes for this problem</Collapsible.Trigger>
        <Collapsible.Content className="stack-s" style={{ paddingTop: 4 }}>
          {notes.pattern && (
            <div>
              <strong>{notes.pattern.name}</strong>
              <p style={{ fontSize: "0.92em" }}><strong>When:</strong> {notes.pattern.when}</p>
              <p style={{ fontSize: "0.92em" }}><strong>How:</strong> {notes.pattern.how}</p>
            </div>
          )}
          {notes.key_ideas.length > 0 && <div><strong>Key ideas</strong><ul>{notes.key_ideas.map((idea) => <li key={idea}>{idea}</li>)}</ul></div>}
          {notes.mistakes.length > 0 && <div><strong>Watch out for</strong><ul>{notes.mistakes.map((item) => <li key={item.mistake}>{item.mistake}</li>)}</ul></div>}
        </Collapsible.Content>
      </Collapsible.Root>
    </section>
  );
}

export function ProblemPane({ problem, showGuide, onDismissGuide }: { problem: ProblemDetail; showGuide: boolean; onDismissGuide: () => void }) {
  return (
    <div className="pane" aria-label="Problem">
      <div className="pane-head">
        <span className="pane-title">Problem</span>
        {problem.is_mine && problem.source_type === "imported" && <Link to={`/problems/${problem.id}/edit`} className="btn btn-ghost btn-small"><Pencil size={14} aria-hidden /> Edit</Link>}
      </div>
      <div className="pane-body stack">
        {showGuide && (
          <div className="notice notice-info" data-testid="walkthrough">
            <div className="grow stack-s" style={{ gap: 4 }}>
              <strong>How this works</strong>
              <ol style={{ paddingLeft: "1.1em" }}>
                <li>Write your code in the editor.</li>
                <li><strong>Run</strong> tries the examples. It is not graded, so run as often as you like.</li>
                <li><strong>Submit</strong> checks all the tests and counts as an attempt.</li>
                <li><strong>Ask for a hint</strong> whenever you like. Or select the lines that confuse you, and ask about them.</li>
                <li>Not sure where to begin? Open <strong>Learn</strong>, beside this tab.</li>
              </ol>
            </div>
            <Button variant="ghost" size="small" icon aria-label="Dismiss walkthrough" onClick={onDismissGuide}><X size={15} aria-hidden /></Button>
          </div>
        )}
        <div className="stack-s">
          <h1 style={{ fontSize: "1.25rem" }}>{problem.title}</h1>
          <div className="row">
            {problem.difficulty ? <span className={`badge badge-${problem.difficulty}`}>{DIFFICULTY_LABEL[problem.difficulty]}</span> : <span className="badge">Difficulty not set</span>}
            <Link to={`/path/${problem.unit_id}?tab=lesson`} className="badge" style={{ textDecoration: "none" }}>{problem.unit_title}</Link>
            <span className="badge">Python</span>
          </div>
        </div>
        <ConceptNotes problem={problem} />
        <Markdown>{problem.description}</Markdown>
        {problem.input_format && <section><h3>Input</h3><Markdown>{problem.input_format}</Markdown></section>}
        {problem.output_format && <section><h3>Output</h3><Markdown>{problem.output_format}</Markdown></section>}
        {problem.constraints && <section><h3>Constraints</h3><Markdown>{problem.constraints}</Markdown></section>}
        {problem.examples.length > 0 && (
          <section className="stack-s">
            <h3>Examples</h3>
            {problem.examples.map((example, index) => (
              <div className="example-box" key={index} style={{ position: "relative" }}>
                <span style={{ position: "absolute", top: 1, right: 1 }}><CopyButton text={example.input} label="Copy this input" /></span>
                {example.origin === "generated" && <span className="badge badge-info" style={{ margin: "6px 9px 0" }}>Generated suggestion</span>}
                {example.origin === "learner" && <span className="badge" style={{ margin: "6px 9px 0" }}>Added by you</span>}
                <dl>
                  <dt>{problem.mode === "stdio" ? "Input" : "Call"}</dt><dd>{example.input}</dd>
                  <dt>Expected</dt><dd>{example.expected ?? "Not set"}</dd>
                </dl>
              </div>
            ))}
          </section>
        )}
        {problem.prelude && (
          <Collapsible.Root>
            <Collapsible.Trigger className="collapsible-trigger"><ChevronRight size={15} className="chevron" aria-hidden /> Code already provided for you</Collapsible.Trigger>
            <Collapsible.Content><pre className="console" style={{ maxHeight: 280 }}><code>{problem.prelude}</code></pre></Collapsible.Content>
          </Collapsible.Root>
        )}
        <div className="row subtle">
          {problem.hidden_test_count > 0 && (
            <span className="row" style={{ gap: 2 }}>
              {problem.hidden_test_count} more test{problem.hidden_test_count === 1 ? "" : "s"} run when you submit
              <HelpDialog title="Why are some tests hidden?"><p>Hidden tests check cases the examples do not show, such as empty or very large inputs. You will see whether each one passed, but not its contents, so passing them shows your code handles the general problem.</p></HelpDialog>
            </span>
          )}
          <span>Time limit: {problem.per_test_seconds}s per test</span>
        </div>
        {problem.learner_notes && <section className="stack-s" data-testid="learner-notes"><h3>Your notes</h3><p className="muted" style={{ whiteSpace: "pre-wrap" }}>{problem.learner_notes}</p></section>}
        {problem.source_type !== "curriculum" && (
          <div className="subtle stack-s" style={{ gap: 2 }}>
            <span data-testid="tests-not-official">These are the tests saved with your question, not the original platform's hidden tests.</span>
            <span>Source: {problem.source_name}{problem.source_retrieved_at ? `, retrieved ${new Date(problem.source_retrieved_at).toLocaleDateString()}` : ""}</span>
            {problem.source_note && <span>{problem.source_note}</span>}
            {problem.source_url && /^https?:\/\//.test(problem.source_url) && <a href={problem.source_url} target="_blank" rel="noreferrer noopener" className="row" style={{ gap: 4 }}>View the original <ExternalLink size={13} aria-hidden /></a>}
          </div>
        )}
      </div>
    </div>
  );
}
