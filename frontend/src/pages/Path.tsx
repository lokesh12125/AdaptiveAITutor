import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { Path, PathUnit, Plan, UnitDetail } from "@/api/types";
import { MasteryRange } from "@/components/Charts";
import { Markdown } from "@/components/Markdown";
import { ErrorState, PageLoading } from "@/components/ui";

import { ProblemRow } from "./Library";

const STATE_LABEL: Record<PathUnit["state"], string> = { completed: "Looking secure", recommended: "Recommended now", in_progress: "In progress", available: "Available", needs_foundations: "Has earlier topics" };

export function PathPage() {
  const query = useQuery<Path>({ queryKey: ["path"], queryFn: () => api<Path>("/path") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="The learning path" onRetry={() => void query.refetch()} />;
  const plan = query.data.recommendation as unknown as Plan;
  const groups = [
    { key: "foundations", title: "Foundations" }, { key: "algorithms", title: "Algorithms" }, { key: "dsa", title: "Data structures and algorithms" }, { key: "elective", title: "Optional" },
  ];
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Learning path</h1>
          <p>A suggested order, not a fixed one. Every topic is open, so jump to whatever you want to work on.</p>
        </div>
      </div>
      <section className="card stack-s" data-testid="path-recommendation" style={{ borderColor: "var(--primary)" }}>
        <span className="subtle">Why this next step</span>
        <h2>{plan.title}</h2>
        <p className="muted prose">{plan.reason}</p>
        {plan.problem_id && <div><Link className="btn btn-primary" to={`/problems/${plan.problem_id}`}>Go <ArrowRight size={15} aria-hidden /></Link></div>}
      </section>
      {groups.map((group) => {
        const units = query.data.units.filter((unit) => unit.track === group.key);
        return (
          <section key={group.key} className="stack-s" aria-labelledby={`track-${group.key}`}>
            <h2 id={`track-${group.key}`}>{group.title}</h2>
            <ol className="path" style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {units.map((unit, index) => (
                <li key={unit.id} className="path-item" data-state={unit.state} data-testid="path-unit">
                  <div className="path-rail" aria-hidden>
                    <span className="path-node">{unit.state === "completed" ? <Check size={15} /> : unit.order}</span>
                    {index < units.length - 1 && <span className="path-line" />}
                  </div>
                  <Link to={`/path/${unit.id}`} className="path-card">
                    <div className="row-between">
                      <strong>{unit.title}</strong>
                      <span className={`badge ${unit.state === "recommended" ? "badge-hint" : unit.state === "completed" ? "badge-ok" : ""}`}>{STATE_LABEL[unit.state]}</span>
                    </div>
                    <p className="subtle" style={{ color: "var(--text-2)" }}>{unit.summary}</p>
                    <div className="row" style={{ marginTop: 4 }}>
                      <span className="subtle">{unit.problems_solved} of {unit.problems_total} solved · {unit.evidence_note}</span>
                      <span className="grow" style={{ maxWidth: 160 }}><MasteryRange low={unit.mastery_low} high={unit.mastery_high} label={`${unit.title} estimate`} /></span>
                    </div>
                  </Link>
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </div>
  );
}

export function UnitPage() {
  const { unitId = "" } = useParams();
  const query = useQuery<UnitDetail>({ queryKey: ["unit", unitId], queryFn: () => api<UnitDetail>(`/units/${unitId}`) });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="This topic" onRetry={() => void query.refetch()} />;
  const unit = query.data;
  return (
    <div className="stack-l">
      <div className="stack-s">
        <Link to="/path" className="row" style={{ gap: 4 }}><ArrowLeft size={14} aria-hidden /> Learning path</Link>
        <h1>{unit.title}</h1>
        <p className="muted prose">{unit.summary}</p>
        {unit.prerequisites.length > 0 && <p className="subtle">Builds on: {unit.prerequisites.map((p, i) => <span key={p.id}>{i > 0 && ", "}<Link to={`/path/${p.id}`}>{p.title}</Link></span>)}</p>}
      </div>
      <section className="stack-s" aria-labelledby="practice-heading">
        <h2 id="practice-heading">Practise</h2>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {unit.problems.map((problem) => <ProblemRow key={problem.id} problem={problem} />)}
        </div>
      </section>
      <section className="stack" aria-labelledby="lessons-heading">
        <h2 id="lessons-heading">Key ideas</h2>
        {unit.lessons.map((lesson) => (
          <article key={lesson.title} className="card stack-s">
            <h3>{lesson.title}</h3>
            {lesson.objective && <p className="subtle">{lesson.objective}</p>}
            <Markdown>{lesson.explanation}</Markdown>
            {(lesson.examples ?? []).map((example, index) => (
              <div key={index} className="stack-s" style={{ gap: 4 }}>
                {example.title ? <span className="subtle">{String(example.title)}</span> : null}
                <pre className="console" style={{ maxHeight: "none" }}><code>{String(example.code)}</code></pre>
              </div>
            ))}
          </article>
        ))}
      </section>
    </div>
  );
}
