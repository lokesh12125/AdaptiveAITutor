/* Charts draw only stored data. Each has a text alternative or a neighbouring table, and identity is never colour alone. */
import { useState } from "react";

export type ActivityDay = { date: string; runs: number; submissions: number; hints: number };

const SERIES = [
  { key: "submissions", label: "Submissions", color: "var(--series-1)" },
  { key: "runs", label: "Runs", color: "var(--series-2)" },
  { key: "hints", label: "Hints", color: "var(--series-3)" },
] as const;

function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function ActivityChart({ days }: { days: ActivityDay[] }) {
  const [active, setActive] = useState<number | null>(null);
  const totals = days.map((d) => d.runs + d.submissions + d.hints);
  const max = Math.max(1, ...totals);
  const sum = totals.reduce((a, b) => a + b, 0);
  const height = 120;
  const width = 560;
  const slot = width / days.length;
  const bar = Math.min(24, slot - 6);
  const top = Math.ceil(max);
  if (sum === 0) return <p className="muted">No activity in the last {days.length} days yet.</p>;
  const shown = active !== null ? days[active] : null;
  return (
    <div className="stack-s">
      <div className="legend" aria-hidden>
        {SERIES.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>)}
      </div>
      <svg viewBox={`0 0 ${width} ${height + 24}`} width="100%" role="img" aria-label={`Activity over the last ${days.length} days: ${sum} actions in total. A table with the same numbers follows.`} onMouseLeave={() => setActive(null)}>
        <line x1="0" x2={width} y1={height} y2={height} stroke="var(--chart-grid)" />
        <line x1="0" x2={width} y1={1} y2={1} stroke="var(--chart-grid)" />
        <text x={0} y={13} textAnchor="start" fontSize="11" fill="var(--text-3)">{top} per day</text>
        {days.map((day, index) => {
          const x = index * slot + (slot - bar) / 2;
          let cursor = height;
          return (
            <g key={day.date} role="img" onMouseEnter={() => setActive(index)} onFocus={() => setActive(index)} onBlur={() => setActive(null)} tabIndex={totals[index] ? 0 : -1} aria-label={`${shortDate(day.date)}: ${day.submissions} submissions, ${day.runs} runs, ${day.hints} hints`}>
              <rect x={index * slot} y={0} width={slot} height={height + 24} fill="transparent" />
              {SERIES.map((s, si) => {
                const value = day[s.key];
                if (!value) return null;
                const h = Math.max(2, (value / top) * (height - 4));
                cursor -= h;
                const isTop = SERIES.slice(si + 1).every((later) => !day[later.key]);
                const y = cursor;
                cursor -= 2; // the surface gap separates stacked segments
                return <path key={s.key} fill={s.color} d={isTop ? `M${x},${y + h}V${y + Math.min(4, h)}Q${x},${y} ${x + 4},${y}H${x + bar - 4}Q${x + bar},${y} ${x + bar},${y + Math.min(4, h)}V${y + h}Z` : `M${x},${y}H${x + bar}V${y + h}H${x}Z`} />;
              })}
              {index % 3 === 0 && <text x={index * slot + slot / 2} y={height + 16} textAnchor="middle" fontSize="11" fill="var(--text-3)">{shortDate(day.date)}</text>}
            </g>
          );
        })}
      </svg>
      <p className="subtle" aria-live="polite" style={{ minHeight: "1.4em" }}>
        {shown ? `${shortDate(shown.date)}: ${shown.submissions} submissions, ${shown.runs} runs, ${shown.hints} hints` : "Point at or focus a day for its numbers."}
      </p>
      <details>
        <summary className="subtle" style={{ cursor: "pointer" }}>Show as a table</summary>
        <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
          <table className="table">
            <thead><tr><th>Date</th><th className="num">Submissions</th><th className="num">Runs</th><th className="num">Hints</th></tr></thead>
            <tbody>{days.filter((_, i) => totals[i]).map((d) => <tr key={d.date}><td>{shortDate(d.date)}</td><td className="num">{d.submissions}</td><td className="num">{d.runs}</td><td className="num">{d.hints}</td></tr>)}</tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

/** A range rather than a single figure, so an estimate never looks more certain than it is. */
export function MasteryRange({ low, high, label }: { low: number | null | undefined; high: number | null | undefined; label: string }) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return <div className="range-track" role="img" aria-label={`${label}: not enough evidence yet`} />;
  }
  return (
    <div className="range-track" role="img" aria-label={`${label}: estimated between ${Math.round(low * 100)} and ${Math.round(high * 100)} percent`}>
      <div className="range-fill" style={{ left: `${low * 100}%`, width: `${(high - low) * 100}%` }} />
    </div>
  );
}

export function ShareBar({ value, label }: { value: number | null | undefined; label: string }) {
  return (
    <div className="bar-track" role="img" aria-label={`${label}: ${value === null || value === undefined ? "no data" : `${Math.round(value * 100)} percent`}`}>
      <div className="bar-fill" style={{ width: `${(value ?? 0) * 100}%` }} />
    </div>
  );
}
