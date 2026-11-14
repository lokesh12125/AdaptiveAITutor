"""Link import: best effort for any public page, with paste always available.

Each request follows the most respectful route that works:
1. A site whose terms restrict automated access is never opened. The link is kept as the source, the
   title is read from the link itself, and the learner pastes the statement.
2. A site with an official API uses it. Codeforces provides titles, tags and ratings, but not statements.
3. Any other public page is fetched once, if its robots.txt allows, and its readable text is parsed.
   Whatever goes wrong, the link is kept so the learner can still paste the question with attribution.

Nothing is presented as complete or official. The learner sees what was found and what is missing, and
reviews it all before saving. Terms were read on 9 November 2026 and can change, see docs/data-imports.md.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from ..config import settings
from ..schemas import ImportDraft, LookupOut
from . import extract, fetcher, parser
from .fetcher import FetchRefused
from .parser import TAG_TO_UNIT

log = logging.getLogger("csmasf.imports")


@dataclass(frozen=True)
class Source:
    name: str
    domains: tuple[str, ...]
    route: str  # official_api | public_page | url_only
    restriction: str | None = None
    selector: str | None = None


SOURCES = (
    Source("LeetCode", ("leetcode.com", "leetcode.cn"), "url_only", "LeetCode's terms of service forbid crawling and scraping."),
    Source("HackerRank", ("hackerrank.com",), "url_only", "HackerRank's terms of service do not allow copying parts of its service."),
    Source("GeeksforGeeks", ("geeksforgeeks.org",), "url_only", "GeeksforGeeks' terms do not allow automated access or data extraction."),
    Source("CodeChef", ("codechef.com",), "url_only", "CodeChef's terms do not allow crawling or scraping, and its robots.txt excludes problem pages."),
    Source("Take U Forward", ("takeuforward.org",), "url_only", "Take U Forward's terms do not allow automated tools to access or collect its content."),
    Source("Codeforces", ("codeforces.com",), "official_api"),
    Source("AtCoder", ("atcoder.jp",), "public_page", selector="#task-statement .lang-en, #task-statement"),
)
PASTE_GUIDANCE = "Open the problem in your browser, copy the description, examples and constraints, and paste them here. Paste always works, for a problem from any site."
FIELD_LABELS = {"title": "title", "description": "description", "constraints": "constraints", "input_format": "input format", "output_format": "output format", "examples": "examples", "difficulty": "difficulty", "tags": "topic tags"}

CODEFORCES_API = "https://codeforces.com/api/problemset.problems"
CF_URL = re.compile(r"codeforces\.com/(?:contest|problemset/problem|gym)/(\d+)(?:/problem)?/([A-Za-z]\d?)", re.I)
CF_ID = re.compile(r"^(?:cf\s*)?(\d{1,5})\s*[-/ ]?\s*([A-Za-z]\d?)$", re.I)
ATCODER_ID = re.compile(r"^(?:atcoder\s+)?((?:abc|arc|agc|ahc)\d{3})[_/ -]?([a-h])$", re.I)
LEETCODE_ID = re.compile(r"^(?:leetcode|lc)[\s:-]+([a-z0-9][a-z0-9 -]*)$", re.I)

_cache: dict[str, Any] = {"at": 0.0, "problems": None}
_lock = threading.Lock()
CACHE_SECONDS = 3600
transport: httpx.BaseTransport | None = None  # replaced in tests


def source_for(host: str) -> Source | None:
    plain = host.lower().removeprefix("www.")
    return next((s for s in SOURCES if any(plain == d or plain.endswith("." + d) for d in s.domains)), None)


def source_name_for(url: str | None) -> str | None:
    """A friendly name for attribution, without contacting the site."""
    if not url:
        return None
    try:
        normalised = fetcher.normalise_url(url)
    except FetchRefused:
        return None
    host = fetcher.host_of(normalised)
    known = source_for(host)
    return known.name if known else host.removeprefix("www.")


def _rating_to_difficulty(rating: int | None) -> str | None:
    if rating is None:
        return None
    return "easy" if rating < 1300 else ("medium" if rating < 1900 else "hard")


def _fetch_codeforces() -> list[dict[str, Any]]:
    with _lock:
        if _cache["problems"] is not None and time.monotonic() - _cache["at"] < CACHE_SECONDS:
            return _cache["problems"]
        with httpx.Client(timeout=20, transport=transport, headers={"User-Agent": fetcher.USER_AGENT}) as client:
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
    fetcher.clear_caches()


def _title_from_url(url: str) -> str:
    """Read a likely title from the link's own words. Nothing is fetched."""
    segments = [s for s in urlsplit(url).path.split("/") if s]
    ignored = {"problems", "problem", "problemset", "challenges", "contests", "contest", "tasks", "practice", "description", "data-structure", "plus", "dsa", "1", "0"}
    for segment in reversed(segments):
        text = unquote(segment).lower()
        if text in ignored or text.isdigit() or len(text) < 3:
            continue
        words = re.sub(r"[-_]+", " ", text).strip()
        if re.search(r"[a-z]", words):
            return words[:1].upper() + words[1:]
    return ""


def _failed(code: str, message: str, source_name: str | None = None, url: str | None = None) -> LookupOut:
    return LookupOut(supported=False, status="failed", reason_code=code, source_name=source_name, source_url=url, access="none", message=message, guidance=PASTE_GUIDANCE)


def _keep_link(name: str, url: str, code: str, message: str, status: str = "url_only") -> LookupOut:
    """The statement could not be read, but the learner's link still gives attribution for what they paste."""
    title = _title_from_url(url)
    missing = ["description", "constraints", "examples", "difficulty"] + ([] if title else ["title"])
    draft = ImportDraft(
        title=title[:160], source_name=name, source_url=url, missing_fields=missing, extracted_fields=["title"] if title else [],
        warnings=["The title, if shown, comes from the words in your link rather than the page, so please check it."],
    )
    return LookupOut(
        supported=False, status=status, reason_code=code, source_name=name, source_url=url, access="url_only", draft=draft,
        extracted_fields=draft.extracted_fields, missing_fields=missing, message=f"{message} Your link is kept as the source.", guidance=PASTE_GUIDANCE,
    )


def _url_only(source: Source, url: str) -> LookupOut:
    return _keep_link(source.name, url, "terms_restrict", f"{source.restriction} So CodePath did not open the page and does not scrape it.")


def _codeforces(contest: int, index: str) -> LookupOut:
    url = f"https://codeforces.com/problemset/problem/{contest}/{index}"
    try:
        problems = _fetch_codeforces()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("codeforces lookup failed: %s", type(exc).__name__)
        return LookupOut(supported=True, status="failed", reason_code="unreachable", source_name="Codeforces", source_url=url, access="official_api", message="Codeforces could not be reached just now. Try again, or paste the question.", guidance=PASTE_GUIDANCE)
    found = next((p for p in problems if p.get("contestId") == contest and str(p.get("index", "")).upper() == index), None)
    if not found:
        return LookupOut(supported=True, status="failed", reason_code="not_found", source_name="Codeforces", source_url=url, access="official_api", message=f"Problem {contest}{index} was not found in the Codeforces problem set.", guidance=PASTE_GUIDANCE)
    tags = list(found.get("tags") or [])
    unit = next((TAG_TO_UNIT[t] for t in tags if t in TAG_TO_UNIT), None)
    difficulty = _rating_to_difficulty(found.get("rating"))
    missing = ["description", "constraints", "examples"] + ([] if difficulty else ["difficulty"])
    extracted = ["title", "tags"] + (["difficulty"] if difficulty else [])
    draft = ImportDraft(
        title=found.get("name", ""), description="", difficulty=difficulty, tags=tags, unit_id=unit, mode="stdio", source_name="Codeforces", source_url=url, source_retrieved_at=datetime.now(UTC),
        missing_fields=missing, extracted_fields=extracted,
        warnings=["Codeforces' API gives the title, tags and rating, but not the statement. Please paste the description and examples from the problem page."],
    )
    return LookupOut(
        supported=True, status="metadata_only", source_name="Codeforces", source_url=url, access="official_api", draft=draft, extracted_fields=extracted, missing_fields=missing,
        message="Found it. Codeforces' official API provides the title, tags and rating. The statement is not available through it, so please paste that in the next step.",
    )


def _looks_like_a_problem(draft: ImportDraft, text: str) -> bool:
    lowered = text.lower()
    words = ("input", "output", "return", "given", "example", "constraint", "write a", "find", "print", "calculate", "compute", "determine", "how many")
    signals = sum(word in lowered for word in words)
    # A short page that asks for something is probably a task. A long article needs stronger evidence.
    return bool(draft.examples) or bool(draft.constraints) or signals >= 2 or (signals == 1 and len(text) < 1500)


def _extracted_fields(draft: ImportDraft) -> list[str]:
    found = []
    for name in ("title", "description", "constraints", "input_format", "output_format", "examples", "difficulty", "tags"):
        if getattr(draft, name):
            found.append(name)
    return found


def _from_public_page(url: str, source: Source | None) -> LookupOut:
    name = source.name if source else fetcher.host_of(url).removeprefix("www.")
    if not settings.import_page_fetch:
        return _keep_link(name, url, "fetch_disabled", "Opening external pages is turned off on this server.")
    try:
        page = fetcher.fetch_page(url)
    except FetchRefused as refused:
        if refused.code in ("not_found", "invalid_url", "not_allowed_address", "too_many_redirects"):
            return _failed(refused.code, refused.message, name, url)
        temporary = refused.code in ("rate_limited", "site_rate_limited", "timeout", "unreachable")
        return _keep_link(name, url, refused.code, refused.message, "failed" if temporary else "url_only")
    try:
        if page.content_type == "text/plain":
            readable = extract.Readable(title="", text=page.text[: extract.MAX_TEXT_CHARS], tags=[])
        else:
            readable = extract.extract_readable(page.text, fetcher.host_of(page.final_url), source.selector if source else None)
    except Exception as exc:  # noqa: BLE001 - any page, however broken, must end in the paste route rather than an error
        log.warning("could not read a fetched page: %s", type(exc).__name__)
        return _keep_link(name, url, "unreadable", "The page opened, but it could not be read.")
    if readable.no_ai:
        return _keep_link(name, url, "content_signal", "This site asks that its content not be used by AI tools, so CodePath did not use the page.")
    if len(readable.text) < 120:
        return _keep_link(name, url, "no_readable_text", "The page opened, but it had almost no readable text. It may need a sign-in or a browser to display.")

    # Lead with the title, so the parser does not mistake a heading for it.
    combined = f"{readable.title}\n\n{readable.text}" if readable.title and not readable.text.startswith(readable.title) else readable.text
    try:
        draft = parser.parse_problem_text(combined)
    except Exception as exc:  # noqa: BLE001 - as above
        log.warning("could not parse a fetched page: %s", type(exc).__name__)
        return _keep_link(name, url, "unreadable", "The page opened, but its contents could not be understood.")
    draft.starter_code = parser.generate_starter(draft)
    draft.title = (readable.title or draft.title)[:160]
    draft.tags = readable.tags or draft.tags
    draft.unit_id = parser.suggest_unit(f"{draft.title} {draft.description}", draft.tags)
    draft.source_name, draft.source_url, draft.source_retrieved_at = name, url, datetime.now(UTC)
    draft.missing_fields = [f for f in draft.missing_fields if f != "title" or not draft.title]
    draft.extracted_fields = _extracted_fields(draft)
    draft.warnings = ["This was read automatically from a web page, so it may be incomplete or out of order. Please check every field.", *draft.warnings]
    is_problem = _looks_like_a_problem(draft, readable.text)
    if not is_problem:
        draft.warnings.insert(0, "This page may not be a problem statement. Please check it carefully.")
    complete = is_problem and "description" not in draft.missing_fields and "examples" not in draft.missing_fields
    return LookupOut(
        supported=True, status="extracted" if complete else "partial", source_name=name, source_url=url, access="public_page", draft=draft,
        extracted_fields=draft.extracted_fields, missing_fields=draft.missing_fields,
        message=f"Read from {name}. Please check it before saving, since it may not be complete. These are public details from the page, not the site's hidden tests.",
    )


def lookup(query: str) -> LookupOut:
    query = query.strip()
    # Platform identifiers first, since these are not web addresses.
    match = CF_ID.match(query)
    if match:
        return _codeforces(int(match.group(1)), match.group(2).upper())
    match = ATCODER_ID.match(query)
    if match:
        contest, letter = match.group(1).lower(), match.group(2).lower()
        query = f"https://atcoder.jp/contests/{contest}/tasks/{contest}_{letter}"
    match = LEETCODE_ID.match(query)
    if match:
        slug = re.sub(r"\s+", "-", match.group(1).strip().lower())
        query = f"https://leetcode.com/problems/{slug}/"

    if "." not in query.split("/")[0] and "://" not in query:
        return LookupOut(supported=False, status="invalid", reason_code="unknown_id", source_name=None, access="none",
                         message="That ID could not be matched to a site. Use a full link, or a Codeforces or AtCoder ID such as 1872A or abc300_a.", guidance=PASTE_GUIDANCE)
    try:
        url = fetcher.normalise_url(query)
    except FetchRefused as refused:
        return LookupOut(supported=False, status="invalid", reason_code=refused.code, source_name=None, access="none", message=refused.message, guidance=PASTE_GUIDANCE)

    host = fetcher.host_of(url)
    plain = host.removeprefix("www.")
    if any(plain == blocked or plain.endswith("." + blocked) for blocked in settings.import_blocked_domain_list):
        name = source_name_for(url) or plain
        return _keep_link(name, url, "blocked_by_server", f"This server is set not to open pages from {name}.")
    source = source_for(host)
    if source and source.route == "url_only":
        return _url_only(source, url)
    if source and source.name == "Codeforces":
        found = CF_URL.search(url)
        if found:
            return _codeforces(int(found.group(1)), found.group(2).upper())
        return _failed("not_a_problem_link", "That Codeforces link does not point to a problem. Problem links look like codeforces.com/problemset/problem/1872/A.", "Codeforces", url)
    return _from_public_page(url, source)
