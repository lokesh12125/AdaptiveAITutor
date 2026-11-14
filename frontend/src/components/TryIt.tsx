import { pythonLanguage } from "@codemirror/lang-python";
import { highlightTree } from "@lezer/highlight";
import { Pencil, Play, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError, api, newKey } from "@/api/client";
import type { Evaluation, TestResult } from "@/api/types";
import { CodeEditor, highlight } from "@/workspace/Editor";

import { Button, Spinner } from "./ui";

const FINISHED = new Set(["completed", "failed", "cancelled"]);
const POLL_MS = 300;
const GIVE_UP_MS = 30_000;

export function CodeBlock({ code }: { code: string }) {
  const parts = useMemo(() => {
    const out: { text: string; className: string }[] = [];
    let position = 0;
    highlightTree(pythonLanguage.parser.parse(code), highlight, (from, to, className) => {
      if (from > position) out.push({ text: code.slice(position, from), className: "" });
      out.push({ text: code.slice(from, to), className });
      position = to;
    });
    if (position < code.length) out.push({ text: code.slice(position), className: "" });
    return out;
  }, [code]);
  return <pre className="tryit-code" tabIndex={0}><code>{parts.map((part, index) => (part.className ? <span key={index} className={part.className}>{part.text}</span> : part.text))}</code></pre>;
}

function describe(evaluation: Evaluation): { text: string; error: boolean } {
  const result = (evaluation.results as unknown as TestResult[])[0];
  if (evaluation.status !== "completed" || !result) return { text: evaluation.message ?? "That could not be run. Please try again.", error: true };
  const printed = result.stdout ?? "";
  if (result.error) {
    const where = result.error.line ? ` on line ${result.error.line}` : "";
    return { text: `${printed}${printed && !printed.endsWith("\n") ? "\n" : ""}${result.error.type}${where}: ${result.error.message}`, error: true };
  }
  return { text: printed || "This code ran and printed nothing.", error: false };
}

/** A lesson example you can run and change. It runs in the same isolated sandbox as everything else, and is never graded. */
export function TryIt({ title, code: original, note }: { title?: string; code: string; note?: string }) {
  const [code, setCode] = useState(original);
  const [editing, setEditing] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<{ text: string; error: boolean } | null>(null);
  const latest = useRef(0);
  const runButton = useRef<HTMLButtonElement>(null);
  useEffect(() => () => { latest.current = -1; }, []);

  const run = async () => {
    const token = ++latest.current;
    setRunning(true);
    setOutput(null);
    try {
      const accepted = await api<{ id: string }>("/playground/run", { method: "POST", body: { code, idempotency_key: newKey() } });
      const deadline = Date.now() + GIVE_UP_MS;
      for (;;) {
        const evaluation = await api<Evaluation>(`/evaluations/${accepted.id}`);
        if (token !== latest.current) return;
        if (FINISHED.has(evaluation.status)) { setOutput(describe(evaluation)); break; }
        if (Date.now() > deadline) { setOutput({ text: "This is taking too long, so the result was not shown. Please try again.", error: true }); break; }
        await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
      }
    } catch (error) {
      if (token === latest.current) setOutput({ text: error instanceof ApiError ? error.message : "That could not be run. Please try again.", error: true });
    } finally {
      if (token === latest.current) setRunning(false);
    }
  };

  return (
    <figure className="tryit" data-testid="tryit">
      <figcaption className="tryit-head">
        <span>{title ?? "Example"}</span>
        <span className="row" style={{ gap: 4 }}>
          {code !== original && <Button variant="ghost" size="small" onClick={() => { setCode(original); setEditing(false); setOutput(null); }}><RotateCcw size={13} aria-hidden /> Reset</Button>}
          {!editing && <Button variant="ghost" size="small" onClick={() => setEditing(true)} data-testid="tryit-edit"><Pencil size={13} aria-hidden /> Edit</Button>}
          <Button ref={runButton} size="small" variant="primary" disabled={running} onClick={() => void run()} data-testid="tryit-run">{running ? <Spinner /> : <Play size={13} aria-hidden />} Run code</Button>
        </span>
      </figcaption>
      {editing ? (
        <div className="tryit-editor">
          <CodeEditor
            initialCode={code} onChange={setCode} onRun={() => void run()} onSubmit={() => void run()} onHint={() => undefined} onSave={() => undefined} onEscape={() => runButton.current?.focus()}
            tabSize={4} lineWrap={false} showLineNumbers syntaxFeedback={false} markedLines={[]}
          />
        </div>
      ) : <CodeBlock code={code} />}
      {output && (
        <div className="tryit-output-wrap">
          <span className="tryit-output-label">{output.error ? "Error" : "Output"}</span>
          <div className="tryit-output" role="status" data-error={output.error} data-testid="tryit-output" tabIndex={0}>{output.text}</div>
        </div>
      )}
      {note && <div className="tryit-note">{note}</div>}
    </figure>
  );
}
