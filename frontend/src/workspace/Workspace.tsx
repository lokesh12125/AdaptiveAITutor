import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, Check, History, ChevronLeft, ChevronRight, CloudOff, Keyboard, Lightbulb, MessageCircleQuestion, PanelLeftClose, PanelLeftOpen, Play, RotateCcw, Search, Send, TextCursorInput, Type, WrapText } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { type ImperativePanelHandle, Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { Preferences, UnitDetail, Workspace } from "@/api/types";
import { LogoMark, SystemBanners, ThemeToggle } from "@/components/Shell";
import { Button, Confirm, ErrorState, Modal, Notice, PageLoading, Spinner, Tip } from "@/components/ui";
import { DIFFICULTY_LABEL } from "@/lib/format";
import { useSession } from "@/lib/session";

import { CodeEditor, type EditorHandle } from "./Editor";
import { LearnPane } from "./LearnPane";
import { Submissions } from "./Submissions";
import { type CaseState, casesChanged, casesForRun, initialCases } from "./TestCases";
import { ProblemPane } from "./ProblemPane";
import { ResultsPane } from "./ResultsPane";
import { TutorPane } from "./TutorPane";
import { useActions, type HintOptions } from "./useActions";
import { loadInitialCode, useActiveSeconds, useDraft, type SaveState } from "./useDraft";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia?.(query).matches ?? false);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);
  return matches;
}

function SaveIndicator({ state, onRetry }: { state: SaveState; onRetry: () => void }) {
  if (state === "failed") {
    return (
      <span className="save-status" data-state="failed" role="status" data-testid="save-status">
        <CloudOff size={13} aria-hidden /> Failed to save. It is safe in this browser. <button type="button" className="btn-link" onClick={onRetry}>Retry</button>
      </span>
    );
  }
  if (state === "saving") return <span className="save-status" data-testid="save-status" data-state="saving"><Spinner /> Saving…</span>;
  if (state === "saved") return <span className="save-status" data-testid="save-status" data-state="saved" role="status"><Check size={13} aria-hidden /> Saved</span>;
  return <span className="save-status" data-testid="save-status" data-state="idle" />;
}

function ShortcutsDialog({ open, onOpenChange, mod }: { open: boolean; onOpenChange: (open: boolean) => void; mod: string }) {
  const rows: [string, string][] = [
    [`${mod} Enter`, "Run the examples"], [`${mod} Shift Enter`, "Submit for checking"], ["Alt H", "Ask for a hint"], [`${mod} S`, "Save now"], [`${mod} F`, "Find and replace in code"], [`${mod} Z`, "Undo"], [`${mod} Shift Z`, "Redo"],
    ["Tab", "Indent, while in the editor"], ["Esc, then Tab", "Leave the editor and move on"], ["?", "Show this list, when not typing in the editor"],
  ];
  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Keyboard shortcuts">
      <table className="table"><tbody>{rows.map(([keys, what]) => <tr key={keys}><td className="nowrap"><kbd>{keys}</kbd></td><td>{what}</td></tr>)}</tbody></table>
      <p className="subtle">Panel dividers can be focused with Tab and resized with the arrow keys.</p>
      <div className="dialog-actions"><Button onClick={() => onOpenChange(false)}>Close</Button></div>
    </Modal>
  );
}

function Loaded({ workspace }: { workspace: Workspace }) {
  const { user, preferences, updatePreferences } = useSession();
  const problem = workspace.problem;
  const [initial] = useState(() => loadInitialCode(user!.id, problem.id, workspace.draft, problem.starter_code));
  const [code, setCode] = useState(initial.code);
  const codeRef = useRef(initial.code);
  const [restoredNote, setRestoredNote] = useState(initial.restored);
  const [selfConfidence, setSelfConfidence] = useState<"low" | "medium" | "high" | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const editor = useRef<EditorHandle>(null);
  const draft = useDraft(user!.id, problem.id);
  const active = useActiveSeconds(user!.id, problem.id, workspace.active_seconds);
  const actions = useActions(problem.id, workspace, () => active.current);
  // Two panes suit most screens: room to read, and the code beside whatever the tutor says. A third fits only on a very wide one.
  const wide = useMediaQuery("(min-width: 1640px)");
  const medium = useMediaQuery("(min-width: 760px)");
  const [mobileTab, setMobileTab] = useState("code");
  const [sideTab, setSideTab] = useState("problem");
  const [selection, setSelection] = useState<{ start: number; end: number } | null>(null);
  const [cases, setCases] = useState<CaseState[]>(() => initialCases(problem));
  const casesRef = useRef(cases);
  casesRef.current = cases;
  const sidePanel = useRef<ImperativePanelHandle>(null);
  const [sideHidden, setSideHidden] = useState(false);
  // Show this part of the side panel, reopening it if the learner had hidden it.
  const openSide = useCallback((tab: string) => {
    setSideTab(tab);
    if (sidePanel.current?.isCollapsed()) sidePanel.current.expand();
  }, []);
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
  const mod = isMac ? "⌘" : "Ctrl";

  const onChange = useCallback((value: string) => {
    codeRef.current = value;
    setCode(value);
    setRestoredNote(false);
    draft.onCodeChange(value);
  }, [draft]);

  useEffect(() => { document.title = `${problem.title} · CodePath`; }, [problem.title]);

  const report = useCallback(() => (selfConfidence ? { self_confidence: selfConfidence } : {}), [selfConfidence]);
  const doRun = useCallback(() => {
    if (actions.evaluationBusy || actions.starting) return;
    const current = casesRef.current;
    actions.start("run", codeRef.current, casesChanged(problem, current) && current.length > 0 ? { cases: casesForRun(problem, current) } : {});
    if (!medium) setMobileTab("results");
  }, [actions, medium, problem]);
  const doSubmit = useCallback(() => { if (!actions.runBusy && !actions.starting) { actions.start("submit", codeRef.current, report()); if (!medium) setMobileTab("results"); } }, [actions, medium, report]);
  // Every kind of help for this exact code has been shown, so a plain "give me a hint" could only repeat something.
  // A question or a pointed-at line is a new request, so it always goes through.
  const hintLocked = !!actions.response?.waiting && actions.run?.code === code;
  const hintChanged = !!actions.run && actions.focus === "run" && actions.run.code !== code;
  const doHint = useCallback((options: HintOptions = {}) => {
    const specific = !!options.question || !!options.self_state || options.focus_start != null;
    if (!actions.runBusy && !actions.starting && (specific || !hintLocked)) {
      actions.start("hint", codeRef.current, { ...report(), ...options });
      if (!medium) setMobileTab("tutor");
      else if (!wide) openSide("tutor");
    }
  }, [actions, hintLocked, medium, openSide, report, wide]);

  // Selecting code is how a learner points at what confuses them, so take them straight to the box to ask, wherever it is.
  const askAboutSelection = useCallback(() => {
    if (!medium) setMobileTab("tutor");
    else if (!wide) openSide("tutor");
    window.setTimeout(() => document.querySelector<HTMLTextAreaElement>('[data-testid="ask-input"]')?.focus(), 0);
  }, [medium, openSide, wide]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest(".cm-editor")) return; // the editor handles its own keys
      const mod = event.metaKey || event.ctrlKey;
      if (mod && event.key === "Enter") { event.preventDefault(); if (event.shiftKey) doSubmit(); else doRun(); }
      else if (mod && event.key.toLowerCase() === "s") { event.preventDefault(); draft.saveNow(); }
      else if (event.altKey && event.key.toLowerCase() === "h") { event.preventDefault(); doHint(); }
      else if (event.key === "?" && !/INPUT|TEXTAREA/.test(target.tagName)) { event.preventDefault(); setShortcutsOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [doHint, doRun, doSubmit, draft]);

  const reset = useCallback(() => {
    editor.current?.setCode(problem.starter_code);
    void draft.clear();
    setRestoredNote(false);
  }, [draft, problem.starter_code]);

  const editorPrefs = {
    tabSize: preferences.editor_tab_size ?? 4, lineWrap: preferences.editor_line_wrap ?? false, showLineNumbers: preferences.editor_line_numbers ?? true, syntaxFeedback: preferences.syntax_feedback ?? true,
  };
  const fontSize = preferences.editor_font_size ?? 14;
  const changeFont = (delta: number) => void updatePreferences({ editor_font_size: Math.min(24, Math.max(11, fontSize + delta)) } as Preferences);
  const markedLines = actions.focus === "run" ? actions.response?.diagnostics?.lines ?? [] : [];
  // The tutor has something to say, so show it, rather than leave it behind a tab.
  const tutorNews = actions.response?.tutor?.hint_id ?? actions.response?.waiting?.snapshot_id ?? actions.response?.offer?.label ?? null;
  const runOnArrival = useRef(workspace.latest_run?.id ?? null);
  useEffect(() => { if (tutorNews && !wide && actions.run?.id !== runOnArrival.current) openSide("tutor"); }, [tutorNews]); // eslint-disable-line react-hooks/exhaustive-deps
  const unitProblems = useQuery<UnitDetail>({ queryKey: ["unit", problem.unit_id], queryFn: () => api<UnitDetail>(`/units/${problem.unit_id}`), staleTime: 60_000, enabled: !!problem.unit_id && !problem.is_mine }).data?.problems ?? [];
  const position = unitProblems.findIndex((item) => item.id === problem.id);
  const previous = position > 0 ? unitProblems[position - 1] : null;
  const next = position >= 0 && position < unitProblems.length - 1 ? unitProblems[position + 1] : null;
  const showGuide = preferences.show_walkthroughs !== false && user?.experience_level !== "advanced" && !workspace.latest_run;
  const [guideDismissed, setGuideDismissed] = useState(false);

  const editorPane = (
    <div className="pane" aria-label="Code">
      <div className="editor-toolbar" role="toolbar" aria-label="Code actions">
        <Tip text={`Try the examples. Not graded. ${mod} Enter`}>
          <Button onClick={doRun} disabled={actions.evaluationBusy || !!actions.starting} data-testid="run" aria-keyshortcuts="Control+Enter Meta+Enter">
            {actions.evaluationBusy ? <Spinner /> : <Play size={15} aria-hidden />} Run
          </Button>
        </Tip>
        <Tip text={`Check all the tests. This counts as an attempt. ${mod} Shift Enter`}>
          <Button variant="primary" onClick={doSubmit} disabled={actions.runBusy || !!actions.starting} data-testid="submit">
            {actions.runBusy ? <Spinner /> : <Send size={15} aria-hidden />} Submit
          </Button>
        </Tip>
        {selection ? (
          <Tip text="Tell the tutor what confuses you about these lines">
            <Button variant="hint" onClick={askAboutSelection} data-testid="ask-about-lines"><MessageCircleQuestion size={15} aria-hidden /> Ask about {selection.start === selection.end ? `line ${selection.start}` : `lines ${selection.start}–${selection.end}`}</Button>
          </Tip>
        ) : (
          <Tip text={hintLocked ? "You have seen every hint for this version. Ask the tutor about a line, or change your code." : "Ask the tutor for help. Never graded. Alt H"}>
            <Button variant="hint" onClick={() => doHint()} disabled={actions.runBusy || !!actions.starting || hintLocked} data-testid="ask-hint"><Lightbulb size={15} aria-hidden /> Ask for a hint</Button>
          </Tip>
        )}
        <div className="grow" />
        <SaveIndicator state={draft.state} onRetry={() => void draft.retry()} />
        <span className="row hide-mobile" style={{ gap: 0 }}>
          <Tip text={`Find and replace. ${mod} F`}><Button variant="ghost" size="small" icon aria-label="Find and replace" onClick={() => editor.current?.openFind()} data-testid="find"><Search size={15} aria-hidden /></Button></Tip>
          <Tip text="Smaller text"><Button variant="ghost" size="small" icon aria-label="Make code text smaller" onClick={() => changeFont(-1)} data-testid="font-smaller"><Type size={12} aria-hidden /></Button></Tip>
          <Tip text="Larger text"><Button variant="ghost" size="small" icon aria-label="Make code text larger" onClick={() => changeFont(1)} data-testid="font-larger"><Type size={16} aria-hidden /></Button></Tip>
          <Tip text={editorPrefs.lineWrap ? "Stop wrapping long lines" : "Wrap long lines"}><Button variant="ghost" size="small" icon aria-pressed={editorPrefs.lineWrap} aria-label="Wrap long lines" onClick={() => void updatePreferences({ editor_line_wrap: !editorPrefs.lineWrap })}><WrapText size={15} aria-hidden /></Button></Tip>
        </span>
        <Confirm
          trigger={<Button variant="ghost" size="small" data-testid="reset"><RotateCcw size={14} aria-hidden /> Reset</Button>}
          title="Reset your code?" description="This replaces your code with the original starter code, and removes your saved draft. Earlier submissions are kept, but your current code cannot be recovered." confirmLabel="Reset code" onConfirm={reset} destructive
        />
      </div>
      {hintLocked && <div className="stale show-mobile" style={{ borderRadius: 0, flexWrap: "nowrap" }} data-testid="hint-locked-mobile"><Lightbulb size={14} style={{ flex: "none" }} aria-hidden /> <span>You have seen every hint for this version. Ask the tutor about a line, or change your code.</span></div>}
      {restoredNote && <div className="stale" style={{ borderRadius: 0 }} data-testid="restored-note"><TextCursorInput size={14} aria-hidden /> Your saved draft has been restored.</div>}
      <CodeEditor ref={editor} initialCode={initial.code} onChange={onChange} onRun={doRun} onSubmit={doSubmit} onHint={() => doHint()} onSave={draft.saveNow} onEscape={() => document.querySelector<HTMLButtonElement>('[data-testid="run"]')?.focus()} markedLines={markedLines} onSelectionChange={setSelection} {...editorPrefs} />
    </div>
  );
  const results = (
    <ResultsPane
      problem={problem} code={code} focus={actions.focus} evaluation={actions.evaluation} run={actions.run} response={actions.response} evaluationBusy={actions.evaluationBusy} runBusy={actions.runBusy} starting={actions.starting}
      busy={actions.busy} onCancel={() => void actions.cancel()} onSubmit={doSubmit} onRetrySubmit={(value) => actions.start(actions.run?.trigger === "hint_request" ? "hint" : "submit", value)} cases={cases} onCasesChange={setCases}
    />
  );
  const tutor = <TutorPane response={actions.response} workspace={workspace} busy={actions.busy} runBusy={actions.runBusy} stages={actions.run?.stages ?? []} codeChanged={hintChanged} onHint={doHint} selfConfidence={selfConfidence} onSelfConfidence={setSelfConfidence} selection={selection} onClearSelection={() => setSelection(null)} unitId={problem.unit_id} />;
  const problemPane = <ProblemPane problem={problem} showGuide={showGuide && !guideDismissed} onDismissGuide={() => { setGuideDismissed(true); void updatePreferences({ show_walkthroughs: false }); }} />;
  const handle = <PanelResizeHandle className="resize-handle" />;
  const learnOpen = medium ? sideTab === "learn" : mobileTab === "learn";
  const learnPane = <LearnPane problemId={problem.id} active={learnOpen} onAskTutor={askAboutSelection} />;
  const historyOpen = medium ? sideTab === "history" : mobileTab === "history";
  const historyPane = <Submissions problemId={problem.id} active={historyOpen} onLoadCode={(value) => { editor.current?.setCode(value); if (!medium) setMobileTab("code"); }} />;
  // On the widest screens the tutor has its own column, so it is not one of these tabs.
  const shownSide = wide && sideTab === "tutor" ? "problem" : sideTab;
  const sideTabs = (
    <Tabs.Root value={shownSide} onValueChange={setSideTab} className="mobile-tabs" style={sideHidden ? { visibility: "hidden" } : undefined}>
      <Tabs.List className="tabs-list" aria-label="Problem, learning notes or tutor">
        <Tabs.Trigger className="tab" value="problem">Problem</Tabs.Trigger>
        <Tabs.Trigger className="tab" value="learn" data-testid="tab-learn"><BookOpen size={14} aria-hidden /> Learn</Tabs.Trigger>
        <Tabs.Trigger className="tab" value="history" data-testid="tab-history"><History size={14} aria-hidden /> Submissions</Tabs.Trigger>
        {!wide && <Tabs.Trigger className="tab" value="tutor"><Lightbulb size={14} aria-hidden /> Tutor{actions.response?.tutor && sideTab !== "tutor" ? <span className="tab-dot" aria-label="New help" /> : null}</Tabs.Trigger>}
      </Tabs.List>
      <Tabs.Content value="problem" forceMount hidden={shownSide !== "problem"} style={{ minHeight: 0, flex: 1 }}>{problemPane}</Tabs.Content>
      <Tabs.Content value="learn" forceMount hidden={shownSide !== "learn"} style={{ minHeight: 0, flex: 1 }}>{learnPane}</Tabs.Content>
      <Tabs.Content value="history" forceMount hidden={shownSide !== "history"} style={{ minHeight: 0, flex: 1 }}>{historyPane}</Tabs.Content>
      {!wide && <Tabs.Content value="tutor" forceMount hidden={shownSide !== "tutor"} style={{ minHeight: 0, flex: 1 }}>{tutor}</Tabs.Content>}
    </Tabs.Root>
  );
  const collapse = { collapsible: true, collapsedSize: 0, ref: sidePanel, onCollapse: () => setSideHidden(true), onExpand: () => setSideHidden(false) };

  return (
    <div className="ws">
      <SystemBanners />
      <header className="ws-bar">
        <Link to="/" className="logo hide-mobile" aria-label="CodePath home"><LogoMark size={22} /></Link>
        {medium && (
          <Tip text={sideHidden ? "Show the side panel" : "Hide the side panel, for more room to code"}>
            <Button variant="ghost" size="small" icon aria-label={sideHidden ? "Show the side panel" : "Hide the side panel"} aria-pressed={sideHidden} onClick={() => { if (sideHidden) sidePanel.current?.expand(); else sidePanel.current?.collapse(); }} data-testid="toggle-side">
              {sideHidden ? <PanelLeftOpen size={16} aria-hidden /> : <PanelLeftClose size={16} aria-hidden />}
            </Button>
          </Tip>
        )}
        <Link to={`/path/${problem.unit_id}?tab=practice`} className="btn btn-ghost btn-small" aria-label="Back to problems"><ArrowLeft size={15} aria-hidden /><span className="hide-mobile">{problem.unit_title}</span></Link>
        <span className="ws-title grow">{problem.title}</span>
        {(previous || next) && (
          <span className="row hide-mobile" style={{ gap: 0, flexWrap: "nowrap" }}>
            {previous ? <Tip text={`Previous: ${previous.title}`}><Link to={`/problems/${previous.id}`} className="btn btn-ghost btn-small btn-icon" aria-label="Previous problem in this topic" data-testid="previous-problem"><ChevronLeft size={16} aria-hidden /></Link></Tip> : <span style={{ width: 32 }} />}
            {next ? <Tip text={`Next: ${next.title}`}><Link to={`/problems/${next.id}`} className="btn btn-ghost btn-small btn-icon" aria-label="Next problem in this topic" data-testid="next-problem"><ChevronRight size={16} aria-hidden /></Link></Tip> : <span style={{ width: 32 }} />}
          </span>
        )}
        <span className="badge hide-mobile" data-testid="language">Python 3.12</span>
        {problem.difficulty && <span className={`badge hide-mobile badge-${problem.difficulty}`}>{DIFFICULTY_LABEL[problem.difficulty]}</span>}
        {workspace.solved && <span className="badge badge-ok"><Check size={12} aria-hidden /> Solved</span>}
        <Tip text="Keyboard shortcuts"><Button variant="ghost" size="small" icon className="hide-mobile" aria-label="Keyboard shortcuts" onClick={() => setShortcutsOpen(true)} data-testid="shortcuts"><Keyboard size={15} aria-hidden /></Button></Tip>
        <ThemeToggle />
      </header>
      {actions.startError && (
        <div style={{ padding: "8px 8px 0" }} data-testid="start-error">
          <Notice tone={actions.startError.error.status === 429 ? "warn" : "danger"} title="That could not be started">
            <div className="row-between">
              <span>{actions.startError.error.message} Your code is safe in the editor.</span>
              <span className="row"><Button size="small" onClick={actions.retry}>Try again</Button><Button size="small" variant="ghost" onClick={actions.dismissError}>Dismiss</Button></span>
            </div>
          </Notice>
        </div>
      )}
      {actions.pollError && actions.busy && (
        <div style={{ padding: "8px 8px 0" }} data-testid="reconnecting"><Notice tone="warn" title="Connection lost">Trying to reconnect. Your code is safe, and your result will appear when the connection returns.</Notice></div>
      )}
      <main className="ws-main" id="main">
        {wide ? (
          <PanelGroup direction="horizontal" autoSaveId="codepath.ws.3col">
            <Panel defaultSize={27} minSize={18} id="problem" order={1} {...collapse}>{sideTabs}</Panel>
            {handle}
            <Panel defaultSize={48} minSize={30} id="center" order={2}>
              <PanelGroup direction="vertical" autoSaveId="codepath.ws.center">
                <Panel defaultSize={58} minSize={22} id="editor" order={1}>{editorPane}</Panel>
                {handle}
                <Panel defaultSize={42} minSize={14} id="results" order={2}>{results}</Panel>
              </PanelGroup>
            </Panel>
            {handle}
            <Panel defaultSize={25} minSize={17} id="tutor" order={3}>{tutor}</Panel>
          </PanelGroup>
        ) : medium ? (
          <PanelGroup direction="horizontal" autoSaveId="codepath.ws.2col">
            <Panel defaultSize={40} minSize={24} id="side" order={1} {...collapse}>{sideTabs}</Panel>
            {handle}
            <Panel defaultSize={60} minSize={36} id="main-col" order={2}>
              <PanelGroup direction="vertical" autoSaveId="codepath.ws.2col.center">
                <Panel defaultSize={56} minSize={22} id="editor" order={1}>{editorPane}</Panel>
                {handle}
                <Panel defaultSize={44} minSize={14} id="results" order={2}>{results}</Panel>
              </PanelGroup>
            </Panel>
          </PanelGroup>
        ) : (
          <Tabs.Root value={mobileTab} onValueChange={setMobileTab} className="mobile-tabs">
            <Tabs.List className="tabs-list" aria-label="Workspace sections">
              <Tabs.Trigger className="tab" value="problem">Problem</Tabs.Trigger>
              <Tabs.Trigger className="tab" value="learn" data-testid="tab-learn">Learn</Tabs.Trigger>
              <Tabs.Trigger className="tab" value="code">Code</Tabs.Trigger>
              <Tabs.Trigger className="tab" value="results">Results</Tabs.Trigger>
              <Tabs.Trigger className="tab" value="tutor">Tutor{actions.response?.tutor ? " •" : ""}</Tabs.Trigger>
              <Tabs.Trigger className="tab" value="history">Submissions</Tabs.Trigger>
            </Tabs.List>
            {/* Panels stay mounted, so editor content and undo history survive tab changes. */}
            <Tabs.Content value="problem" forceMount hidden={mobileTab !== "problem"}>{problemPane}</Tabs.Content>
            <Tabs.Content value="learn" forceMount hidden={mobileTab !== "learn"}>{learnPane}</Tabs.Content>
            <Tabs.Content value="history" forceMount hidden={mobileTab !== "history"}>{historyPane}</Tabs.Content>
            <Tabs.Content value="code" forceMount hidden={mobileTab !== "code"}>{editorPane}</Tabs.Content>
            <Tabs.Content value="results" forceMount hidden={mobileTab !== "results"}>{results}</Tabs.Content>
            <Tabs.Content value="tutor" forceMount hidden={mobileTab !== "tutor"}>{tutor}</Tabs.Content>
          </Tabs.Root>
        )}
      </main>
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} mod={mod} />
    </div>
  );
}

export function WorkspacePage() {
  const { problemId = "" } = useParams();
  const query = useQuery<Workspace>({ queryKey: ["workspace", problemId], queryFn: () => api<Workspace>(`/problems/${problemId}/workspace`), staleTime: 5_000 });
  if (query.isLoading) return <div className="page"><PageLoading label="Loading the workspace" /></div>;
  if (query.isError || !query.data) return <div className="page"><ErrorState error={query.error} what="This problem" onRetry={() => void query.refetch()} /><div className="row" style={{ justifyContent: "center" }}><Link to="/problems" className="btn">Back to problems</Link></div></div>;
  // Remounting on a new problem guarantees one problem's code and results never appear on another.
  return <Loaded key={problemId} workspace={query.data} />;
}
