#!/usr/bin/env python3
"""Drive real tutoring scenarios through a running API and check what every agent produced.

Each scenario uses a fresh learner. For every submission or hint request it records the diagnostic, the learner-state
estimates, the retrieval result, the DSDA decision, the hint and its validation, the reflection decision and the plan,
all read back from the run and its agent trace. Then it checks those outputs against the rules in docs/agent-audit.md.

Run against a development stack (the trace endpoint is off in production):
    backend/.venv/bin/python scripts/agent_audit.py http://127.0.0.1:8101 > docs/agent-audit-run.md
"""
from __future__ import annotations

import datetime as dt
import itertools
import re
import sys
import time
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8101"

# Advice the brief names as unacceptable, and close relatives. A hint may not lean on any of these.
GENERIC = re.compile(r"\b(try debugging|debug your code|check your (code|logic|work)|read the (problem|question|task) again|use a loop|think (carefully|harder)|"
                     r"be careful|try again|keep trying|look at your code|review your (code|logic)|fix your code|something is wrong)\b", re.IGNORECASE)

SUM_RIGHT = "def sum_to_n(n):\n    return n * (n + 1) // 2\n"
OFF_BY_ONE = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
EARLY_RETURN = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n        return total\n"
MISSING_COLON = "def sum_to_n(n)\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
NAME_ERROR = "def sum_to_n(n):\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
ENDLESS = "def sum_to_n(n):\n    total = 0\n    i = 1\n    while i <= n:\n        total += i\n    return total\n"
NO_RETURN = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n"


class Learner:
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=BASE, timeout=90)
        email = f"audit-{uuid.uuid4().hex[:10]}@example.com"
        response = self.client.post("/api/auth/register", json={"name": "Audit learner", "email": email, "password": "correct horse battery", "role": "student"})
        response.raise_for_status()

    def _wait(self, run_id: str) -> dict[str, Any]:
        for _ in range(600):
            body = self.client.get(f"/api/runs/{run_id}").json()
            if body["status"] in ("completed", "failed"):
                trace = self.client.get(f"/api/runs/{run_id}/trace")
                body["trace"] = trace.json() if trace.status_code == 200 else None
                return body
            time.sleep(0.2)
        raise TimeoutError(run_id)

    def submit(self, problem: str, code: str, **extra: Any) -> dict[str, Any]:
        run = self.client.post(f"/api/problems/{problem}/submit", json={"code": code, "idempotency_key": uuid.uuid4().hex, **extra})
        run.raise_for_status()
        return self._wait(run.json()["id"])

    def hint(self, problem: str, code: str, **extra: Any) -> dict[str, Any]:
        run = self.client.post(f"/api/problems/{problem}/hint", json={"code": code, "idempotency_key": uuid.uuid4().hex, **extra})
        run.raise_for_status()
        return self._wait(run.json()["id"])


def stage(run: dict[str, Any], name: str) -> dict[str, Any]:
    for step in (run.get("trace") or {}).get("steps", []):
        if step["stage"] == name:
            return step
    return {}


def cycle(action: str, run: dict[str, Any], code: str) -> dict[str, Any]:
    response = run.get("response") or {}
    tutor = response.get("tutor") or {}
    diag = response.get("diagnostics") or {}
    dsda = stage(run, "dsda").get("output") or {}
    retrieval = stage(run, "retrieval").get("output") or {}
    cognitive = stage(run, "cognitive_state").get("output") or {}
    validate = stage(run, "validate_hint")
    reflection = response.get("reflection") or {}
    plan = response.get("plan") or {}
    return {
        "action": action, "code": code, "verdict": response.get("verdict"), "issue": diag.get("issue_key"), "category": diag.get("category"),
        # The learner's first view may hold the cause back, so the trace (development only) is the source of truth here.
        "cause": (stage(run, "diagnostic").get("output") or {}).get("cause") or (diag.get("diagnosis") or {}).get("likely_cause"),
        "concept": (stage(run, "diagnostic").get("output") or {}).get("concept") or (diag.get("diagnosis") or {}).get("concept"),
        "confidence": (stage(run, "diagnostic").get("output") or {}).get("cause_confidence") or (diag.get("diagnosis") or {}).get("confidence"), "same_issue": (diag.get("comparison") or {}).get("same_issue"),
        "moved_further": (diag.get("comparison") or {}).get("moved_further"), "facts": [f.get("text") for f in diag.get("facts") or []],
        "mastery": cognitive.get("mastery"), "band": cognitive.get("band"), "confusion": cognitive.get("confusion"), "load": cognitive.get("load"), "progress": cognitive.get("progress"),
        "retrieval_reliable": retrieval.get("reliable"), "retrieval_reason": retrieval.get("reason"), "retrieval_candidates": retrieval.get("candidates"), "retrieval_excluded": retrieval.get("excluded"),
        "level": dsda.get("selected_level"), "strategy": dsda.get("strategy"), "reasons": dsda.get("reason_codes"), "dsda_action": dsda.get("action"), "timing": dsda.get("timing"),
        "hint": tutor.get("text"), "hint_source": tutor.get("source"), "why": tutor.get("why"), "level_name": tutor.get("level_name"),
        "validation": {"status": validate.get("status"), "reason": validate.get("reason"), "output": validate.get("output")},
        "waiting": response.get("waiting"), "reflection": reflection.get("prompt") if reflection else None, "reflection_action": (stage(run, "reflection").get("output") or {}).get("action"),
        "plan_action": plan.get("action"), "plan_title": plan.get("title"), "plan_reason": plan.get("reason"),
    }


def similar(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    left, right = re.findall(r"[a-z0-9_]+", a.lower()), re.findall(r"[a-z0-9_]+", b.lower())
    return max(SequenceMatcher(None, left, right).ratio(), len(set(left) & set(right)) / max(1, len(set(left) | set(right))))


def specific(hint: str, code: str) -> bool:
    """Names something concrete: quoted code, a line, a value, or a name from the learner's own code."""
    if re.search(r"`[^`]+`|\bline \d+\b|\d", hint):
        return True
    names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code)) - {"def", "return", "for", "in", "if", "else", "while", "range", "print", "True", "False", "None"}
    return any(re.search(rf"\b{re.escape(n)}\b", hint) for n in names if len(n) > 1)


# ---------------------------------------------------------------- scenarios

def scenario_repeated_hints() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle("submit wrong code", me.submit("sum-to-n", OFF_BY_ONE), OFF_BY_ONE)]
    rows.append(cycle("ask for a hint, code unchanged", me.hint("sum-to-n", OFF_BY_ONE), OFF_BY_ONE))
    rows.append(cycle("ask again, code unchanged", me.hint("sum-to-n", OFF_BY_ONE), OFF_BY_ONE))
    rows.append(cycle("ask for more help, code unchanged", me.hint("sum-to-n", OFF_BY_ONE, request_size="more"), OFF_BY_ONE))
    hints = [r["hint"] for r in rows if r["hint"]]
    pairs = [similar(a, b) for i, a in enumerate(hints) for b in hints[i + 1:]]
    levels = [r["level"] for r in rows if r["level"] is not None]
    checks = [
        ("Every request on unchanged code got a different hint", len(hints) == len(set(hints)) and len(hints) >= 3, f"{len(hints)} hints, highest similarity {max(pairs or [0]):.2f}"),
        ("No two hints are near-copies (similarity below 0.8)", all(p < 0.8 for p in pairs), f"similarities {[round(p, 2) for p in pairs]}"),
        ("DSDA escalates one level at a time, never down while stuck", all(0 <= b - a <= 1 for a, b in itertools.pairwise(levels)), f"levels {levels}"),
        ("DSDA records hints already seen on this code", any("SAME_CODE" in " ".join(r["reasons"] or []) or "REPEAT" in " ".join(r["reasons"] or []) for r in rows[2:]), f"reasons {[r['reasons'] for r in rows]}"),
        ("Strategy changes between requests", len({r["strategy"] for r in rows if r["strategy"]}) >= 3, f"strategies {[r['strategy'] for r in rows]}"),
        ("Retrieval leaves out approaches already shown", any(r["retrieval_excluded"] for r in rows[1:]), f"excluded {[r['retrieval_excluded'] for r in rows]}"),
        ("Diagnosis stays on the same issue while the code is unchanged", len({r["issue"] for r in rows}) == 1, f"issues {[r['issue'] for r in rows]}"),
    ]
    return rows, checks


def scenario_syntax() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle("submit a missing colon", me.submit("sum-to-n", MISSING_COLON), MISSING_COLON)]
    rows.append(cycle("ask for a hint", me.hint("sum-to-n", MISSING_COLON), MISSING_COLON))
    rows.append(cycle("submit the same mistake again", me.submit("sum-to-n", MISSING_COLON + "\n"), MISSING_COLON + "\n"))
    first = rows[0]
    checks = [
        ("Syntax error is diagnosed as syntax, with a line", first["category"] == "syntax" and any("line 1" in (f or "").lower() for f in first["facts"] + [first["hint"] or ""]), f"category {first['category']}, facts {first['facts']}"),
        ("The first syntax hint is precise enough to act on", specific(first["hint"] or "", MISSING_COLON), first["hint"] or ""),
        ("A repeated syntax mistake is offered more help, not pushed", rows[2]["hint"] is None and rows[2]["dsda_action"] == "offer_help", f"{rows[2]['dsda_action']} ({', '.join(rows[2]['reasons'] or [])})"),
    ]
    return rows, checks


def scenario_runtime_and_timeout() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle("submit code using a name before it is set", me.submit("sum-to-n", NAME_ERROR), NAME_ERROR)]
    other = Learner()
    rows.append(cycle("submit a loop that never ends", other.submit("sum-to-n", ENDLESS), ENDLESS))
    runtime, endless = rows
    checks = [
        ("Runtime error names the exception, the line and the variable", runtime["category"] == "runtime" and "total" in (runtime["hint"] or "") + " ".join(runtime["facts"]), f"{runtime['issue']}: {runtime['hint']}"),
        ("The runtime cause is told apart from a generic NameError", runtime["cause"] == "used_before_assignment", f"cause {runtime['cause']}, concept {runtime['concept']}, confidence {runtime['confidence']}"),
        ("A loop that never ends is diagnosed as a timeout and the hint is about the loop", endless["category"] == "timeout" and re.search(r"loop|while|i\b", endless["hint"] or "") is not None, f"{endless['issue']}: {endless['hint']}"),
    ]
    return rows, checks


def scenario_progress_and_new_issue() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle("submit code with no return", me.submit("sum-to-n", NO_RETURN), NO_RETURN)]
    rows.append(cycle("ask for a hint", me.hint("sum-to-n", NO_RETURN), NO_RETURN))
    rows.append(cycle("fix it, but now off by one", me.submit("sum-to-n", OFF_BY_ONE), OFF_BY_ONE))
    rows.append(cycle("fix it completely", me.submit("sum-to-n", SUM_RIGHT), SUM_RIGHT))
    checks = [
        ("A new issue after a hint is diagnosed afresh", rows[2]["issue"] != rows[0]["issue"] and rows[2]["same_issue"] is False, f"{rows[0]['issue']} then {rows[2]['issue']}"),
        ("The new issue starts at a low level again", (rows[2]["level"] or 0) <= (rows[1]["level"] or 0), f"levels {rows[1]['level']} then {rows[2]['level']}"),
        ("Moving from no answer to a close answer counts as progress", rows[2]["progress"] in ("improving", "steady") or rows[2]["moved_further"], f"progress {rows[2]['progress']}, moved further {rows[2]['moved_further']}"),
        ("A correct submission gets no hint", rows[3]["verdict"] == "accepted" and not rows[3]["hint"] or "No hint needed" in (rows[3]["hint"] or ""), rows[3]["hint"] or "(none)"),
        ("One solve does not jump to a harder problem or topic", rows[3]["plan_action"] != "harder_next", f"{rows[3]['plan_action']}: {rows[3]['plan_reason']}"),
    ]
    return rows, checks


def scenario_early_return() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle("submit a return inside the loop", me.submit("sum-to-n", EARLY_RETURN), EARLY_RETURN)]
    rows.append(cycle("ask for a hint", me.hint("sum-to-n", EARLY_RETURN), EARLY_RETURN))
    checks = [
        ("The early return is diagnosed by name", rows[0]["issue"] == "logic:early_return_in_loop", rows[0]["issue"] or ""),
        ("Hints talk about the return and the loop", all(re.search(r"return", r["hint"] or "") and re.search(r"loop|iteration|pass", r["hint"] or "") for r in rows), " | ".join(r["hint"] or "" for r in rows)),
    ]
    return rows, checks


def scenario_states() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    solutions = yaml.safe_load((ROOT / "content/solutions/bank.yaml").read_text())
    strong = Learner()
    for slug in ("product-of-a-list", "sum-of-squares", "count-even-digits", "below-the-average"):
        strong.submit(slug, solutions[slug])
    rows = [cycle("high-mastery learner submits wrong code", strong.submit("sum-to-n", OFF_BY_ONE), OFF_BY_ONE)]
    rows.append(cycle("and asks only for a nudge", strong.hint("sum-to-n", OFF_BY_ONE, request_size="nudge"), OFF_BY_ONE))
    tired = Learner()
    rows.append(cycle("overloaded learner submits wrong code", tired.submit("sum-to-n", OFF_BY_ONE, self_state="overwhelmed", active_seconds=1500), OFF_BY_ONE))
    fresh = Learner()
    rows.append(cycle("hint with no history at all", fresh.hint("sum-to-n", "def sum_to_n(n):\n    pass\n"), "def sum_to_n(n):\n    pass\n"))
    checks = [
        ("A nudge request from a strong learner is honoured with light help", (rows[1]["level"] or 9) <= 2, f"level {rows[1]['level']} ({rows[1]['strategy']})"),
        ("An overloaded learner gets one short action and no reflection question", rows[2]["reflection_action"] in (None, "defer", "skip") and len((rows[2]["hint"] or "").split()) <= 45, f"reflection {rows[2]['reflection_action']}, {len((rows[2]['hint'] or '').split())} words"),
        ("Unknown confidence stays unknown", rows[3]["mastery"] is not None and rows[3].get("confusion") in (None, "low"), f"confusion {rows[3]['confusion']}"),
        ("No history still produces a decision", rows[3]["level"] is not None and bool(rows[3]["hint"]), f"level {rows[3]['level']}: {rows[3]['hint']}"),
        ("No reliable match is reported as such", all((r["retrieval_reliable"] is True) or bool(r["retrieval_reason"]) for r in rows if r["action"] != "high-mastery learner submits wrong code" or r["retrieval_reason"]), " | ".join(str(r["retrieval_reason"]) for r in rows)),
    ]
    return rows, checks


def scenario_no_cascade() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    rows = [cycle(f"submit wrong code ({n})", me.submit("sum-to-n", OFF_BY_ONE + f"# try {n}\n"), OFF_BY_ONE) for n in range(1, 4)]
    rows.append(cycle("then ask for a hint", me.hint("sum-to-n", OFF_BY_ONE + "# try 3\n"), OFF_BY_ONE))
    checks = [
        ("The first failed submission gets a hint without asking", bool(rows[0]["hint"]), rows[0]["hint"] or ""),
        ("Later failed submissions only offer help; nothing climbs the ladder unasked", all(r["hint"] is None and r["dsda_action"] == "offer_help" for r in rows[1:3]), f"{[r['dsda_action'] for r in rows[1:3]]}"),
        ("Asking then gets the next step, one level at most above the last", bool(rows[3]["hint"]) and (rows[3]["level"] or 0) <= (rows[0]["level"] or 0) + 1, f"level {rows[0]['level']} then {rows[3]['level']}"),
    ]
    return rows, checks


def scenario_reflection() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    rows, replies = [], []
    cases = (("solve on the first try", False, "not sure, I just changed it until it passed"),
             ("solve with help", True, "not sure, I just changed it until it passed"),
             ("solve with help", True, "range(1, n) stopped before n, so I added one to include the last value in total"))
    for label, helped, answer in cases:
        me = Learner()
        if helped:
            me.submit("sum-to-n", OFF_BY_ONE)
            me.hint("sum-to-n", OFF_BY_ONE)
        run = me.submit("sum-to-n", SUM_RIGHT)
        rows.append(cycle(label, run, SUM_RIGHT))
        response = run.get("response") or {}
        question = response.get("reflection") or {}
        reply = me.client.post(f"/api/reflections/{question.get('id')}/answer", json={"answer": answer}).json() if question else {}
        replies.append((question.get("prompt"), answer, reply, response.get("plan") or {}))
    moving_on, consolidating, clear = replies
    checks = [
        ("After a solve with help, the reflection question names the technique", bool(consolidating[0]) and "running totals" in consolidating[0].lower(), consolidating[0] or "(no question)"),
        ("An unsure answer gets a kind reply with one small thing to try", moving_on[2].get("quality") == "unsure" and bool(moving_on[2].get("feedback")), moving_on[2].get("feedback", "")),
        ("An unsure answer holds back a plan that was moving on: one more problem of the same technique", bool(moving_on[2].get("next")) and (moving_on[2]["next"] or {}).get("reason_codes") == ["REFLECTION_UNSURE"]
         and (moving_on[2]["next"] or {}).get("problem_id") != moving_on[3].get("problem_id"), f"{moving_on[3].get('title')} became {(moving_on[2].get('next') or {}).get('title')}"),
        ("An unsure answer does not repeat a plan that already gives one more problem", consolidating[2].get("quality") == "unsure" and consolidating[2].get("next") is None, str(consolidating[3].get("title"))),
        ("A clear answer is confirmed and the plan stands", clear[2].get("quality") == "specific" and clear[2].get("next") is None, clear[2].get("feedback", "")),
        ("Replies never grade and never contain code", all("```" not in r[2].get("feedback", "") and "%" not in r[2].get("feedback", "") for r in replies), ""),
    ]
    for prompt, answer, reply, plan in replies:
        print(f"  - Question: {prompt}\n    Answer: {answer}\n    Reply ({reply.get('quality')}): {reply.get('feedback')}\n    Plan shown: {plan.get('title')}; after the answer: {(reply.get('next') or {}).get('title')}", file=sys.stderr)
    return rows, checks


def scenario_planner() -> tuple[list[dict], list[tuple[str, bool, str]]]:
    me = Learner()
    run = me.submit("sum-to-n", SUM_RIGHT)
    row = cycle("solve on the first try, no hints", run, SUM_RIGHT)
    plan = (run.get("response") or {}).get("plan") or {}
    nxt = me.client.get(f"/api/problems/{plan.get('problem_id')}").json() if plan.get("problem_id") else {}
    home = me.client.get("/api/home").json().get("recommendation", {})
    checks = [
        ("A fluent first solve moves to the next technique in the same topic, at the same level", plan.get("action") == "similar_independent" and nxt.get("unit_id") == "loops" and nxt.get("pattern") != "Running totals" and nxt.get("difficulty") == "easy",
         f"{plan.get('title')} ({nxt.get('pattern')}, {nxt.get('difficulty')}): {plan.get('reason')}"),
        ("The plan shows a route from the current topic onward", len(plan.get("route") or []) >= 2 and (plan.get("route") or [{}])[0].get("unit_id") == "loops", " -> ".join(step["title"] for step in plan.get("route") or [])),
        ("Home keeps the learner in their topic and suggests the same next step as the plan", home.get("unit_id") == "loops" and home.get("problem_id") == plan.get("problem_id"),
         f"{home.get('title')}: {home.get('reason')}"),
    ]
    return [row], checks


SCENARIOS = [
    ("Repeated hint requests on unchanged wrong code (the critical regression)", scenario_repeated_hints),
    ("Syntax error, then the same mistake again", scenario_syntax),
    ("Runtime exception and a loop that never ends", scenario_runtime_and_timeout),
    ("Progress after a hint, a new issue, then a solve", scenario_progress_and_new_issue),
    ("Return inside a loop", scenario_early_return),
    ("High mastery, overload, and no history", scenario_states),
    ("Wrong submissions without asking: help is offered, not pushed", scenario_no_cascade),
    ("Reflection: the question, the reply, and what happens next", scenario_reflection),
    ("Learning Planner: from where the learner is, onward", scenario_planner),
]


def main() -> int:
    print(f"# Agent audit run\n\nGenerated by `scripts/agent_audit.py` against {BASE} on {dt.datetime.now().strftime('%d %B %Y, %H:%M')}. "
          "Every row comes from a real run of the six agents, read back from the run response and its agent trace. No model was configured, so hint wording is the built-in, evidence-based text.\n")
    failures = 0
    all_hints: list[tuple[str, str]] = []
    for title, scenario in SCENARIOS:
        rows, checks = scenario()
        print(f"## {title}\n")
        print("| Step | Verdict | Diagnosis | Estimates | Retrieval | DSDA | Hint shown |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            estimates = f"mastery {r['mastery']}, confusion {r['confusion'] or 'unknown'}, load {r['load'] or 'unknown'}, progress {r['progress']}"
            retrieval = "reliable match" if r["retrieval_reliable"] else f"no reliable match ({r['retrieval_candidates']} candidates)"
            decision = f"L{r['level']} {r['strategy']} ({', '.join(r['reasons'] or [])})" if r["level"] is not None else (r["dsda_action"] or "none")
            hint = (r["hint"] or f"(not shown: {r['timing'] or r['dsda_action']}; the learner can ask)").replace("|", "\\|").replace("\n", " ")
            print(f"| {r['action']} | {r['verdict']} | {r['issue']}: {r['cause'] or ''} | {estimates} | {retrieval} | {decision} | {hint} |")
            if r["hint"]:
                all_hints.append((r["hint"], r["code"]))
        print()
        for name, ok, detail in checks:
            failures += 0 if ok else 1
            print(f"- {'PASS' if ok else 'FAIL'}: {name}. {detail}")
        print()
    generic = [h for h, _ in all_hints if GENERIC.search(h)]
    vague = [h for h, code in all_hints if not specific(h, code)]
    print("## Across every hint shown\n")
    print(f"- {'PASS' if not generic else 'FAIL'}: No hint uses generic advice such as \"check your logic\" or \"use a loop\". {len(all_hints)} hints checked{': ' + ' | '.join(generic) if generic else ''}.")
    print(f"- {'PASS' if not vague else 'FAIL'}: Every hint names something concrete from the learner's code, a line or a value{': ' + ' | '.join(vague) if vague else ''}.")
    failures += bool(generic) + bool(vague)
    print(f"\n{failures} check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
