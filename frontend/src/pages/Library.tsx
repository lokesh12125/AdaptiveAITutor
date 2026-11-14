import { useQuery } from "@tanstack/react-query";
import { BookOpen, Check, ChevronRight, Circle, CircleDot, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type { ProblemSummary } from "@/api/types";
import { EmptyState, ErrorState, Ring, Select } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";

export function StatusIcon({ status }: { status: ProblemSummary["status"] }) {
  if (status === "solved") return <span className="status-dot" style={{ color: "var(--ok)" }} title="Solved"><Check size={17} aria-hidden /><span className="sr-only">Solved</span></span>;
  if (status === "in_progress") return <span className="status-dot" style={{ color: "var(--hint)" }} title="In progress"><CircleDot size={16} aria-hidden /><span className="sr-only">In progress</span></span>;
  return <span className="status-dot" style={{ color: "var(--border-strong)" }} title="Not started"><Circle size={15} aria-hidden /><span className="sr-only">Not started</span></span>;
}

export function ProblemRow({ problem, hideUnit, hidePattern }: { problem: ProblemSummary; hideUnit?: boolean; hidePattern?: boolean }) {
  const imported = problem.source_type === "imported" && problem.source_name && problem.source_name !== "Added by you" ? `from ${problem.source_name}` : null;
  const detail = [hideUnit ? null : problem.unit_title, hidePattern ? null : problem.pattern, imported].filter(Boolean).join(" · ");
  return (
    <Link to={`/problems/${problem.id}`} className="problem-row" data-testid="problem-row">
      <StatusIcon status={problem.status} />
      <span className="grow">
        <span className="problem-row-title">{problem.title}</span>
        {problem.is_mine && <span className="badge badge-info" style={{ marginLeft: 8 }}>Added by you</span>}
        {detail && <><br /><span className="subtle">{detail}</span></>}
      </span>
      <span className={`badge ${problem.difficulty ? `badge-${problem.difficulty}` : ""}`}>{problem.difficulty ? DIFFICULTY_LABEL[problem.difficulty] : "Not rated"}</span>
      <span className="row-action hide-mobile" aria-hidden>{problem.status === "solved" ? "Review" : problem.status === "in_progress" ? "Continue" : "Solve"}</span>
    </Link>
  );
}

function TopicGroup({ unitId, title, problems, startOpen, own }: { unitId: string; title: string; problems: ProblemSummary[]; startOpen: boolean; own?: boolean }) {
  const [open, setOpen] = useState(startOpen);
  useEffect(() => setOpen(startOpen), [startOpen]);
  const solved = problems.filter((problem) => problem.status === "solved").length;
  return (
    <section className="topic-group" data-open={open} data-testid={own ? "your-questions-group" : "topic-group"} aria-label={title}>
      <div className="topic-group-head">
        <button type="button" className="topic-group-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          <ChevronRight size={17} className="chev" aria-hidden />
          <Ring value={solved} total={problems.length} size={38} label={`${solved} of ${problems.length} solved`} />
          <span className="grow">
            <strong style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem" }}>{title}</strong><br />
            <span className="subtle">{problems.length} problem{problems.length === 1 ? "" : "s"} · {solved} solved</span>
          </span>
        </button>
        {own
          ? <Link to="/problems/new" className="btn btn-ghost btn-small" aria-label="Add another question"><Plus size={14} aria-hidden /><span className="hide-mobile">Add</span></Link>
          : <Link to={`/path/${unitId}?tab=lesson`} className="btn btn-ghost btn-small" aria-label={`Read the lesson on ${title}`}><BookOpen size={14} aria-hidden /><span className="hide-mobile">Lesson</span></Link>}
      </div>
      {open && problems.map((problem) => <ProblemRow key={problem.id} problem={problem} hideUnit={!own} />)}
    </section>
  );
}

export function Library() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const unit = params.get("unit") ?? "all";
  const difficulty = params.get("difficulty") ?? "all";
  const status = params.get("status") ?? "all";
  // The search box updates after a short delay, so this must read the newest filters, or it would undo one chosen meanwhile.
  const latest = useRef(params);
  latest.current = params;
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(latest.current);
    if (value === "all" || !value) next.delete(key);
    else next.set(key, value);
    if (next.toString() !== latest.current.toString()) setParams(next, { replace: true });
  };
  useEffect(() => {
    const timer = window.setTimeout(() => setFilter("q", search.trim()), 250);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);
  const queryString = params.toString();
  const problems = useQuery<ProblemSummary[]>({ queryKey: ["problems", queryString], queryFn: () => api<ProblemSummary[]>(`/problems?${queryString}`), placeholderData: (previous) => previous });
  const units = useQuery<{ id: string; title: string }[]>({ queryKey: ["unit-options"], queryFn: () => api("/units/options"), staleTime: 300_000 });
  const filtered = queryString !== "";
  const groups = useMemo(() => {
    const byUnit = new Map<string, ProblemSummary[]>();
    for (const problem of problems.data ?? []) byUnit.set(problem.unit_id, [...(byUnit.get(problem.unit_id) ?? []), problem]);
    // In learning order. A topic missing from the options still shows, at the end.
    const order = (units.data ?? []).map((option) => option.id);
    const rank = (id: string) => { const at = order.indexOf(id); return at === -1 ? order.length : at; };
    return [...byUnit.entries()].sort(([a], [b]) => rank(a) - rank(b)).map(([id, rows]) => ({ id, title: rows[0].unit_title, rows }));
  }, [problems.data, units.data]);
  const mine = (problems.data ?? []).filter((problem) => problem.is_mine);
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Practice</h1>
          <p>Every problem, sorted by topic. Each topic has a lesson you can read first. All problems run in Python.</p>
        </div>
        <Link to="/problems/new" className="btn btn-primary" data-testid="add-question"><Plus size={15} aria-hidden /> Add question</Link>
      </div>
      <div className="filters" role="search">
        <label className="row" style={{ position: "relative", gap: 0 }}>
          <span className="sr-only">Search problems</span>
          <Search size={15} aria-hidden style={{ position: "absolute", left: 11, color: "var(--text-3)" }} />
          <input className="input" style={{ paddingLeft: 33 }} placeholder="Search by title, technique or concept" value={search} onChange={(e) => setSearch(e.target.value)} data-testid="search" />
        </label>
        <Select label="Filter by topic" value={unit} onChange={(value) => setFilter("unit", value)} options={[{ value: "all", label: "All topics" }, ...(units.data ?? []).map((u) => ({ value: u.id, label: u.title }))]} />
        <Select label="Filter by difficulty" value={difficulty} onChange={(value) => setFilter("difficulty", value)} options={[{ value: "all", label: "Any difficulty" }, { value: "easy", label: "Easy" }, { value: "medium", label: "Medium" }, { value: "hard", label: "Hard" }]} />
        <Select label="Filter by status" value={status} onChange={(value) => setFilter("status", value)} options={[{ value: "all", label: "Any status" }, { value: "not_started", label: "Not started" }, { value: "in_progress", label: "In progress" }, { value: "solved", label: "Solved" }]} />
      </div>
      {problems.isError ? <ErrorState error={problems.error} what="The problem list" onRetry={() => void problems.refetch()} /> : (
        <section className="stack-s" aria-busy={problems.isFetching} aria-label="Problems by topic">
          {problems.isLoading && <div className="stack-s" role="status" aria-label="Loading problems"><div className="skeleton" style={{ height: 64 }} /><div className="skeleton" style={{ height: 64 }} /><div className="skeleton" style={{ height: 64 }} /></div>}
          {problems.data && problems.data.length === 0 && (
            <div className="card">
              <EmptyState title={filtered ? "No problems match" : "No problems yet"} action={filtered ? <button type="button" className="btn" onClick={() => { setSearch(""); setParams({}, { replace: true }); }}>Clear filters</button> : undefined}>
                {filtered ? "Try a different search or fewer filters." : undefined}
              </EmptyState>
            </div>
          )}
          {mine.length > 0 && <TopicGroup key="mine" unitId="" title="Your questions" problems={mine} startOpen own />}
          {groups.map((group, index) => <TopicGroup key={group.id} unitId={group.id} title={group.title} problems={group.rows} startOpen={filtered || (index === 0 && mine.length === 0)} />)}
        </section>
      )}
      {problems.data && <p className="subtle" role="status">{problems.data.length} problem{problems.data.length === 1 ? "" : "s"} in {groups.length} topic{groups.length === 1 ? "" : "s"}</p>}
    </div>
  );
}
