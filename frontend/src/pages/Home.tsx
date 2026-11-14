import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Path, Plan } from "@/api/types";
import { MasteryRange } from "@/components/Charts";
import { RouteLine } from "@/components/RouteLine";
import { RouteArt } from "@/components/Shell";
import { EmptyState, ErrorState, HelpDialog, PageLoading } from "@/components/ui";
import { timeAgo, VERDICT_LABEL } from "@/lib/format";
import { useSession } from "@/lib/session";

import { TopicRow } from "./Path";

type HomeData = {
  recommendation: Plan; is_new: boolean; solved_count: number;
  unfinished: { problem_id: string; title: string; unit_title: string; last_active: string; attempted: boolean }[];
  recent_activity: { problem_id: string; title: string; verdict: string | null; passed: number; total: number; at: string }[];
  topics: { unit_id: string; title: string; band: string; band_label: string; low: number; high: number }[];
};

const NEXT_ORDER = ["recommended", "in_progress", "available", "needs_foundations", "completed"];

export function Home() {
  const { user } = useSession();
  const query = useQuery<HomeData>({ queryKey: ["home"], queryFn: () => api<HomeData>("/home") });
  const path = useQuery<Path>({ queryKey: ["path"], queryFn: () => api<Path>("/path") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="Your home page" onRetry={() => void query.refetch()} />;
  const { recommendation: plan, unfinished, recent_activity: recent, topics, is_new: isNew, solved_count: solved } = query.data;
  const first = user?.name?.split(" ")[0];
  const nextTopics = [...(path.data?.units ?? [])].sort((a, b) => NEXT_ORDER.indexOf(a.state) - NEXT_ORDER.indexOf(b.state) || a.order - b.order).slice(0, 4);
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{isNew ? `Welcome${user?.is_demo ? "" : `, ${first}`}` : `Welcome back${user?.is_demo ? "" : `, ${first}`}`}</h1>
          <p>{isNew ? "Here is a good place to begin." : `You have solved ${solved} problem${solved === 1 ? "" : "s"} so far. Keep going.`}</p>
        </div>
      </div>
      <div className="home-grid">
        <div className="stack-l" style={{ minWidth: 0 }}>
          <section className="spotlight" data-testid="recommendation" aria-labelledby="next-heading">
            <RouteArt />
            <span className="eyebrow">{plan.action === "continue_current" ? "Continue where you left off" : "Your next step"}</span>
            <h2 id="next-heading">{plan.title}</h2>
            <p className="muted">{plan.reason}</p>
            <RouteLine route={plan.route} />
            <div className="row">
              {plan.problem_id && <Link to={`/problems/${plan.problem_id}`} className="btn btn-primary" data-testid="recommended-start">{plan.action === "continue_current" ? "Continue" : "Start"} <ArrowRight size={15} aria-hidden /></Link>}
              <Link to="/path" className="btn">See all topics</Link>
              <Link to="/problems/new" className="btn btn-ghost" data-testid="home-add-question">Bring your own question</Link>
            </div>
          </section>

          {nextTopics.length > 0 && (
            <section aria-labelledby="next-topics-heading">
              <div className="section-title">
                <h2 id="next-topics-heading">Topics to learn</h2>
                <Link to="/path">All {path.data?.units.length} topics</Link>
              </div>
              <ol className="path path-plain">{nextTopics.map((unit) => <TopicRow key={unit.id} unit={unit} here={unit.id === path.data?.current_unit_id} />)}</ol>
            </section>
          )}

          <section className="card" aria-labelledby="recent-heading">
            <h2 className="card-title" id="recent-heading">Recent activity</h2>
            {recent.length === 0 ? <EmptyState title="No submissions yet" action={plan.problem_id ? <Link className="btn" to={`/problems/${plan.problem_id}`}>Try your first problem</Link> : undefined}>Your submitted attempts will be listed here.</EmptyState> : (
              <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
                <table className="table">
                  <thead><tr><th>Problem</th><th>Result</th><th className="num">Tests</th><th>When</th></tr></thead>
                  <tbody>
                    {recent.map((row, index) => (
                      <tr key={index}>
                        <td><Link to={`/problems/${row.problem_id}`}>{row.title}</Link></td>
                        <td>{VERDICT_LABEL[row.verdict ?? ""] ?? row.verdict ?? "Running"}</td>
                        <td className="num">{row.total ? `${row.passed}/${row.total}` : "–"}</td>
                        <td className="nowrap">{timeAgo(row.at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <aside className="home-side" aria-label="Your progress">
          <section className="card card-tight" aria-label="Summary">
            <div className="mini-stats" data-testid="home-stats">
              <div><b>{solved}</b><span>Solved</span></div>
              <div><b>{unfinished.length}</b><span>In progress</span></div>
              <div><b>{topics.length}</b><span>Topics started</span></div>
            </div>
          </section>
          <section className="card card-tight" aria-labelledby="unfinished-heading">
            <h2 className="card-title" id="unfinished-heading" style={{ fontSize: "1.05rem" }}>Unfinished</h2>
            {unfinished.length === 0 ? <p className="muted">Nothing in progress. Problems you start will wait here, with your code saved.</p> : (
              <div>
                {unfinished.map((item) => (
                  <Link key={item.problem_id} to={`/problems/${item.problem_id}`} className="card-link">
                    <span className="grow"><strong>{item.title}</strong><br /><span className="subtle">{item.unit_title} · {timeAgo(item.last_active)}</span></span>
                    <ArrowRight size={15} aria-hidden />
                  </Link>
                ))}
              </div>
            )}
          </section>
          <section className="card card-tight" aria-labelledby="topics-heading">
            <div className="row" style={{ gap: 2 }}>
              <h2 id="topics-heading" style={{ fontSize: "1.05rem" }}>Topic progress</h2>
              <HelpDialog title="What does this show?"><p>A rough range for how well you know each topic, based on your coding activity. The range is wide when there is not much evidence, and narrows as you practise. It is an estimate, not a grade.</p></HelpDialog>
            </div>
            {topics.length === 0 ? <p className="muted" style={{ marginTop: 6 }}>Topics appear here once you have made a graded attempt.</p> : (
              <div style={{ marginTop: 4 }}>
                {topics.map((topic) => (
                  <div className="topic-row" key={topic.unit_id}>
                    <Link to={`/path/${topic.unit_id}`} style={{ color: "inherit", textDecoration: "none" }}>{topic.title}</Link>
                    <MasteryRange low={topic.low} high={topic.high} label={topic.title} />
                    <span className="subtle">{topic.band_label}</span>
                  </div>
                ))}
                <div style={{ marginTop: 8 }}><Link to="/progress">See all your progress</Link></div>
              </div>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
