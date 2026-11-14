import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ChevronRight, CircleAlert, History } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import type { SubmissionRow } from "@/api/types";
import { CodeBlock } from "@/components/TryIt";
import { Confirm, Button, EmptyState, ErrorState } from "@/components/ui";
import { CATEGORY_LABEL, VERDICT_LABEL } from "@/lib/format";

function dayLabel(date: Date): string {
  const today = new Date();
  const start = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((start(today) - start(date)) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: date.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}

/** Every submission of this problem, grouped by day, with the code that was submitted. */
export function Submissions({ problemId, active, onLoadCode }: { problemId: string; active: boolean; onLoadCode: (code: string) => void }) {
  const query = useQuery<SubmissionRow[]>({ queryKey: ["submissions", problemId], queryFn: () => api<SubmissionRow[]>(`/problems/${problemId}/submissions`), enabled: active });
  const [open, setOpen] = useState<string | null>(null);
  const rows = query.data ?? [];
  const groups: { label: string; rows: SubmissionRow[] }[] = [];
  for (const row of rows) {
    const label = dayLabel(new Date(row.created_at));
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.rows.push(row);
    else groups.push({ label, rows: [row] });
  }
  const accepted = rows.filter((row) => row.verdict === "accepted").length;
  return (
    <div className="pane" aria-label="Submissions">
      <div className="pane-body stack-s" data-testid="submissions">
        {query.isLoading && <div className="skeleton" style={{ height: 60 }} />}
        {query.isError && <ErrorState error={query.error} what="Your submissions" onRetry={() => void query.refetch()} />}
        {query.data && rows.length === 0 && <EmptyState title="No submissions yet">Press Submit to check every test. Each submission is listed here, with its date and the code you sent.</EmptyState>}
        {rows.length > 0 && (
          <p className="row subtle" style={{ gap: 6 }} data-testid="submissions-summary">
            <History size={14} aria-hidden /> {rows.length} submission{rows.length === 1 ? "" : "s"}, {accepted} accepted. Last on {new Date(rows[0].created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}.
          </p>
        )}
        {groups.map((group) => (
          <section key={group.label} className="stack-s" aria-label={group.label} style={{ gap: 6 }}>
            <h3 className="submission-day">{group.label}</h3>
            {group.rows.map((row) => {
              const ok = row.verdict === "accepted";
              const expanded = open === row.id;
              return (
                <div key={row.id} className="submission" data-verdict={row.verdict} data-testid="submission">
                  <button type="button" className="submission-head" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : row.id)}>
                    {ok ? <CheckCircle2 size={16} className="ok" aria-hidden /> : <CircleAlert size={16} className="fail" aria-hidden />}
                    <span className="grow">
                      <strong className={ok ? "ok" : "fail"}>{VERDICT_LABEL[row.verdict ?? ""] ?? row.verdict ?? "Running"}</strong>
                      <span className="subtle"> · {row.total ? `${row.passed} of ${row.total} tests` : "no tests ran"}{row.duration_ms ? ` · ${(row.duration_ms / 1000).toFixed(1)}s` : ""}</span>
                      {row.first_failure && <span className="subtle"><br />First failed: {row.first_failure.name}, {CATEGORY_LABEL[row.first_failure.category ?? ""] ?? row.first_failure.category}</span>}
                    </span>
                    <time className="subtle nowrap" dateTime={row.created_at}>{new Date(row.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</time>
                    <ChevronRight size={14} className="chevron" style={{ transform: expanded ? "rotate(90deg)" : undefined }} aria-hidden />
                  </button>
                  {expanded && (
                    <div className="submission-body stack-s">
                      <CodeBlock code={row.code} />
                      <div className="row">
                        <Confirm
                          trigger={<Button size="small" data-testid="load-submission">Load into the editor</Button>}
                          title="Replace your current code?" description="This puts the code from this submission in the editor. Your current code is replaced, though your earlier submissions stay listed here."
                          confirmLabel="Load this code" onConfirm={() => onLoadCode(row.code)}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        ))}
      </div>
    </div>
  );
}
