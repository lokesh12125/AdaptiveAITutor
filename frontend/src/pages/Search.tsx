import { useQuery } from "@tanstack/react-query";
import { BookOpen, ListChecks, Search as SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type { SearchResults } from "@/api/types";
import { EmptyState, ErrorState } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";

/** Search across topics, lesson sections, glossary terms, techniques and problems. */
export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const asked = params.get("q") ?? "";
  const [text, setText] = useState(asked);
  useEffect(() => setText(asked), [asked]);
  useEffect(() => {
    const timer = window.setTimeout(() => { if (text.trim() !== asked) setParams(text.trim() ? { q: text.trim() } : {}, { replace: true }); }, 250);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);
  const query = useQuery<SearchResults>({ queryKey: ["search", asked], queryFn: () => api<SearchResults>(`/search?q=${encodeURIComponent(asked)}`), enabled: asked.length >= 2, placeholderData: (previous) => previous });
  const data = asked.length >= 2 ? query.data : undefined;
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div><h1>Search</h1><p>Find a topic, a lesson section, a term or a problem.</p></div>
      </div>
      <label className="row" style={{ position: "relative", gap: 0 }} role="search">
        <span className="sr-only">Search topics and problems</span>
        <SearchIcon size={15} aria-hidden style={{ position: "absolute", left: 11, color: "var(--text-3)" }} />
        <input className="input" style={{ paddingLeft: 33 }} placeholder="For example: sliding window, recursion, or time complexity" value={text} onChange={(event) => setText(event.target.value)} data-testid="search-input" />
      </label>
      {query.isError && <ErrorState error={query.error} what="Search" onRetry={() => void query.refetch()} />}
      {asked.length < 2 && <p className="muted">Type at least two letters.</p>}
      {data && data.topics.length === 0 && data.problems.length === 0 && <div className="card"><EmptyState title="Nothing found">Try a different word, or fewer words.</EmptyState></div>}
      {data && data.topics.length > 0 && (
        <section className="card stack-s" aria-labelledby="search-topics">
          <h2 id="search-topics" className="row" style={{ gap: 8 }}><BookOpen size={18} aria-hidden /> Topics and notes</h2>
          <div>
            {data.topics.map((hit) => (
              <Link key={hit.id} to={`/path/${hit.id}${hit.section ? `#${hit.section}` : ""}`} className="card-link" data-testid="search-topic">
                <span className="grow"><strong>{hit.title}</strong><br /><span className="subtle">{hit.where}: {hit.text}</span></span>
              </Link>
            ))}
          </div>
        </section>
      )}
      {data && data.problems.length > 0 && (
        <section className="card stack-s" aria-labelledby="search-problems">
          <h2 id="search-problems" className="row" style={{ gap: 8 }}><ListChecks size={18} aria-hidden /> Problems</h2>
          <div>
            {data.problems.map((hit) => (
              <Link key={hit.id} to={`/problems/${hit.id}`} className="card-link" data-testid="search-problem">
                <span className="grow"><strong>{hit.title}</strong><br /><span className="subtle">{[hit.unit_title, hit.pattern].filter(Boolean).join(" · ")}</span></span>
                {hit.difficulty && <span className={`badge badge-${hit.difficulty}`}>{DIFFICULTY_LABEL[hit.difficulty]}</span>}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
