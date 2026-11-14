"""Writes the pgfplots coordinates used by the report, computed from the project's own data and code.

Run from the repository root with the backend environment:
    backend/.venv/bin/python report/tools/make_figure_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.tutoring import dsda  # noqa: E402
from app.tutoring.cognitive import POLICY, bkt_update, mastery_estimate  # noqa: E402

OUT = ROOT / "report" / "figures" / "data"
OUT.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "report" / "data"


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text)
    print("wrote", name)


# 1. Mastery trajectories from the implemented BKT update and evidence weights.
weights = POLICY["evidence_weights"]
sequences = {
    "fluent": [("solve", weights["solved_independently"])] * 5,
    "recovering": [("fail", weights["logic_failure"]), ("fail", weights["logic_failure"]),
                   ("solve", weights["solved_with_hints_by_level"][2]), ("solve", weights["solved_independently"]),
                   ("solve", weights["solved_independently"])],
    "struggling": [("fail", weights["logic_failure"])] * 5,
}
lines = []
summary = {}
for name, seq in sequences.items():
    value, evidence = POLICY["bkt_prior"], 0.0
    points = [(0, value, value, value)]
    for step, (kind, weight) in enumerate(seq, start=1):
        value = bkt_update(value, kind == "solve", weight)
        evidence += weight
        est = mastery_estimate(value, evidence, True, "")
        points.append((step, est.value, est.low, est.high))
    summary[name] = points
    lines.append(f"% {name}: step, value, low, high")
    lines.append(f"\\def\\bkt{name}{{" + " ".join(f"({s},{v:.3f})" for s, v, _, _ in points) + "}")
    lines.append(f"\\def\\bkt{name}low{{" + " ".join(f"({s},{lo:.3f})" for s, _, lo, _ in points) + "}")
    lines.append(f"\\def\\bkt{name}high{{" + " ".join(f"({s},{hi:.3f})" for s, _, _, hi in points) + "}")
write("bkt.tex", "\n".join(lines) + "\n")
json.dump(summary, open(DATA / "bkt.json", "w"), indent=1)

# 2. The documented DSDA worked example, recomputed with the implemented score.
example = dsda.DSDAInput(trigger="submit", request_size=None, category="wrong_answer", issue_key="logic:off_by_one", repeat_count=2,
                         mastery=0.25, mastery_evidence=2.0, confidence=None, confusion="moderate", load=None, progress="stalled",
                         attempts_on_problem=2, last_level_on_issue=1, hints_on_issue=1, hints_without_progress_on_issue=1)
score, components = dsda.need_score(example, dsda.POLICY)
decision = dsda.decide(example)
json.dump({"score": score, "components": components, "level": decision.selected_level, "strategy": decision.strategy,
           "action": decision.action, "reason_codes": decision.reason_codes}, open(DATA / "dsda_example.json", "w"), indent=1)
print("dsda example", score, components, decision.selected_level, decision.strategy, decision.action, decision.reason_codes)

# 3. Curriculum by topic and difficulty.
cur = json.load(open(DATA / "curriculum.json"))
short = {"python-basics": "Basics", "variables-io": "Variables/IO", "conditionals": "Conditionals", "loops": "Loops", "functions": "Functions",
         "strings": "Strings", "lists-dicts": "Lists/dicts", "recursion": "Recursion", "searching-sorting": "Search/sort",
         "arrays-two-pointers": "Arrays", "hashing": "Hashing", "stacks-queues": "Stacks/queues", "linked-lists": "Linked lists",
         "trees": "Trees", "graphs": "Graphs", "dynamic-programming": "DP", "python-toolkit": "Toolkit"}
labels = ",".join("{" + short[u["id"]] + "}" for u in cur["units"])
out = [f"\\def\\topiclabels{{{labels}}}"]
for level in ("easy", "medium", "hard"):
    out.append(f"\\def\\topic{level}{{" + " ".join(f"({i},{u[level]})" for i, u in enumerate(cur["units"])) + "}")
write("curriculum.tex", "\n".join(out) + "\n")

cats = sorted(cur["hidden_categories"].items(), key=lambda kv: kv[1])
write("categories.tex", "\\def\\catlabels{" + ",".join("{" + k + "}" for k, _ in cats) + "}\n\\def\\catcoords{" +
      " ".join(f"({v},{i})" for i, (k, v) in enumerate(cats)) + "}\n")

# 4. Audit checks per scenario.
audit = json.load(open(DATA / "audit.json"))
names = ["Repeated requests on unchanged code", "Repeated syntax error", "Runtime error and endless loop", "Progress, new issue, solve",
         "Return inside a loop", "High mastery, overload, no history", "Help offered, not pushed", "Reflection question and reply",
         "Planner route and agreement", "Checks over every hint shown"]
rows = list(reversed(list(enumerate(audit))))
write("audit.tex", "\\def\\auditlabels{" + ",".join("{" + names[i] + "}" for i, _ in rows) + "}\n\\def\\auditcoords{" +
      " ".join(f"({row['pass']},{k})" for k, (i, row) in enumerate(rows)) + "}\n")
print("audit total", sum(r["pass"] for r in audit), "failed", sum(r["fail"] for r in audit))
