# Importing questions

A learner can bring a problem from anywhere and practise it with the same tutor. Imported questions become ordinary private problems, so every agent, the progress dashboard and the planner treat them normally. Evidence from them counts for half as much towards mastery, because the tests are less certain.

## The flow

1. **Add question**, then choose **Paste question** or **Import from a link**.
2. Paste the question, or enter a link or problem ID. Paste can also take a source link, a topic and notes.
3. Review what was found and what is missing.
4. Fill in anything missing. Nothing is made up, so blanks stay blank.
5. Review and edit the tests.
6. Save and start practising.

## Paste: always available

`imports/parser.py` reads titles, descriptions, constraints, input and output formats, examples and function signatures with deterministic rules. Each field comes from the text, or is reported as missing. Very long sections are shortened with a warning, and unusual formats are corrected at review. A source link given here is only recorded, and the page is not opened.

## Link: best effort, not universal

Each request takes the most respectful route that works (`imports/sources.py`).

| Site | Route | Why | What the learner gets |
|---|---|---|---|
| LeetCode | Link only, never contacted | Terms of service forbid crawling and scraping | Source, title from the link's own words, then paste |
| HackerRank | Link only, never contacted | Terms do not allow copying parts of the service | As above |
| GeeksforGeeks | Link only, never contacted | Terms do not allow automated access or data extraction | As above |
| CodeChef | Link only, never contacted | Terms do not allow crawling or scraping, and robots.txt excludes `/problems/*` | As above |
| Take U Forward | Link only, never contacted | Terms do not allow automated tools | As above |
| Codeforces | Official API | Public API, which has no statements | Title, tags and rating, then paste |
| AtCoder | Page, if allowed | robots.txt allows task pages, but they are currently marked `noai` | Respected at runtime, so currently source and then paste |
| Any other public page | Page, if allowed | robots.txt and machine-readable signals are checked each time | Readable fields, then review |

**Checked on 9 November 2026.** Terms and robots files change, so review this table periodically. A lawyer has not reviewed it. LeetCode's terms page refused a direct fetch, so that entry relies on a search summary of its official terms, and should be confirmed by reading the page in a browser. Terms cannot be read by a machine, so an unlisted site is only checked through robots.txt and signals. Add domains to `SOURCES`, or to `IMPORT_BLOCKED_DOMAINS`, to change how a site is treated.

This means **none of the named coding sites currently provide a statement automatically**. The link still gives attribution and carries the learner to paste, with the reason explained. Reading works on sites that allow it. It was tried live on Project Euler, Rosetta Code and Wikipedia.

Problem IDs: `1872A` or `cf 1872A` (Codeforces), `abc300_a` (AtCoder), `lc two-sum` (LeetCode, link only).

### What happens to a page

1. **Validate and normalise the URL.** Tracking parameters are removed. Private addresses are refused. See [security.md](security.md).
2. **Read robots.txt,** using RFC 9309 matching. Python's standard `urllib.robotparser` ignores `*` and `$` in paths, which would wrongly allow CodeChef's problem pages, so it is not used. An unreachable robots.txt counts as a refusal.
3. **Fetch once,** with limits on time and size, spacing per host, and caching.
4. **Respect `noai` and `ai-input=no`,** since page text can reach a language model.
5. **Clean it.** Scripts, styles, navigation, comments and anything hidden from readers are removed.
6. **Parse it** with the same rules as paste, and report what was found and what is missing.

Anything that goes wrong ends with a plain explanation and a way to paste. Unless the address itself is unusable, the link is kept as the source.

## Tests are labelled by where they came from

| Label | Meaning | Runs by default? |
|---|---|---|
| Imported example | From the pasted text or the page | Yes |
| Added by you | Written by the learner | When it has an expected output |
| Generated suggestion | Proposed from the examples and constraints: empty, minimal, boundary, repeated, negative, large | Only with an expected output |

- **Expected outputs are never guessed.** A generated test is marked "needs expected output" and stays off until the learner supplies one.
- The exception is a large-input check, which only requires finishing in time, and says so.
- **Imported or generated tests are never the platform's hidden tests.** The review step, the problem page and the success message all say so.
- Invalid or oversized tests (over 256 KB) are refused with a message naming the test.

## Provenance

Each imported question stores its source name, link and retrieval time. It is private to the learner who added it. A correct solution here does not mean the original site would accept it.
