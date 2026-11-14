"""Turn a fetched web page into readable text that the paste parser can understand.

Page content is untrusted. Scripts, styles and anything hidden from readers are removed, so hidden text
cannot slip instructions into the question. The result is plain text, and it is shown to the learner to
review before anything is saved.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

MAX_TEXT_CHARS = 25000
REMOVE = ("script", "style", "noscript", "template", "svg", "canvas", "iframe", "object", "embed", "form", "input", "button", "select", "textarea", "nav", "footer", "aside", "link", "meta")
HIDDEN_STYLE = re.compile(r"(display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0+)?\b|font-size\s*:\s*0)", re.I)
BOILERPLATE_CLASS = re.compile(r"(^|[-_ ])(comment|comments|sidebar|cookie|advert|advertisement|share|social|newsletter|related|breadcrumb|dropdown|menu|toc|navbox|portlet|langlinks|sitesub|editsection)s?($|[-_ ])", re.I)
BLOCK = {"p", "div", "section", "article", "main", "header", "ul", "ol", "dl", "dt", "dd", "blockquote", "table", "thead", "tbody", "tr", "figure", "figcaption", "hr", "details", "summary"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


@dataclass
class Readable:
    title: str
    text: str
    tags: list[str]
    no_ai: bool = False


def _render(node: Tag | NavigableString, out: list[str]) -> None:
    if isinstance(node, NavigableString):
        out.append(re.sub(r"\s+", " ", str(node)))
        return
    if not isinstance(node, Tag):
        return
    name = node.name
    if name == "pre":
        out.append("\n\n" + node.get_text().strip("\n") + "\n\n")
    elif name == "br":
        out.append("\n")
    elif name == "sup":
        text = node.get_text().strip()
        if not re.fullmatch(r"\[.*\]", text):  # a citation mark such as [1] is not an exponent
            out.append("^" + text)
    elif name == "sub":
        out.append("_" + node.get_text().strip())
    elif name in HEADINGS:
        out.append("\n\n" + re.sub(r"\s+", " ", node.get_text()).strip() + "\n")
    elif name == "li":
        out.append("\n- ")
        for child in node.children:
            _render(child, out)
    elif name in ("td", "th"):
        for child in node.children:
            _render(child, out)
        out.append("  ")
    else:
        block = name in BLOCK
        if block:
            out.append("\n")
        for child in node.children:
            _render(child, out)
        if block:
            out.append("\n")


def _is_hidden(tag: Tag) -> bool:
    if tag.has_attr("hidden") or tag.get("aria-hidden") == "true":
        return True
    style = tag.get("style")
    return isinstance(style, str) and bool(HIDDEN_STYLE.search(style))


def _clean(soup: BeautifulSoup) -> None:
    for name in REMOVE:
        for tag in soup.find_all(name):
            tag.decompose()
    for tag in soup.find_all(True):
        if tag.decomposed:
            continue
        classes = " ".join(tag.get("class") or []) if tag.attrs is not None else ""
        if _is_hidden(tag) or (tag.name not in ("html", "body", "main", "article") and classes and BOILERPLATE_CLASS.search(classes)):
            tag.decompose()


def _json_ld(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and (item.get("headline") or item.get("name")):
                return item
    return {}


def _title(soup: BeautifulSoup, host: str, ld: dict) -> str:
    # The page's own heading first. JSON-LD "headline" often holds a description rather than a title.
    candidates: list[str] = []
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        candidates.append(str(meta["content"]))
    heading = soup.find("h1")
    if heading:
        candidates.append(heading.get_text(" ", strip=True))
    for key in ("name", "headline"):
        if isinstance(ld.get(key), str):
            candidates.append(ld[key])
    if soup.title and soup.title.string:
        candidates.append(str(soup.title.string))
    site = host.removeprefix("www.").split(".")[0].lower()
    for candidate in candidates:
        cleaned = re.sub(r"\s+", " ", candidate).strip()
        parts = re.split(r"\s+[|–—-]\s+", cleaned)
        if len(parts) > 1 and (site in re.sub(r"[^a-z0-9]", "", parts[-1].lower()) or len(parts[-1]) > len(parts[0]) * 3):
            cleaned = " - ".join(parts[:-1]) if len(parts) > 2 else parts[0]
        if 3 <= len(cleaned) <= 160:
            return cleaned
    return ""


def _largest_block(soup: BeautifulSoup) -> Tag:
    body = soup.body or soup
    best, best_length = body, 0
    for tag in body.find_all(["div", "section"]):
        direct = sum(len(str(p.get_text())) for p in tag.find_all(["p", "pre", "li"], recursive=False))
        if direct > best_length:
            best, best_length = tag, direct
    return best if best_length > 200 else body


def _to_text(container: Tag) -> str:
    out: list[str] = []
    _render(container, out)
    text = "".join(out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+(?=\S)", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_TEXT_CHARS]


def extract_readable(html: str, host: str, selector: str | None = None) -> Readable:
    soup = BeautifulSoup(html, "html.parser")
    robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    no_ai = bool(robots_meta and "noai" in str(robots_meta.get("content", "")).lower())
    ld = _json_ld(soup)
    title = _title(soup, host, ld)
    raw_tags = ld.get("keywords") if isinstance(ld.get("keywords"), (list, str)) else []
    tags = [t.strip() for t in (raw_tags.split(",") if isinstance(raw_tags, str) else raw_tags) if isinstance(t, str) and t.strip()][:20]
    _clean(soup)
    container: Tag | None = None
    if selector:
        container = soup.select_one(selector)
    if container is None:
        container = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or _largest_block(soup)
    return Readable(title=title, text=_to_text(container), tags=tags, no_ai=no_ai)
