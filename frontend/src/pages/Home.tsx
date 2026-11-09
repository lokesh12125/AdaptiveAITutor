import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Plan } from "@/api/types";
import { MasteryRange } from "@/components/Charts";
import { EmptyState, ErrorState, HelpDialog, PageLoading } from "@/components/ui";
import { timeAgo, VERDICT_LABEL } from "@/lib/format";
import { useSession } from "@/lib/session";

type HomeData = {
  recommendation: Plan; is_new: boolean; solved_count: number;
  unfinished: { problem_id: string; title: string; unit_title: string; last_active: string; attempted: boolean }[];
  recent_activity: { problem_id: string; title: string; verdict: string | null; passed: number; total: number; at: string }[];
  topics: { unit_id: string; title: string; band: string; band_label: string; low: number; high: number }[];
};

export function Home() {
  const { user } = useSession();
  const query = useQuery<HomeData>({ queryKey: ["home"], queryFn: () => api<HomeData>("/home") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="Your home page" onRetry={() => void query.refetch()} />;
  const { recommendation: plan, unfinished, recent_activity: recent, topics, is_new: isNew } = query.data;
  const first = user?.name?.split(" ")[0];
  return (
    <div className="stack-l">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{isNew ? `Welcome${user?.is_demo ? "" : `, ${first}`}` : `Welcome back${user?.is_demo ? "" : `, ${first}`}`}</h1>
          <p>{isNew ? "Here is a good place to begin." : `You have solved ${query.data.solved_count} problem${query.data.solved_count === 1 ? "" : "s"} so far.`}</p>
        </div>
      </div>

      <section className="card stack-s" data-testid="recommendation" style={{ borderColor: "var(--primary)" }} aria-labelledby="next-heading">
        <span className="subtle" id="next-heading">Recommended next</span>
        <h2>{plan.title}</h2>
        <p className="muted prose">{plan.reason}</p>
        <div className="row" style={{ marginTop: 6 }}>
          {plan.problem_id && <Link to={`/problems/${plan.problem_id}`} className="btn btn-primary" data-testid="recommended-start">{plan.action === "continue_current" ? "Continue" : "Start"} <ArrowRight size={15} aria-hidden /></Link>}
          <Link to="/path" className="btn btn-ghost">See the full path</Link>
        </div>
      </section>

      <div className="grid-2">
        <section className="card" aria-labelledby="unfinished-heading">
          <h2 className="card-title" id="unfinished-heading">Unfinished</h2>
          {unfinished.length === 0 ? <p className="muted">Nothing in progress. Problems you start will wait for you here, with your code saved.</p> : (
            <div className="stack-s">
              {unfinished.map((item) => (
                <Link key={item.problem_id} to={`/problems/${item.problem_id}`} className="row-between" style={{ textDecoration: "none", color: "inherit" }}>
                  <span className="grow"><strong>{item.title}</strong><br /><span className="subtle">{item.unit_title} · {timeAgo(item.last_active)}</span></span>
                  <ArrowRight size={15} aria-hidden />
                </Link>
              ))}
            </div>
          )}
        </section>
        <section className="card" aria-labelledby="topics-heading">
          <div className="row" style={{ gap: 2 }}>
            <h2 id="topics-heading">Topic progress</h2>
            <HelpDialog title="What does this show?"><p>A rough range for how well you know each topic, based on your coding activity. The range is wide when there is not much evidence, and narrows as you practise. It is an estimate, not a grade.</p></HelpDialog>
          </div>
          {topics.length === 0 ? <p className="muted" style={{ marginTop: 8 }}>Topics appear here once you have made a graded attempt.</p> : (
            <div style={{ marginTop: 6 }}>
              {topics.map((topic) => (
                <div className="topic-row" key={topic.unit_id}>
                  <Link to={`/path/${topic.unit_id}`} style={{ color: "inherit", textDecoration: "none" }}>{topic.title}</Link>
                  <MasteryRange low={topic.low} high={topic.high} label={topic.title} />
                  <span className="subtle">{topic.band_label}</span>
                </div>
              ))}
              <div style={{ marginTop: 10 }}><Link to="/progress">See all your progress</Link></div>
            </div>
          )}
        </section>
      </div>

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
  );
}
