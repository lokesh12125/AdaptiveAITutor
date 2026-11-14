import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, BookOpen, Check, ChevronRight, Clock, Lightbulb, ListChecks, MapPin, TriangleAlert, X } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type { Guide, LearningMode, Path, PathUnit, Plan, ProblemSummary, UnitDetail } from "@/api/types";
import { Markdown } from "@/components/Markdown";
import { ModeSwitch, useLearningMode } from "@/components/ModeSwitch";
import { RouteArt } from "@/components/Shell";
import { TryIt } from "@/components/TryIt";
import { ErrorState, HelpDialog, PageLoading, Ring } from "@/components/ui";

import { ProblemRow } from "./Library";

const STATE_LABEL: Record<PathUnit["state"], string> = { completed: "Looking secure", recommended: "Recommended now", in_progress: "In progress", available: "Ready when you are", needs_foundations: "Builds on earlier topics" };
const GROUPS = [
  { key: "foundations", title: "Foundations", short: "Foundations" }, { key: "algorithms", title: "Algorithms", short: "Algorithms" }, { key: "dsa", title: "Data structures and algorithms", short: "DSA topics" }, { key: "elective", title: "Optional", short: "Optional" },
];

/** One stop on the path: a numbered point on the line, and the topic beside it. */
export function TopicRow({ unit, here, testId }: { unit: PathUnit; here?: boolean; testId?: string }) {
  return (
    <li className="path-item" data-state={unit.state} data-testid={testId} aria-current={here ? "step" : undefined}>
      <div className="path-rail" aria-hidden>
        <span className="path-node">{unit.state === "completed" ? <Check size={17} /> : unit.order}</span>
        <span className="path-line" />
      </div>
      <Link to={`/path/${unit.id}`} className="path-card">
        <div className="grow stack-s" style={{ gap: 3 }}>
          <div className="row" style={{ gap: 8 }}>
            <h3>{unit.title}</h3>
            {here && <span className="badge badge-info">You are here</span>}
            {unit.state === "recommended" && <span className="badge badge-hint">{STATE_LABEL[unit.state]}</span>}
            {unit.state === "completed" && <span className="badge badge-ok">{STATE_LABEL[unit.state]}</span>}
          </div>
          <p className="muted" style={{ fontSize: "0.94em" }}>{unit.summary}</p>
          <div className="path-meta">
            <span>{unit.problems_solved} of {unit.problems_total} solved</span>
            {unit.state !== "recommended" && unit.state !== "completed" && <span>· {STATE_LABEL[unit.state]}</span>}
            {unit.evidence_note !== "Not started" && <span>· {unit.evidence_note}</span>}
          </div>
        </div>
        <Ring value={unit.problems_solved} total={unit.problems_total} label={`${unit.problems_solved} of ${unit.problems_total} problems solved`} />
        <ChevronRight size={18} style={{ color: "var(--text-3)", flex: "none" }} aria-hidden />
      </Link>
    </li>
  );
}

export function PathPage() {
  const query = useQuery<Path>({ queryKey: ["path"], queryFn: () => api<Path>("/path") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="The learning path" onRetry={() => void query.refetch()} />;
  const plan = query.data.recommendation as unknown as Plan;
  const required = query.data.units.filter((unit) => !unit.optional);
  const secure = required.filter((unit) => unit.state === "completed").length;
  const current = query.data.units.find((unit) => unit.id === query.data.current_unit_id);
  const total = query.data.units.reduce((sum, unit) => sum + unit.problems_total, 0);
  return (
    <div className="stack-l">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Learning path</h1>
          <p>{query.data.units.length} topics and {total} problems, in a suggested order. Each topic has a full lesson, then problems to practise it. Nothing is locked, so start wherever you like.</p>
          <p className="path-summary" data-testid="path-position" style={{ marginTop: 10 }}>
            <MapPin size={15} aria-hidden />
            <span>{current ? <>You are working on <strong>{current.title}</strong>. </> : "You have not started a topic yet. "}{secure} of {required.length} topics look secure so far.</span>
            <HelpDialog title="What does secure mean?"><p>The tutor keeps a rough estimate of how well you know each topic, based on your graded attempts. It is an estimate, not a grade, and it never locks a topic. Your Progress page shows the detail.</p></HelpDialog>
          </p>
        </div>
      </div>

      <section className="spotlight" data-testid="path-recommendation">
        <RouteArt />
        <span className="eyebrow">Why this next step</span>
        <h2>{plan.title}</h2>
        <p className="muted">{plan.reason}</p>
        <div className="row">
          {plan.problem_id && <Link className="btn btn-primary" to={`/problems/${plan.problem_id}`}>Go <ArrowRight size={15} aria-hidden /></Link>}
          {(plan.alternatives ?? []).slice(0, 2).map((alternative) => (
            <Link key={alternative.title} className="btn btn-ghost" data-testid="path-alternative" to={alternative.problem_id ? `/problems/${alternative.problem_id}` : alternative.unit_id ? `/path/${alternative.unit_id}` : "/problems"}>{alternative.title}</Link>
          ))}
        </div>
      </section>

      <nav className="chip-row path-jump" aria-label="Jump to a group of topics" data-testid="path-jump">
        {GROUPS.filter((group) => query.data.units.some((unit) => unit.track === group.key)).map((group) => <a key={group.key} className="chip" href={`#track-${group.key}`}>{group.short}</a>)}
        <Link className="chip" to="/problems">All problems</Link>
      </nav>

      {GROUPS.map((group) => {
        const units = query.data.units.filter((unit) => unit.track === group.key);
        if (units.length === 0) return null;
        return (
          <section key={group.key} aria-labelledby={`track-${group.key}`}>
            <h2 className="track-title" id={`track-${group.key}`}>{group.title}</h2>
            <ol className="path">
              {units.map((unit) => <TopicRow key={unit.id} unit={unit} here={unit.id === query.data.current_unit_id} testId="path-unit" />)}
            </ol>
          </section>
        );
      })}
    </div>
  );
}

const DIFFICULTY_ORDER: Record<string, number> = { easy: 0, medium: 1, hard: 2 };

/** Problems grouped by the technique they practise, in the order the lesson teaches them. */
function practiceGroups(problems: ProblemSummary[], guide: Guide | null) {
  const byPattern = new Map<string, ProblemSummary[]>();
  for (const problem of problems) {
    const key = problem.pattern ?? "More practice";
    byPattern.set(key, [...(byPattern.get(key) ?? []), problem]);
  }
  const taught = (guide?.patterns ?? []).map((pattern) => pattern.name).filter((name) => byPattern.has(name));
  const rest = [...byPattern.keys()].filter((name) => !taught.includes(name));
  return [...taught, ...rest].map((name) => ({
    name,
    when: guide?.patterns.find((pattern) => pattern.name === name)?.when ?? null,
    problems: [...(byPattern.get(name) ?? [])].sort((a, b) => (DIFFICULTY_ORDER[a.difficulty ?? ""] ?? 3) - (DIFFICULTY_ORDER[b.difficulty ?? ""] ?? 3)),
  }));
}

/** Which lesson section is on screen, so the list on the left can show where you are. */
function useActiveSection(ids: string[], enabled: boolean): string | null {
  const [active, setActive] = useState<string | null>(null);
  const key = ids.join(",");
  useEffect(() => {
    if (!enabled || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible) setActive(visible.target.id);
    }, { rootMargin: "-76px 0px -70% 0px" });
    for (const id of ids) {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
    // `key` stands for the list of ids.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled]);
  return active;
}

/** A short question to check understanding. It is for the learner only: nothing is graded or stored. */
function KnowledgeCheck({ check }: { check: NonNullable<Guide["checks"]>[number] }) {
  const [chosen, setChosen] = useState<number | null>(null);
  const right = chosen === check.answer;
  return (
    <div className="check card card-tight stack-s" data-testid="knowledge-check">
      <p><strong>{check.question}</strong></p>
      <div className="stack-s" style={{ gap: 5 }} role="group" aria-label={check.question}>
        {check.options.map((option, index) => (
          <button key={option} type="button" className="check-option" aria-pressed={chosen === index} data-result={chosen === index ? (right ? "right" : "wrong") : undefined} onClick={() => setChosen(index)}>
            {chosen === index && (right ? <Check size={15} aria-hidden /> : <X size={15} aria-hidden />)} {option}
          </button>
        ))}
      </div>
      {chosen !== null && <p className="subtle" role="status" data-testid="check-feedback"><strong>{right ? "That's right." : "Not quite, so have another look."}</strong>{right ? ` ${check.why}` : ""}</p>}
    </div>
  );
}

/** Easiest unsolved problem at each difficulty, as a suggested order. */
function practiceRecommendations(problems: ProblemSummary[]): ProblemSummary[] {
  return ["easy", "medium", "hard"].map((level) => problems.find((problem) => problem.difficulty === level && problem.status !== "solved")).filter((problem): problem is ProblemSummary => !!problem);
}

/** Each mode decides what comes first. In revision and interview prep, the long explanation folds away, ready to open. */
function lessonOrder(mode: LearningMode, sectionIds: string[]): string[] {
  if (mode === "revision") return ["key-ideas", "patterns", "mistakes", "complexity", "definitions", "glossary", "checks", "full-lesson"];
  if (mode === "interview") return ["patterns", "complexity", "edge-cases", "mistakes", "when", "key-ideas", "checks", "full-lesson"];
  return ["overview", "definitions", "how", ...sectionIds, "patterns", "mistakes", "edge-cases", "complexity", "when", "checks", "key-ideas", "glossary"];
}

const BLOCK_TITLES: Record<string, string> = {
  overview: "Overview", definitions: "Core definitions", how: "How it works", patterns: "Techniques", mistakes: "Common mistakes", "edge-cases": "Edge cases", complexity: "Time and space", when: "When to use it", checks: "Check your understanding", "key-ideas": "Key ideas", glossary: "Glossary", "full-lesson": "Full lesson",
};

export function UnitPage() {
  const { unitId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const [mode] = useLearningMode();
  const query = useQuery<UnitDetail>({ queryKey: ["unit", unitId], queryFn: () => api<UnitDetail>(`/units/${unitId}`) });
  const guide = (query.data?.guide ?? null) as unknown as Guide | null;
  const groups = useMemo(() => practiceGroups(query.data?.problems ?? [], guide), [query.data, guide]);
  const chosenTab = params.get("tab");
  // A link to one section of the lesson, or one that asks for the lesson, always opens it, whatever the learning mode.
  const tab = guide && (chosenTab === "lesson" || (chosenTab !== "practice" && (Boolean(location.hash) || mode !== "practice"))) ? "lesson" : "practice";
  const sectionIds = useMemo(() => (guide?.sections ?? []).map((section) => section.id), [guide]);
  const order = useMemo(() => lessonOrder(mode, sectionIds), [mode, sectionIds]);
  const activeSection = useActiveSection(order, tab === "lesson");
  const goToTab = (value: string) => {
    setParams({ tab: value }, { replace: true });
    window.scrollTo({ top: 0 });
  };
  // A link from search or a problem may point at one section, which only exists once the lesson has loaded.
  useEffect(() => {
    if (query.data && location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }, [query.data, location.hash]);
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="This topic" onRetry={() => void query.refetch()} />;
  const unit = query.data;
  const solved = unit.problems.filter((problem) => problem.status === "solved").length;
  const recommended = practiceRecommendations(unit.problems);
  const sectionNodes = (guide?.sections ?? []).map((section) => (
    <section key={section.id} className="lesson-section" id={section.id} aria-labelledby={`${section.id}-heading`}>
      <h2 id={`${section.id}-heading`}>{section.title}</h2>
      <Markdown className="lesson-text">{section.body}</Markdown>
      {(section.examples ?? []).map((example) => <TryIt key={example.title} title={example.title} code={example.code} note={example.note} />)}
    </section>
  ));
  const blocks: Record<string, ReactNode> = guide ? {
    overview: (
      <section className="lesson-section" id="overview" aria-labelledby="overview-heading" key="overview">
        <h2 id="overview-heading">Overview</h2>
        <Markdown className="lesson-text">{guide.overview}</Markdown>
        {guide.why && <div className="why-note" data-testid="why-it-matters"><strong>Why this matters.</strong> {guide.why}</div>}
        <div className="grid-2">
          <div className="card card-tight stack-s" data-testid="before-you-start">
            <h3>Before you start</h3>
            <ul className="checklist">{guide.before_you_start.map((item) => <li key={item}><Lightbulb size={15} aria-hidden /><span>{item}</span></li>)}</ul>
            {unit.prerequisites.length > 0 && <p className="subtle">Builds on: {unit.prerequisites.map((p, i) => <span key={p.id}>{i > 0 && ", "}<Link to={`/path/${p.id}`}>{p.title}</Link></span>)}</p>}
          </div>
          <div className="card card-tight stack-s">
            <h3>You will learn</h3>
            <ul className="checklist">{guide.you_will_learn.map((item) => <li key={item}><Check size={15} aria-hidden /><span>{item}</span></li>)}</ul>
          </div>
        </div>
      </section>
    ),
    definitions: guide.definitions?.length ? (
      <section className="lesson-section" id="definitions" aria-labelledby="definitions-heading" key="definitions">
        <h2 id="definitions-heading">Core definitions</h2>
        <dl className="definition-list">{guide.definitions.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.meaning}</dd></div>)}</dl>
      </section>
    ) : null,
    how: guide.how_it_works?.length ? (
      <section className="lesson-section" id="how" aria-labelledby="how-heading" key="how">
        <h2 id="how-heading">How it works, step by step</h2>
        <ol className="how-steps">{guide.how_it_works.map((step) => <li key={step}>{step}</li>)}</ol>
        {guide.diagram && (
          <figure className="diagram" data-testid="diagram">
            <pre tabIndex={0} aria-label={guide.diagram.caption}>{guide.diagram.text}</pre>
            <figcaption>{guide.diagram.caption}</figcaption>
          </figure>
        )}
      </section>
    ) : null,
    patterns: guide.patterns.length ? (
      <section className="lesson-section" id="patterns" aria-labelledby="patterns-heading" key="patterns">
        <h2 id="patterns-heading">Techniques you will use</h2>
        <p className="muted">The practice problems are grouped by these techniques.</p>
        <div className="pattern-grid">
          {guide.patterns.map((pattern) => (
            <div key={pattern.name} className="pattern-card">
              <h3>{pattern.name}</h3>
              <p style={{ fontSize: "0.94em" }}><strong>When:</strong> {pattern.when}</p>
              <p className="muted" style={{ fontSize: "0.94em" }}><strong>How:</strong> {pattern.how}</p>
            </div>
          ))}
        </div>
      </section>
    ) : null,
    mistakes: guide.mistakes.length ? (
      <section className="lesson-section" id="mistakes" aria-labelledby="mistakes-heading" key="mistakes">
        <h2 id="mistakes-heading" className="row" style={{ gap: 8 }}><TriangleAlert size={20} style={{ color: "var(--warn)" }} aria-hidden /> Common mistakes</h2>
        {guide.mistakes.map((item) => (
          <div key={item.mistake} className="mistake">
            <div className="bad"><b>Mistake</b>{item.mistake}</div>
            <div className="good"><b>Instead</b>{item.fix}</div>
          </div>
        ))}
      </section>
    ) : null,
    "edge-cases": guide.edge_cases?.length ? (
      <section className="lesson-section" id="edge-cases" aria-labelledby="edge-heading" key="edge-cases">
        <h2 id="edge-heading">Edge cases to check</h2>
        <ul className="checklist">{guide.edge_cases.map((item) => <li key={item}><TriangleAlert size={15} aria-hidden /><span>{item}</span></li>)}</ul>
      </section>
    ) : null,
    complexity: guide.complexity?.length ? (
      <section className="lesson-section" id="complexity" aria-labelledby="complexity-heading" key="complexity">
        <h2 id="complexity-heading">Time and space</h2>
        <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
          <table className="table"><thead><tr><th scope="col">Operation</th><th scope="col">Cost</th></tr></thead><tbody>{guide.complexity.map((row) => <tr key={row.operation}><td>{row.operation}</td><td>{row.cost}</td></tr>)}</tbody></table>
        </div>
      </section>
    ) : null,
    when: guide.when_to_use?.length ? (
      <section className="lesson-section" id="when" aria-labelledby="when-heading" key="when">
        <h2 id="when-heading">When to use it</h2>
        <ul className="checklist">{guide.when_to_use.map((item) => <li key={item}><Check size={15} aria-hidden /><span>{item}</span></li>)}</ul>
        {guide.related?.length ? <p className="subtle" data-testid="related-topics">Related topics: {guide.related.map((id, index) => <span key={id}>{index > 0 && ", "}<Link to={`/path/${id}`}>{id.replace(/-/g, " ")}</Link></span>)}</p> : null}
      </section>
    ) : null,
    checks: guide.checks?.length ? (
      <section className="lesson-section" id="checks" aria-labelledby="checks-heading" key="checks">
        <h2 id="checks-heading">Check your understanding</h2>
        <p className="muted">Just for you. Nothing here is graded or saved.</p>
        {guide.checks.map((check) => <KnowledgeCheck key={check.question} check={check} />)}
      </section>
    ) : null,
    "key-ideas": (
      <section className="key-ideas lesson-section" id="key-ideas" aria-labelledby="key-ideas-heading" key="key-ideas">
        <h2 id="key-ideas-heading">Key ideas</h2>
        {guide.summary && <p data-testid="revision-summary">{guide.summary}</p>}
        <ul className="checklist">{guide.key_ideas.map((idea) => <li key={idea}><Check size={15} aria-hidden /><span>{idea}</span></li>)}</ul>
      </section>
    ),
    glossary: guide.glossary?.length ? (
      <section className="lesson-section" id="glossary" aria-labelledby="glossary-heading" key="glossary">
        <h2 id="glossary-heading">Glossary</h2>
        <dl className="definition-list" data-testid="glossary">{guide.glossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.meaning}</dd></div>)}</dl>
      </section>
    ) : null,
  } : {};
  const shownOrder = order.filter((id) => id === "full-lesson" || id in blocks ? id === "full-lesson" || !!blocks[id] : sectionIds.includes(id));
  const sectionTitle = (id: string) => guide?.sections.find((section) => section.id === id)?.title ?? BLOCK_TITLES[id] ?? id;
  return (
    <Tabs.Root value={tab} onValueChange={goToTab}>
      <header className="topic-head">
        <Link to="/path" className="crumb"><ArrowLeft size={14} aria-hidden /> Learning path</Link>
        <h1>{unit.title}</h1>
        <p className="muted prose">{unit.summary}</p>
        <div className="row">
          <span className="badge"><ListChecks size={13} aria-hidden /> {unit.problems.length} problems</span>
          {guide && <span className="badge"><Clock size={13} aria-hidden /> {guide.reading_minutes} minute read</span>}
          {solved > 0 && <span className="badge badge-ok"><Check size={13} aria-hidden /> {solved} solved</span>}
        </div>
        <Tabs.List className="tabs-list" aria-label="Lesson or practice">
          {guide && <Tabs.Trigger className="tab" value="lesson" data-testid="tab-lesson"><BookOpen size={15} aria-hidden /> Lesson</Tabs.Trigger>}
          <Tabs.Trigger className="tab" value="practice" data-testid="tab-practice"><ListChecks size={15} aria-hidden /> Practice <span className="tab-count">{unit.problems.length}</span></Tabs.Trigger>
        </Tabs.List>
      </header>

      {guide && (
        <Tabs.Content value="lesson" tabIndex={-1}>
          <div className="lesson-layout">
            <nav className="lesson-toc" aria-label="In this lesson">
              {shownOrder.map((id) => <a key={id} href={`#${id}`} aria-current={activeSection === id ? "true" : undefined}>{sectionTitle(id)}</a>)}
              <a href="#ready">Ready to practise</a>
            </nav>
            <div className="lesson-body">
              <ModeSwitch />
              {shownOrder.map((id) => {
                if (id === "full-lesson") {
                  return (
                    <details key={id} id="full-lesson" className="full-lesson" open={sectionIds.includes(location.hash.slice(1)) || undefined} data-testid="full-lesson">
                      <summary>Read the full lesson</summary>
                      <div className="lesson-body" style={{ marginTop: 18 }}>
                        {blocks.overview}
                        {mode === "interview" && blocks.definitions}
                        {blocks.how}
                        {sectionNodes}
                        {mode === "interview" && blocks.glossary}
                      </div>
                    </details>
                  );
                }
                if (sectionIds.includes(id)) return sectionNodes[sectionIds.indexOf(id)];
                return blocks[id];
              })}
              <div className="lesson-next" id="ready">
                <div className="stack-s" style={{ gap: 4 }}>
                  <h2>Ready to practise?</h2>
                  {recommended.length > 0 ? (
                    <p className="muted" data-testid="practice-recommendation">
                      Try {recommended.map((problem, index) => <span key={problem.id}>{index > 0 && (index === recommended.length - 1 ? ", then " : ", ")}<Link to={`/problems/${problem.id}`}>{problem.title}</Link></span>)}.
                    </p>
                  ) : <p className="muted">You have solved everything here. Nice work.</p>}
                </div>
                <button type="button" className="btn btn-primary" onClick={() => goToTab("practice")} data-testid="start-practice">All {unit.problems.length} problems <ArrowRight size={15} aria-hidden /></button>
              </div>
            </div>
          </div>
        </Tabs.Content>
      )}

      <Tabs.Content value="practice" tabIndex={-1}>
        <section aria-labelledby="practice-heading">
          <div className="practice-head">
            <Ring value={solved} total={unit.problems.length} label={`${solved} of ${unit.problems.length} solved`} />
            <div className="grow">
              <h2 id="practice-heading">Practise {unit.title.toLowerCase()}</h2>
              <p className="subtle">{solved} of {unit.problems.length} solved. Grouped by technique, easiest first.</p>
            </div>
          </div>
          <div className="practice-groups">
            {groups.map((group) => (
              <div key={group.name} className="practice-group">
                <header>
                  <h3>{group.name} <span className="subtle" style={{ fontWeight: 500 }}>· {group.problems.length}</span></h3>
                  {group.when && <p className="subtle">{group.when}</p>}
                </header>
                <div className="practice-list">{group.problems.map((problem) => <ProblemRow key={problem.id} problem={problem} hideUnit hidePattern />)}</div>
              </div>
            ))}
          </div>
        </section>
      </Tabs.Content>
    </Tabs.Root>
  );
}
