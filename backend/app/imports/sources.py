"""External problem sources. A source is added only when it has a permitted, reliable route.

Codeforces offers an official public API. It provides titles, tags and ratings, but not statements, so
those are imported and the learner pastes the statement. Sites without a public API are not scraped:
the learner is told why, and guided to the paste method.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from ..schemas import ImportDraft, LookupOut
from .parser import TAG_TO_UNIT

log = logging.getLogger("csmasf.imports")

CODEFORCES_API = "https://codeforces.com/api/problemset.problems"
CF_URL = re.compile(r"codeforces\.com/(?:contest|problemset/problem|gym)/(\d+)(?:/problem)?/([A-Za-z]\d?)", re.I)
CF_ID = re.compile(r"^(?:cf\s*)?(\d{1,5})\s*[-/ ]?\s*([A-Za-z]\d?)$", re.I)
UNSUPPORTED = {
    "leetcode.com": "LeetCode",
    "hackerrank.com": "HackerRank",
    "geeksforgeeks.org": "GeeksforGeeks",
    "codechef.com": "CodeChef",
    "atcoder.jp": "AtCoder",
    "hackerearth.com": "HackerEarth",
    "interviewbit.com": "InterviewBit",
    "codewars.com": "Codewars",
}
PASTE_GUIDANCE = "Open the problem in your browser, copy the description, examples and constraints, and use Paste details instead."

_cache: dict[str, Any] = {"at": 0.0, "problems": None}
_lock = threading.Lock()
CACHE_SECONDS = 3600
transport: httpx.BaseTransport | None = None  # replaced in tests


def _rating_to_difficulty(rating: int | None) -> str | None:
    if rating is None:
        return None
    return "easy" if rating < 1300 else ("medium" if rating < 1900 else "hard")


def _fetch_codeforces() -> list[dict[str, Any]]:
    with _lock:
        if _cache["problems"] is not None and time.monotonic() - _cache["at"] < CACHE_SECONDS:
            return _cache["problems"]
        with httpx.Client(timeout=20, transport=transport, headers={"User-Agent": "CSMASF-tutor/1.0 (educational project)"}) as client:
            response = client.get(CODEFORCES_API)
            response.raise_for_status()
            body = response.json()
        if body.get("status") != "OK":
            raise ValueError("Codeforces reported an error")
        _cache["problems"], _cache["at"] = body["result"]["problems"], time.monotonic()
        return _cache["problems"]


def clear_cache() -> None:
    with _lock:
        _cache["problems"], _cache["at"] = None, 0.0


def lookup(query: str) -> LookupOut:
    query = query.strip()
    host = ""
    if "://" in query or query.startswith("www.") or "." in query.split("/")[0]:
        parsed = urlparse(query if "://" in query else f"https://{query}")
        host = (parsed.hostname or "").lower().removeprefix("www.")
    for domain, name in UNSUPPORTED.items():
        if host == domain or host.endswith("." + domain):
            return LookupOut(
                supported=False, source_name=name,
                message=f"{name} does not offer a public API for problem statements here, and this app does not scrape websites.",
                guidance=PASTE_GUIDANCE,
            )
    if host and host != "codeforces.com" and not host.endswith(".codeforces.com"):
        return LookupOut(supported=False, source_name=host, message=f"{host} is not a supported source.", guidance=PASTE_GUIDANCE)

    match = CF_URL.search(query) or CF_ID.match(query)
    if not match:
        return LookupOut(supported=False, source_name=None, message="That does not look like a supported link or problem ID. Codeforces links and IDs such as 1872A are supported.", guidance=PASTE_GUIDANCE)
    contest, index = int(match.group(1)), match.group(2).upper()
    try:
        problems = _fetch_codeforces()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("codeforces lookup failed: %s", type(exc).__name__)
        return LookupOut(supported=True, source_name="Codeforces", message="Codeforces could not be reached just now. Try again, or use Paste details.", guidance=PASTE_GUIDANCE)
    found = next((p for p in problems if p.get("contestId") == contest and str(p.get("index", "")).upper() == index), None)
    if not found:
        return LookupOut(supported=True, source_name="Codeforces", message=f"Problem {contest}{index} was not found in the Codeforces problem set.", guidance=PASTE_GUIDANCE)
    tags = list(found.get("tags") or [])
    unit = next((TAG_TO_UNIT[t] for t in tags if t in TAG_TO_UNIT), None)
    url = f"https://codeforces.com/problemset/problem/{contest}/{index}"
    draft = ImportDraft(
        title=found.get("name", ""), description="", difficulty=_rating_to_difficulty(found.get("rating")), tags=tags, unit_id=unit, mode="stdio",
        source_name="Codeforces", source_url=url, source_retrieved_at=datetime.now(UTC),
        missing_fields=["description", "constraints", "examples"],
        warnings=["Codeforces' API gives the title, tags and rating, but not the statement. Please paste the description and examples from the problem page."],
    )
    return LookupOut(
        supported=True, source_name="Codeforces", draft=draft,
        message="Found it. Codeforces' public API provides the title, tags and rating. The statement is not available through it, so please paste that in the next step.",
    )
