import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, Eye, Lightbulb } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { ProblemLearning } from "@/api/types";
import { Markdown } from "@/components/Markdown";
import { Button, ErrorState } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";
import { NewTabLink } from "@/lib/theme";
import { StatusIcon } from "@/pages/Library";

/** The theory behind this problem, read top to bottom: what it asks, then each approach from simplest to best. It never gives this problem's solution. */
export function LearnPane({ problemId, active, onAskTutor }: { problemId: string; active: boolean; onAskTutor: () => void }) {
  const query = useQuery<ProblemLearning>({ queryKey: ["learn", problemId], queryFn: () => api<ProblemLearning>(`/problems/${problemId}/learn`), enabled: active, staleTime: 60_000 });
  const data = query.data;
  const [chosen, setChosen] = useState(0);
  const [stepsShown, setStepsShown] = useState<Record<number, boolean>>({});
  useEffect(() => { setChosen(0); setStepsShown({}); }, [problemId]);
  const approaches = data?.approaches ?? [];
  const index = Math.min(chosen, Math.max(0, approaches.length - 1));
  const approach = approaches[index];
  // The steps of the approach the problem practises are one click away, so the learner can try the idea first.
  const stepsVisible = approach && (!approach.main || approaches.length === 1 || stepsShown[index]);
  return (
    <div className="pane" aria-label="Learn">
      <div className="pane-body theory" data-testid="learn-pane">
        {query.isLoading && <div className="stack-s" role="status" aria-label="Loading"><div className="skeleton" style={{ height: 40 }} /><div className="skeleton" style={{ height: 120 }} /></div>}
        {query.isError && <ErrorState error={query.error} what="This theory" onRetry={() => void query.refetch()} />}
        {data && (
          <>
            {approaches.length > 0 && (
              <div className="approach-tabs" role="tablist" aria-label="Approaches" data-testid="approach-tabs">
                {approaches.map((item, i) => (
                  <button key={item.level} type="button" role="tab" aria-selected={i === index} className="approach-tab" onClick={() => setChosen(i)} data-testid="approach-tab">
                    {item.level}{item.main && approaches.length > 1 ? <span className="approach-best">Best</span> : null}
                  </button>
                ))}
              </div>
            )}

            <section data-testid="learn-understand">
              <h2>The problem</h2>
              <Markdown>{data.summary}</Markdown>
              <p>{data.asking.replace(/`/g, "")}</p>
              {data.worked_example && (
                <p>
                  For example, <code>{data.worked_example.input}</code>{data.worked_example.expected !== null ? <> should give <code>{data.worked_example.expected}</code></> : null}.
                  {data.worked_example.facts.length > 0 ? ` ${data.worked_example.facts.join(" ").replace(/`/g, "")}` : ""}
                </p>
              )}
            </section>

            {approach && (
              <section data-testid="learn-approach" aria-label={approach.level}>
                <h2>Intuition</h2>
                {approach.intuition.map((line) => <p key={line}>{line}</p>)}

                <h2>Approach</h2>
                {stepsVisible ? (
                  <ul className="theory-list" data-testid="approach-steps">{approach.steps.map((step) => <li key={step}>{step}</li>)}</ul>
                ) : (
                  <div className="reveal" data-testid="steps-hidden">
                    <p className="muted">Try turning the intuition into code yourself first. The steps are here when you want them, in words, never as code.</p>
                    <div><Button size="small" onClick={() => setStepsShown({ ...stepsShown, [index]: true })} data-testid="show-steps"><Eye size={14} aria-hidden /> Show the steps</Button></div>
                  </div>
                )}

                <h2>Complexity</h2>
                <ul className="theory-list" data-testid="approach-complexity">
                  <li><strong>Time: {approach.time}</strong>{approach.time_reason ? `, because of ${approach.time_reason}.` : "."}</li>
                  <li><strong>Space: {approach.space}</strong>{approach.space_reason ? `, because of ${approach.space_reason}.` : "."}</li>
                </ul>
              </section>
            )}

            {data.observations.length > 0 && (
              <section>
                <h2>Observations</h2>
                <ul className="theory-list">{data.observations.map((item) => <li key={item}>{item}</li>)}</ul>
              </section>
            )}

            <section>
              <h2>Common mistakes</h2>
              <ul className="theory-list">{data.mistakes.map((item) => <li key={item}>{item}</li>)}</ul>
              <h2>Edge cases to test</h2>
              <ul className="theory-list">{data.edge_cases.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>

            <section className="theory-foot">
              <p className="row" style={{ gap: 6 }}>
                <BookOpen size={15} aria-hidden />
                <NewTabLink to={`/path/${data.concept.unit_id}?tab=lesson${data.concept.section ? `#${data.concept.section.id}` : ""}`} data-testid="learn-lesson-link">
                  Read the theory on {data.concept.unit_title}{data.concept.section ? `: ${data.concept.section.title}` : ""}
                </NewTabLink>
              </p>
              <p className="muted">Stuck on your own code? The tutor looks at what you wrote, and its help gets more specific each time you ask.</p>
              <div><Button variant="hint" size="small" onClick={onAskTutor} data-testid="learn-ask-tutor"><Lightbulb size={14} aria-hidden /> Ask the tutor</Button></div>
              {data.related.length > 0 && (
                <>
                  <h2>Practise the same idea</h2>
                  <div>
                    {data.related.slice(0, 4).map((item) => (
                      <Link key={item.id} to={`/problems/${item.id}`} className="card-link" data-testid="learn-related">
                        <span className="row grow" style={{ gap: 6, flexWrap: "nowrap" }}><StatusIcon status={item.status} /><strong className="grow">{item.title}</strong></span>
                        {item.difficulty && <span className={`badge badge-${item.difficulty}`}>{DIFFICULTY_LABEL[item.difficulty]}</span>}
                        <ArrowRight size={14} aria-hidden />
                      </Link>
                    ))}
                  </div>
                </>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
