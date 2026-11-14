"""Fetch one public web page at a learner's request, safely and politely.

A server that opens any URL it is given can be used to reach private networks (SSRF), so:
- Only http and https on the standard ports. No credentials in URLs, no bare hostnames, no IP literals.
- Every address a name resolves to must be public, and the connection goes to that checked address, so a
  name cannot change to a private address between the check and the request (DNS rebinding).
- Each redirect is checked again from the start. Time and size are limited, including after decompression.

To be polite:
- robots.txt is read and followed, using RFC 9309 matching. Python's urllib.robotparser ignores `*` and `$`
  in paths, which would wrongly allow pages such as CodeChef's `Disallow: /problems/*`.
- A site's Content-Signal of ai-input=no is respected, since page text can reach a language model.
- Requests to one host are spaced out, and results are cached, so repeated clicks do not repeat requests.

Terms of service cannot be read by a machine. Sites known to restrict automated access are listed in
sources.py and never reach this module.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

log = logging.getLogger("csmasf.imports")

USER_AGENT = "CodePath-import/1.0 (educational Python tutor; fetches one page at a learner's request; follows robots.txt)"
AGENT_TOKEN = "codepath-import"
MAX_REDIRECTS = 3
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_ROBOTS_BYTES = 512 * 1024
TOTAL_SECONDS = 12.0
MIN_INTERVAL_SECONDS = 2.0
MAX_CRAWL_DELAY_SECONDS = 30.0
ROBOTS_CACHE_SECONDS = 3600
PAGE_CACHE_SECONDS = 600
ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
TRACKING_PARAMS = re.compile(r"^(utm_.+|fbclid|gclid|mc_[a-z]+|ref|ref_src|igshid|si)$", re.I)

transport: httpx.BaseTransport | None = None  # replaced in tests


class FetchRefused(Exception):
    """The page was not fetched, or could not be used. `code` says why, and the message is safe to show."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Page:
    url: str
    final_url: str
    content_type: str
    text: str
    fetched_at: float = field(default_factory=time.time)


def resolve(host: str, port: int) -> list[str]:
    """All addresses for a name. Kept separate so tests need no real DNS."""
    return sorted({info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})


def normalise_url(raw: str) -> str:
    """Validate a learner's URL and give it a canonical form. Raises FetchRefused for anything unusable."""
    text = raw.strip()
    if not text or any(ch.isspace() for ch in text) or any(ord(ch) < 32 for ch in text):
        raise FetchRefused("invalid_url", "That does not look like a web address.")
    if "://" not in text:
        text = f"https://{text}"
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError as exc:
        raise FetchRefused("invalid_url", "That does not look like a web address.") from exc
    if parts.scheme.lower() not in ("http", "https"):
        raise FetchRefused("invalid_url", "Only http and https links can be imported.")
    if parts.username or parts.password:
        raise FetchRefused("invalid_url", "Links containing a username or password cannot be imported.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise FetchRefused("invalid_url", "That does not look like a web address.")
    if port not in (None, 80, 443):
        raise FetchRefused("not_allowed_address", "Only links on the standard web ports can be imported.")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        raise FetchRefused("not_allowed_address", "Links to a raw IP address cannot be imported. Please use the site's normal address.")
    if "." not in host or host.endswith((".local", ".localhost", ".internal", ".intranet", ".lan", ".home", ".corp")):
        raise FetchRefused("not_allowed_address", "This address is not a public website, so it cannot be imported.")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise FetchRefused("invalid_url", "That web address is not valid.") from exc
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not TRACKING_PARAMS.match(k)])
    netloc = ascii_host if port is None else f"{ascii_host}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def checked_address(host: str, port: int) -> str:
    """An address that is safe to connect to. Every resolved address must be public, not just the first."""
    try:
        addresses = resolve(host, port)
    except OSError as exc:
        raise FetchRefused("unreachable", "That website could not be found. Please check the link.") from exc
    if not addresses:
        raise FetchRefused("unreachable", "That website could not be found. Please check the link.")
    if not all(_is_public(address) for address in addresses):
        log.warning("refused a link that resolves to a non-public address")
        raise FetchRefused("not_allowed_address", "This address is not a public website, so it cannot be imported.")
    return addresses[0]


@dataclass
class _Response:
    status: int
    headers: httpx.Headers
    body: bytes
    url: str


def _request(url: str, limit: int, deadline: float) -> _Response:
    """One GET, following checked redirects. The connection goes to the address that was checked."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(current)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        address = checked_address(host, port)
        pinned = f"[{address}]" if ":" in address else address
        netloc = pinned if parts.port is None else f"{pinned}:{parts.port}"
        target = urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))
        host_header = parts.netloc
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchRefused("timeout", "That website took too long to respond.")
        timeout = httpx.Timeout(min(remaining, 8.0), connect=min(remaining, 5.0))
        try:
            with httpx.Client(transport=transport, timeout=timeout, follow_redirects=False) as client:
                request_headers = {"Host": host_header, "User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8", "Accept-Language": "en"}
                with client.stream("GET", target, headers=request_headers, extensions={"sni_hostname": host}) as response:
                    if response.is_redirect and response.headers.get("location"):
                        current = normalise_url(urljoin(current, response.headers["location"]))
                        continue
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > limit:
                            raise FetchRefused("too_large", "That page is too large to import.")
                        if time.monotonic() > deadline:
                            raise FetchRefused("timeout", "That website took too long to respond.")
                        chunks.append(chunk)
                    return _Response(response.status_code, response.headers, b"".join(chunks), current)
        except httpx.TimeoutException as exc:
            raise FetchRefused("timeout", "That website took too long to respond.") from exc
        except httpx.HTTPError as exc:
            raise FetchRefused("unreachable", "That website could not be reached just now.") from exc
    raise FetchRefused("too_many_redirects", "That link redirected too many times.")


# ---------------------------------------------------------------- robots.txt (RFC 9309)

@dataclass
class RobotsRules:
    rules: list[tuple[bool, str]] = field(default_factory=list)
    crawl_delay: float | None = None
    signals: dict[str, str] = field(default_factory=dict)
    disallow_all: bool = False


_FIELD = re.compile(r"^\s*([A-Za-z-]+)\s*:\s*(.*?)\s*$")


def parse_robots(text: str, token: str = AGENT_TOKEN) -> RobotsRules:
    """Rules for this agent: the group naming it, otherwise the `*` group."""
    groups: list[tuple[list[str], list[tuple[bool, str]], float | None, dict[str, str]]] = []
    agents: list[str] = []
    rules: list[tuple[bool, str]] = []
    delay: float | None = None
    signals: dict[str, str] = {}
    in_rules = False

    def close() -> None:
        if agents:
            groups.append((list(agents), list(rules), delay, dict(signals)))

    for raw in text.splitlines():
        match = _FIELD.match(raw.split("#", 1)[0])
        if not match:
            continue
        name, value = match.group(1).lower(), match.group(2)
        if name == "user-agent":
            if in_rules:
                close()
                agents, rules, delay, signals, in_rules = [], [], None, {}, False
            agents.append(value.lower())
        elif name in ("allow", "disallow"):
            in_rules = True
            if value:
                rules.append((name == "allow", value))
        elif name == "crawl-delay":
            in_rules = True
            try:
                delay = float(value)
            except ValueError:
                pass
        elif name == "content-signal":
            in_rules = True
            for part in value.split(","):
                key, _, setting = part.partition("=")
                if setting:
                    signals[key.strip().lower()] = setting.strip().lower()
    close()

    named = [g for g in groups if any(a != "*" and a in token for a in g[0])]
    chosen = named or [g for g in groups if "*" in g[0]]
    merged = RobotsRules()
    for _, group_rules, group_delay, group_signals in chosen:
        merged.rules.extend(group_rules)
        merged.crawl_delay = group_delay if group_delay is not None else merged.crawl_delay
        merged.signals.update(group_signals)
    return merged


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    return re.compile("".join(".*" if ch == "*" else re.escape(ch) for ch in body) + ("$" if anchored else ""))


def robots_allows(rules: RobotsRules, path_and_query: str) -> bool:
    """The longest matching rule wins, and on a tie Allow wins. No matching rule means allowed."""
    if rules.disallow_all:
        return False
    if path_and_query.split("?", 1)[0] == "/robots.txt":
        return True
    best_length, allowed = -1, True
    for is_allow, pattern in rules.rules:
        if _pattern_regex(pattern).match(path_and_query):
            length = len(pattern)
            if length > best_length or (length == best_length and is_allow):
                best_length, allowed = length, is_allow
    return allowed


_robots_cache: dict[str, tuple[float, RobotsRules]] = {}
_page_cache: dict[str, Page] = {}
_last_request: dict[str, float] = {}
_lock = threading.Lock()


def clear_caches() -> None:
    with _lock:
        _robots_cache.clear()
        _page_cache.clear()
        _last_request.clear()


def _robots_for(scheme: str, netloc: str, deadline: float) -> RobotsRules:
    now = time.monotonic()
    with _lock:
        cached = _robots_cache.get(netloc)
        if cached and now - cached[0] < ROBOTS_CACHE_SECONDS:
            return cached[1]
    try:
        response = _request(f"{scheme}://{netloc}/robots.txt", MAX_ROBOTS_BYTES, deadline)
        if response.status >= 500 or response.status == 429:
            rules = RobotsRules(disallow_all=True)  # RFC 9309: an unreachable robots.txt means assume everything is disallowed
        elif response.status >= 400:
            rules = RobotsRules()  # RFC 9309: no robots.txt means no restrictions
        else:
            rules = parse_robots(response.body.decode("utf-8", errors="replace"))
    except FetchRefused as refused:
        if refused.code in ("not_allowed_address", "invalid_url"):
            raise
        rules = RobotsRules(disallow_all=True)
    with _lock:
        _robots_cache[netloc] = (now, rules)
    return rules


def _space_out(host: str, delay: float | None) -> None:
    interval = max(MIN_INTERVAL_SECONDS, min(delay or 0.0, MAX_CRAWL_DELAY_SECONDS))
    now = time.monotonic()
    with _lock:
        last = _last_request.get(host)
        if last is not None and now - last < interval:
            wait = int(interval - (now - last)) + 1
            raise FetchRefused("rate_limited", f"This site was contacted a moment ago. Please try again in about {wait} seconds.")
        _last_request[host] = now


def fetch_page(raw_url: str) -> Page:
    """Fetch a public page if the site allows it. Raises FetchRefused with a clear reason if not."""
    url = normalise_url(raw_url)
    with _lock:
        cached = _page_cache.get(url)
        if cached and time.time() - cached.fetched_at < PAGE_CACHE_SECONDS:
            return cached
    deadline = time.monotonic() + TOTAL_SECONDS
    parts = urlsplit(url)
    path = parts.path + (f"?{parts.query}" if parts.query else "")
    rules = _robots_for(parts.scheme, parts.netloc, deadline)
    if rules.disallow_all:
        raise FetchRefused("robots_unavailable", "This site's robots.txt could not be read, so the page was not opened.")
    if not robots_allows(rules, path):
        raise FetchRefused("robots_disallow", "This site's robots.txt asks automated tools not to open this page, so it was not opened.")
    if rules.signals.get("ai-input") == "no":
        raise FetchRefused("content_signal", "This site asks that its content not be used as input for AI tools, so the page was not opened.")
    _space_out(parts.hostname or "", rules.crawl_delay)

    response = _request(url, MAX_PAGE_BYTES, deadline)
    if response.url != url:
        # A redirect can lead somewhere with different rules.
        moved = urlsplit(response.url)
        moved_rules = _robots_for(moved.scheme, moved.netloc, deadline)
        if not robots_allows(moved_rules, moved.path + (f"?{moved.query}" if moved.query else "")):
            raise FetchRefused("robots_disallow", "That link leads to a page that robots.txt asks automated tools not to open.")
    if response.status in (401, 402, 403):
        raise FetchRefused("login_required", "This site did not let the page be opened automatically. It may need a sign-in, or it may refuse automated requests.")
    if response.status == 404 or response.status == 410:
        raise FetchRefused("not_found", "That page was not found. Please check the link.")
    if response.status == 429:
        raise FetchRefused("site_rate_limited", "This site is limiting requests right now. Please try again later, or paste the question.")
    if response.status >= 400:
        raise FetchRefused("unreachable", "That website could not provide the page just now.")
    if "noai" in response.headers.get("x-robots-tag", "").lower():
        raise FetchRefused("content_signal", "This site asks that its content not be used by AI tools, so the page was not used.")
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_TYPES:
        raise FetchRefused("not_a_page", "That link is not a web page, so it cannot be read here. If it is a PDF or a file, please paste the question.")
    charset = response.headers.get_charset_encoding() if hasattr(response.headers, "get_charset_encoding") else None
    match = re.search(r"charset=([\w-]+)", response.headers.get("content-type", ""), re.I)
    encoding = (match.group(1) if match else charset) or "utf-8"
    try:
        text = response.body.decode(encoding, errors="replace")
    except LookupError:
        text = response.body.decode("utf-8", errors="replace")
    page = Page(url=url, final_url=response.url, content_type=content_type or "text/html", text=text)
    with _lock:
        if len(_page_cache) > 200:
            _page_cache.clear()
        _page_cache[url] = page
    return page
