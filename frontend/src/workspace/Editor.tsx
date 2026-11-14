import { autocompletion, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { python } from "@codemirror/lang-python";
import { bracketMatching, HighlightStyle, indentOnInput, indentUnit, syntaxHighlighting, syntaxTree } from "@codemirror/language";
import { linter, type Diagnostic } from "@codemirror/lint";
import { highlightSelectionMatches, openSearchPanel, search, searchKeymap } from "@codemirror/search";
import { Compartment, EditorState, Prec, StateEffect, StateField } from "@codemirror/state";
import { Decoration, type DecorationSet, drawSelection, EditorView, highlightActiveLine, highlightActiveLineGutter, keymap, lineNumbers } from "@codemirror/view";
import { tags } from "@lezer/highlight";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export const highlight = HighlightStyle.define([
  { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword, tags.moduleKeyword, tags.operatorKeyword, tags.bool, tags.null, tags.self], class: "tok-keyword" },
  { tag: [tags.string, tags.special(tags.string)], class: "tok-string" },
  { tag: [tags.number, tags.integer, tags.float], class: "tok-number" },
  { tag: [tags.comment, tags.lineComment], class: "tok-comment" },
  { tag: [tags.function(tags.definition(tags.variableName)), tags.definition(tags.className)], class: "tok-def" },
  { tag: [tags.function(tags.variableName), tags.standard(tags.variableName)], class: "tok-builtin" },
  { tag: tags.invalid, class: "tok-invalid" },
]);

const setMarkedLines = StateEffect.define<number[]>();
const lineMark = Decoration.line({ class: "cm-diagnostic-line" });
const markedLines = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(value, transaction) {
    let next = value.map(transaction.changes);
    for (const effect of transaction.effects) {
      if (effect.is(setMarkedLines)) {
        const lines = effect.value.filter((n) => n >= 1 && n <= transaction.state.doc.lines).sort((a, b) => a - b);
        next = Decoration.set(lines.map((n) => lineMark.range(transaction.state.doc.line(n).from)));
      }
    }
    return next;
  },
  provide: (field) => EditorView.decorations.from(field),
});

/** Light feedback from the local parser only. Nothing is executed or sent to the server while typing. */
const pythonSyntaxLint = linter((view) => {
  const found: Diagnostic[] = [];
  syntaxTree(view.state).iterate({
    enter(node) {
      if (node.type.isError && found.length < 3) {
        found.push({ from: node.from, to: Math.min(node.to + 1, view.state.doc.length), severity: "info", message: "Python may not be able to read this part yet." });
      }
    },
  });
  return found;
}, { delay: 1400 });

export type EditorHandle = { setCode: (code: string) => void; focus: () => void; openFind: () => void };
type Props = {
  initialCode: string; onChange: (code: string) => void; onRun: () => void; onSubmit: () => void; onHint: () => void; onSave: () => void; onEscape: () => void;
  tabSize: number; lineWrap: boolean; showLineNumbers: boolean; syntaxFeedback: boolean; markedLines: number[];
  /** The lines the learner has selected, or null when nothing is selected. */
  onSelectionChange?: (lines: { start: number; end: number } | null) => void;
};

export const CodeEditor = forwardRef<EditorHandle, Props>(function CodeEditor(props, ref) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const callbacks = useRef(props);
  callbacks.current = props;
  const wrapping = useRef(new Compartment());
  const numbers = useRef(new Compartment());
  const tabs = useRef(new Compartment());
  const lint = useRef(new Compartment());

  useEffect(() => {
    if (!host.current) return;
    const instance = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: props.initialCode,
        extensions: [
          Prec.highest(keymap.of([
            { key: "Mod-Enter", run: () => { callbacks.current.onRun(); return true; } },
            { key: "Mod-Shift-Enter", run: () => { callbacks.current.onSubmit(); return true; } },
            { key: "Alt-h", run: () => { callbacks.current.onHint(); return true; } },
            { key: "Mod-s", run: () => { callbacks.current.onSave(); return true; }, preventDefault: true },
            { key: "Escape", run: () => { callbacks.current.onEscape(); return true; } },
          ])),
          numbers.current.of(props.showLineNumbers ? lineNumbers() : []),
          highlightActiveLineGutter(), highlightActiveLine(), drawSelection(), history(), indentOnInput(), bracketMatching(), closeBrackets(), autocompletion({ activateOnTyping: false }),
          search({ top: true }), highlightSelectionMatches(), python(), syntaxHighlighting(highlight), markedLines,
          tabs.current.of([EditorState.tabSize.of(props.tabSize), indentUnit.of(" ".repeat(props.tabSize))]),
          wrapping.current.of(props.lineWrap ? EditorView.lineWrapping : []),
          lint.current.of(props.syntaxFeedback ? pythonSyntaxLint : []),
          keymap.of([...closeBracketsKeymap, ...defaultKeymap, ...searchKeymap, ...historyKeymap, indentWithTab]),
          EditorView.contentAttributes.of({ "aria-label": "Python code editor. Press Escape, then Tab, to leave the editor.", spellcheck: "false", autocapitalize: "off", autocorrect: "off" }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) callbacks.current.onChange(update.state.doc.toString());
            if (update.selectionSet || update.docChanged) {
              const { from, to, empty } = update.state.selection.main;
              if (empty) { callbacks.current.onSelectionChange?.(null); return; }
              const first = update.state.doc.lineAt(from);
              const last = update.state.doc.lineAt(to);
              // A selection that ends at the very start of a line does not include that line.
              const end = last.from === to && last.number > first.number ? last.number - 1 : last.number;
              callbacks.current.onSelectionChange?.({ start: first.number, end });
            }
          }),
        ],
      }),
    });
    view.current = instance;
    return () => { instance.destroy(); view.current = null; };
    // The editor instance lives for the life of this component. Settings change through compartments below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { view.current?.dispatch({ effects: wrapping.current.reconfigure(props.lineWrap ? EditorView.lineWrapping : []) }); }, [props.lineWrap]);
  useEffect(() => { view.current?.dispatch({ effects: numbers.current.reconfigure(props.showLineNumbers ? lineNumbers() : []) }); }, [props.showLineNumbers]);
  useEffect(() => { view.current?.dispatch({ effects: tabs.current.reconfigure([EditorState.tabSize.of(props.tabSize), indentUnit.of(" ".repeat(props.tabSize))]) }); }, [props.tabSize]);
  useEffect(() => { view.current?.dispatch({ effects: lint.current.reconfigure(props.syntaxFeedback ? pythonSyntaxLint : []) }); }, [props.syntaxFeedback]);
  const marked = props.markedLines.join(",");
  useEffect(() => { view.current?.dispatch({ effects: setMarkedLines.of(props.markedLines) }); }, [marked]); // eslint-disable-line react-hooks/exhaustive-deps

  useImperativeHandle(ref, () => ({
    setCode(code: string) {
      const current = view.current;
      if (current) current.dispatch({ changes: { from: 0, to: current.state.doc.length, insert: code } });
    },
    focus() { view.current?.focus(); },
    openFind() { if (view.current) { view.current.focus(); openSearchPanel(view.current); } },
  }), []);

  return <div className="editor-host" ref={host} data-testid="code-editor" />;
});
