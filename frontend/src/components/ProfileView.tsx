import { ArrowDown, ArrowUp, Award, CalendarDays, Check, Flame, Minus } from "lucide-react";
import { Link } from "react-router-dom";

import type { Profile } from "@/api/types";
import { HelpDialog, Stat } from "@/components/ui";
import { timeAgo, VERDICT_LABEL } from "@/lib/format";

const LEVEL_WORDS: Record<string, string> = { low: "Low", moderate: "Moderate", high: "High" };
const PROGRESS_WORDS: Record<string, string> = { improving: "Improving", steady: "Steady", stalled: "Stalled", regressing: "Going back", solved: "Solved", unknown: "Unknown" };
const percent = (value: number | null | undefined) => (value === null || value === undefined ? "–" : `${Math.round(value * 100)}%`);
const unknown = <span className="subtle">Unknown</span>;

/** A calendar of daily activity over about six months, one square per day. Counts are also in each square's label. */
function Calendar({ days }: { days: Profile["calendar"] }) {
  const max = Math.max(1, ...days.map((d) => d.count));
  const first = new Date(`${days[0]?.date}T00:00:00`);
  const offset = (first.getDay() + 6) % 7; // weeks start on Monday
  const cells = [...Array(offset).fill(null), ...days];
  const weeks: (Profile["calendar"][number] | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const level = (count: number) => (count === 0 ? 0 : Math.min(4, Math.ceil((count / max) * 4)));
  const active = days.filter((d) => d.count > 0).length;
  return (
    <div className="stack-s">
      <div className="calendar" role="img" aria-label={`Activity on ${active} of the last ${days.length} days`} data-testid="calendar">
        {weeks.map((week, i) => (
          <div key={i} className="calendar-week">
            {week.map((day, j) => day ? <span key={j} className="calendar-day" data-level={level(day.count)} title={`${day.date}: ${day.count} action${day.count === 1 ? "" : "s"}`} /> : <span key={j} className="calendar-day calendar-empty" />)}
          </div>
        ))}
      </div>
      <div className="row subtle" style={{ gap: 6 }}>
        Less {[0, 1, 2, 3, 4].map((n) => <span key={n} className="calendar-day" data-level={n} aria-hidden />)} More
        <span className="grow" />{active} active day{active === 1 ? "" : "s"} in the last six months
      </div>
    </div>
  );
}

function Change({ better }: { better: boolean | null }) {
  if (better === null) return <Minus size={14} className="subtle" aria-label="No change" />;
  return better ? <ArrowUp size={14} className="ok-text" aria-label="Better" /> : <ArrowDown size={14} className="warn-text" aria-label="Worse" />;
}

function show(value: number | null, unit: string): string {
  if (value === null || value === undefined) return "–";
  return unit === "%" ? `${Math.round(value * 100)}%` : `${value}${unit}`;
}

/** The learner's profile. The same view is shown to the learner and, for a joined class, to their teacher. */
export function ProfileView({ profile, own }: { profile: Profile; own: boolean }) {
  const t = profile.totals;
  const difficulty = t.solved_by_difficulty;
  const you = own ? "you" : "this learner";
  return (
    <div className="stack-l">
      <div className="grid-stats" data-testid="profile-stats">
        <Stat label="Problems solved" value={t.solved} note={`of ${t.started} started`} />
        <Stat label="Acceptance rate" value={percent(t.acceptance_rate)} note={`${t.accepted_submissions} of ${t.submissions} submissions`} />
        <Stat label="Solved first time" value={t.first_try_solves} note="On the first submission" />
        <Stat label="Solved without hints" value={t.solved_without_hints} />
        <Stat label="Current streak" value={`${t.current_streak} day${t.current_streak === 1 ? "" : "s"}`} note={`Longest: ${t.longest_streak}`} />
        <Stat label="Hints per solve" value={t.hints_per_solved ?? "–"} note={`${t.hints_total} hints in all`} />
      </div>

      <div className="grid-2">
        <section className="card stack-s" aria-labelledby="difficulty-heading">
          <h2 id="difficulty-heading">Solved by difficulty</h2>
          {(["easy", "medium", "hard"] as const).map((level) => (
            <div key={level} className="difficulty-row" data-testid={`difficulty-${level}`}>
              <span className={`badge badge-${level}`}>{level[0].toUpperCase() + level.slice(1)}</span>
              <div className="bar-track grow"><div className="bar-fill" data-level={level} style={{ width: `${difficulty[level][1] ? (difficulty[level][0] / difficulty[level][1]) * 100 : 0}%` }} /></div>
              <span className="nowrap"><strong>{difficulty[level][0]}</strong> <span className="subtle">of {difficulty[level][1]}</span></span>
            </div>
          ))}
          <p className="subtle">{t.runs} runs, {t.submissions} submissions, {t.days_active} active day{t.days_active === 1 ? "" : "s"}{t.questions_added ? `, ${t.questions_added} question${t.questions_added === 1 ? "" : "s"} added` : ""}.</p>
        </section>
        <section className="card stack-s" aria-labelledby="milestones-heading">
          <h2 id="milestones-heading" className="row" style={{ gap: 8 }}><Award size={18} aria-hidden /> Milestones</h2>
          <ul className="milestones" data-testid="milestones">
            {profile.milestones.map((m) => <li key={m.id} data-achieved={m.achieved}>{m.achieved ? <Check size={14} aria-hidden /> : <span className="milestone-dot" aria-hidden />}<span>{m.title}</span><span className="sr-only">{m.achieved ? ", achieved" : ", not yet"}</span></li>)}
          </ul>
        </section>
      </div>

      <section className="card stack-s" aria-labelledby="calendar-heading">
        <h2 id="calendar-heading" className="row" style={{ gap: 8 }}><CalendarDays size={18} aria-hidden /> Activity</h2>
        <Calendar days={profile.calendar} />
      </section>

      <section className="card stack" aria-labelledby="improvement-heading">
        <div className="row" style={{ gap: 2 }}>
          <h2 id="improvement-heading">How {you === "you" ? "you have" : "they have"} improved</h2>
          <HelpDialog title="How is improvement measured?"><p>The first few problems solved are compared with the most recent ones, using submissions, hints and time per solve. Fewer submissions and hints, and less time, mean more independent solving. The knowledge checks are the only measure of learning gain, and they are separate from the tutor's own estimates.</p></HelpDialog>
        </div>
        {profile.improvement.then_now ? (
          <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
            <table className="table" data-testid="then-now">
              <thead><tr><th scope="col">Measure</th><th scope="col" className="num">First {profile.improvement.then_now.count} solved</th><th scope="col" className="num">Latest {profile.improvement.then_now.count} solved</th><th scope="col">Change</th></tr></thead>
              <tbody>{profile.improvement.then_now.rows.map((row) => (
                <tr key={row.label}><td>{row.label}</td><td className="num">{show(row.early, row.unit)}</td><td className="num">{show(row.recent, row.unit)}</td><td><Change better={row.better} /> <span className="subtle">{row.better === null ? "Same" : row.better ? "Better" : "Worse"}</span></td></tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="muted" data-testid="then-now-empty">Solve at least four problems to compare {you === "you" ? "your" : "their"} early and recent work.</p>}
        <div>
          <h3 style={{ marginBottom: 8 }}>Week by week</h3>
          <div className="weekly" data-testid="weekly">
            {profile.improvement.weekly.map((week) => {
              const top = Math.max(1, ...profile.improvement.weekly.map((w) => w.solved));
              return (
                <div key={week.week_start} className="weekly-col" title={`Week of ${week.week_start}: ${week.solved} solved, ${week.submissions} submissions`}>
                  <span className="weekly-value">{week.solved}</span>
                  <span className="weekly-bar" style={{ height: `${(week.solved / top) * 70 + 2}px` }} />
                  <span className="weekly-label">{new Date(`${week.week_start}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
                </div>
              );
            })}
          </div>
          <p className="subtle">Problems solved each week, for the last eight weeks.</p>
        </div>
        {profile.improvement.knowledge_checks.available
          ? <p>Knowledge checks: normalised gain <strong>{profile.improvement.knowledge_checks.mean_normalised_gain}</strong>, from the starting and closing checks.</p>
          : <p className="subtle">Knowledge checks: not taken yet, so learning gain is not measured.{own ? <> <Link to="/check/pre">Take the starting check</Link>.</> : null}</p>}
      </section>

      <section className="card stack-s" aria-labelledby="matrix-heading">
        <div className="row" style={{ gap: 2 }}>
          <h2 id="matrix-heading">Learning state, by topic</h2>
          <HelpDialog title="What are these columns?">
            <p><strong>Mastery</strong> is the tutor's estimate of how well a topic is understood, with its likely range. It starts uncertain and narrows with evidence. <strong>Evidence</strong> is how much graded work it rests on.</p>
            <p><strong>Confidence</strong> is what the learner said about their own approach. <strong>Confusion</strong> and <strong>workload</strong> need at least two signs before they are anything but unknown. <strong>Progress</strong> is whether recent attempts moved forward.</p>
            <p>These are estimates from coding activity, never grades, and they decide how much help the tutor offers.</p>
          </HelpDialog>
        </div>
        {profile.state_matrix.length === 0 ? <p className="muted">No estimates yet. They appear after the first submission or hint.</p> : (
          <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
            <table className="table matrix" data-testid="state-matrix">
              <thead><tr>
                <th scope="col">Topic</th><th scope="col" className="num">Solved</th><th scope="col">Mastery</th><th scope="col" className="num">Started at</th><th scope="col" className="num">Evidence</th>
                <th scope="col" className="num">Alone / with help</th><th scope="col">Confidence</th><th scope="col">Confusion</th><th scope="col">Workload</th><th scope="col">Progress</th><th scope="col">Updated</th>
              </tr></thead>
              <tbody>{profile.state_matrix.map((row) => (
                <tr key={row.unit_id}>
                  <th scope="row"><Link to={`/path/${row.unit_id}`}>{row.title}</Link></th>
                  <td className="num">{row.solved} / {row.total}</td>
                  <td className="nowrap">{row.mastery === null ? unknown : <><strong>{percent(row.mastery)}</strong> <span className="subtle">({percent(row.mastery_low)}–{percent(row.mastery_high)})</span><br /><span className="subtle">{row.band}</span></>}</td>
                  <td className="num">{percent(row.starting_mastery)}</td>
                  <td className="num">{row.evidence_weight} <span className="subtle">({row.graded_attempts} graded)</span></td>
                  <td className="num">{row.independent_solved} / {row.assisted_solved}</td>
                  <td>{row.confidence === null ? unknown : percent(row.confidence)}</td>
                  <td>{row.confusion ? LEVEL_WORDS[row.confusion] ?? row.confusion : unknown}</td>
                  <td>{row.load ? LEVEL_WORDS[row.load] ?? row.load : unknown}</td>
                  <td>{row.progress ? PROGRESS_WORDS[row.progress] ?? row.progress : unknown}</td>
                  <td className="nowrap subtle">{row.updated_at ? timeAgo(row.updated_at) : "–"}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card stack-s" aria-labelledby="vector-heading">
        <div className="row" style={{ gap: 2 }}>
          <h2 id="vector-heading">How the tutor matches similar situations</h2>
          <HelpDialog title="What is this?">
            <p>Before choosing help, the tutor describes the current situation as numbers from −1 to 1, and looks for similar past situations to see which kind of help led to progress.</p>
            <p>It compares situations, not people. No other learner's name, code or answers are ever shown or used to identify anyone. Demonstration records are labelled, and a match only adjusts the choice within the tutor's limits.</p>
          </HelpDialog>
        </div>
        {profile.vector ? (
          <>
            <p className="subtle">From the latest work on {profile.vector.problem ?? "a problem"}, {timeAgo(profile.vector.at)}. Version {profile.vector.version}.</p>
            <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
              <table className="table" data-testid="vector-table">
                <thead><tr><th scope="col">Feature</th><th scope="col">Value</th><th scope="col" className="num">As used, −1 to 1</th><th scope="col">Meaning</th></tr></thead>
                <tbody>{profile.vector.features.map((f) => (
                  <tr key={f.name}><th scope="row">{f.name}</th><td>{f.raw ?? <span className="subtle">–</span>}</td>
                    <td className="num"><span className="vector-bar" aria-hidden><span style={{ left: f.value >= 0 ? "50%" : `${50 + f.value * 50}%`, width: `${Math.abs(f.value) * 50}%` }} /></span> {f.value.toFixed(2)}</td>
                    <td className="subtle">{f.meaning}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </>
        ) : <p className="muted" data-testid="vector-empty">This appears after the next hint or submission.</p>}
        {profile.similar && (
          <p data-testid="similar-summary">
            {profile.similar.matched
              ? <>Last match: <strong>{profile.similar.support}</strong> similar situations{profile.similar.demo_data ? " from demonstration records" : ""}, where the suggested kind of help led to progress in <strong>{percent(profile.similar.effectiveness)}</strong> of cases.</>
              : <>Last match: no reliable match. {profile.similar.reason}</>}
          </p>
        )}
      </section>

      <section className="card stack-s" aria-labelledby="recent-heading">
        <h2 id="recent-heading" className="row" style={{ gap: 8 }}><Flame size={18} aria-hidden /> Recent submissions</h2>
        {profile.recent.length === 0 ? <p className="muted">No submissions yet.</p> : (
          <div className="table-wrap" tabIndex={0} role="group" aria-label="Scrollable table">
            <table className="table"><thead><tr><th scope="col">Problem</th><th scope="col">Result</th><th scope="col" className="num">Tests</th><th scope="col">When</th></tr></thead>
              <tbody>{profile.recent.map((row, i) => (
                <tr key={i}><td>{own ? <Link to={`/problems/${row.problem_id}`}>{row.title}</Link> : row.title}</td><td>{VERDICT_LABEL[row.verdict ?? ""] ?? row.verdict}</td><td className="num">{row.total ? `${row.passed}/${row.total}` : "–"}</td><td className="nowrap">{timeAgo(row.at)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
