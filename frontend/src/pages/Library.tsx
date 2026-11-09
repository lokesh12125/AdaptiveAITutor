import { useQuery } from "@tanstack/react-query";
import { Check, Circle, CircleDot, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type { ProblemSummary } from "@/api/types";
import { EmptyState, ErrorState, Select } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";

export function StatusIcon({ status }: { status: ProblemSummary["status"] }) {
  if (status === "solved") return <span className="status-dot" style={{ color: "var(--ok)" }} title="Solved"><Check size={17} aria-hidden /><span className="sr-only">Solved</span></span>;
  if (status === "in_progress") return <span className="status-dot" style={{ color: "var(--hint)" }} title="In progress"><CircleDot size={16} aria-hidden /><span className="sr-only">In progress</span></span>;
  return <span className="status-dot" style={{ color: "var(--border-strong)" }} title="Not started"><Circle size={15} aria-hidden /><span className="sr-only">Not started</span></span>;
}

export function ProblemRow({ problem }: { problem: ProblemSummary }) {
  return (
    <Link to={`/problems/${problem.id}`} className="problem-row" data-testid="problem-row">
      <StatusIcon status={problem.status} />
      <span className="grow">
        <span className="problem-row-title">{problem.title}</span>
        {problem.is_mine && <span className="badge badge-info" style={{ marginLeft: 8 }}>Added by you</span>}
        <br />
        <span className="subtle">{problem.unit_title}{problem.source_type === "imported" && problem.source_name && problem.source_name !== "Added by you" ? ` · from ${problem.source_name}` : ""}</span>
      </span>
      <span className="badge hide-mobile">Python</span>
      <span className="badge">{problem.difficulty ? DIFFICULTY_LABEL[problem.difficulty] : "Not rated"}</span>
    </Link>
  );
}

export function Library() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const unit = params.get("unit") ?? "all";
  const difficulty = params.get("difficulty") ?? "all";
  const status = params.get("status") ?? "all";
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "all" || !value) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
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
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Problems</h1>
          <p>All problems run in Python, the language currently supported here.</p>
        </div>
        <Link to="/problems/new" className="btn btn-primary" data-testid="add-question"><Plus size={15} aria-hidden /> Add question</Link>
      </div>
      <div className="filters" role="search">
        <label className="row" style={{ position: "relative", gap: 0 }}>
          <span className="sr-only">Search problems</span>
          <Search size={15} aria-hidden style={{ position: "absolute", left: 10, color: "var(--text-3)" }} />
          <input className="input" style={{ paddingLeft: 32 }} placeholder="Search by title or concept" value={search} onChange={(e) => setSearch(e.target.value)} data-testid="search" />
        </label>
        <Select label="Filter by topic" value={unit} onChange={(value) => setFilter("unit", value)} options={[{ value: "all", label: "All topics" }, ...(units.data ?? []).map((u) => ({ value: u.id, label: u.title }))]} />
        <Select label="Filter by difficulty" value={difficulty} onChange={(value) => setFilter("difficulty", value)} options={[{ value: "all", label: "Any difficulty" }, { value: "easy", label: "Easy" }, { value: "medium", label: "Medium" }, { value: "hard", label: "Hard" }]} />
        <Select label="Filter by status" value={status} onChange={(value) => setFilter("status", value)} options={[{ value: "all", label: "Any status" }, { value: "not_started", label: "Not started" }, { value: "in_progress", label: "In progress" }, { value: "solved", label: "Solved" }]} />
      </div>
      {problems.isError ? <ErrorState error={problems.error} what="The problem list" onRetry={() => void problems.refetch()} /> : (
        <section className="card" style={{ padding: 0, overflow: "hidden" }} aria-busy={problems.isFetching}>
          {problems.isLoading && <div className="stack-s" style={{ padding: 14 }} role="status" aria-label="Loading problems"><div className="skeleton" style={{ height: 40 }} /><div className="skeleton" style={{ height: 40 }} /><div className="skeleton" style={{ height: 40 }} /></div>}
          {problems.data && problems.data.length === 0 && (
            <EmptyState title={filtered ? "No problems match" : "No problems yet"} action={filtered ? <button type="button" className="btn" onClick={() => { setSearch(""); setParams({}, { replace: true }); }}>Clear filters</button> : undefined}>
              {filtered ? "Try a different search or fewer filters." : undefined}
            </EmptyState>
          )}
          {problems.data?.map((problem) => <ProblemRow key={problem.id} problem={problem} />)}
        </section>
      )}
      {problems.data && <p className="subtle" role="status">{problems.data.length} problem{problems.data.length === 1 ? "" : "s"}</p>}
    </div>
  );
}
