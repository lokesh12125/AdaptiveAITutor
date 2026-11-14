import { describe, expect, it } from "vitest";

import { fromEditable } from "@/pages/AddQuestion";
import { chooseInitial } from "@/workspace/useDraft";

import { duration, percent, roundedRange, timeAgo } from "./format";
import { migrateStorage } from "./migrateStorage";
import { withTheme } from "./theme";

describe("draft restoration", () => {
  const starter = "def f():\n    pass\n";
  const at = (ms: number) => new Date(ms).toISOString();

  it("uses the starter when nothing is saved", () => {
    expect(chooseInitial(null, null, starter)).toEqual({ code: starter, restored: false });
  });
  it("prefers the newer browser copy", () => {
    expect(chooseInitial({ code: "local", at: 2000 }, { code: "server", updated_at: at(1000) }, starter)).toEqual({ code: "local", restored: true });
  });
  it("prefers the newer server copy", () => {
    expect(chooseInitial({ code: "local", at: 1000 }, { code: "server", updated_at: at(2000) }, starter)).toEqual({ code: "server", restored: true });
  });
  it("does not claim to restore unchanged starter code", () => {
    expect(chooseInitial({ code: starter, at: 2000 }, null, starter).restored).toBe(false);
  });
});

describe("test editor conversion", () => {
  const row = (overrides: object) => ({ localId: "a", kind: "args", origin: "learner", compare: "exact", enabled: true, needs_expected: false, argsText: "[1, 2]", expectedText: "3", label: "T", ...overrides }) as never;

  it("parses JSON arguments and answers", () => {
    const { tests, errors } = fromEditable([row({})]);
    expect(errors).toEqual({});
    expect(tests[0].args).toEqual([1, 2]);
    expect(tests[0].expected).toBe(3);
    expect(tests[0].enabled).toBe(true);
  });
  it("reports invalid arguments instead of guessing", () => {
    expect(fromEditable([row({ argsText: "1, 2" })]).errors.a).toContain("JSON list");
  });
  it("reports invalid expected output", () => {
    expect(fromEditable([row({ expectedText: "not json" })]).errors.a).toContain("JSON");
  });
  it("keeps a test off until it has an expected output", () => {
    const { tests } = fromEditable([row({ expectedText: "" })]);
    expect(tests[0].needs_expected).toBe(true);
    expect(tests[0].enabled).toBe(false);
  });
  it("allows completion-only tests without an answer", () => {
    const { tests } = fromEditable([row({ expectedText: "", compare: "completes" })]);
    expect(tests[0].needs_expected).toBe(false);
    expect(tests[0].enabled).toBe(true);
  });
  it("treats standard input as plain text", () => {
    const { tests, errors } = fromEditable([row({ kind: "stdio", argsText: "3 4\n", expectedText: "7\n" })]);
    expect(errors).toEqual({});
    expect(tests[0].stdin).toBe("3 4\n");
    expect(tests[0].expected).toBe("7\n");
    expect(tests[0].args).toBeNull();
  });
});

describe("display formatting", () => {
  it("rounds estimates to avoid implying false precision", () => {
    expect(roundedRange(0.327, 0.781)).toBe("35–80%");
    expect(roundedRange(null, 0.5)).toBe("");
  });
  it("says when there is no data", () => {
    expect(percent(null)).toBe("No data yet");
    expect(duration(null)).toBe("No data yet");
    expect(percent(0.5)).toBe("50%");
  });
  it("formats durations", () => {
    expect(duration(45)).toBe("45 sec");
    expect(duration(120)).toBe("2 min");
    expect(duration(7200)).toBe("2.0 hr");
  });
  it("formats relative time", () => {
    expect(timeAgo(null)).toBe("never");
    expect(timeAgo(new Date().toISOString())).toBe("just now");
  });
});

describe("moving saved data to the new product name", () => {
  const memory = (entries: Record<string, string>) => {
    const data = new Map(Object.entries(entries));
    return {
      get length() { return data.size; }, key: (index: number) => [...data.keys()][index] ?? null, getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => { data.set(key, value); }, removeItem: (key: string) => { data.delete(key); }, clear: () => data.clear(), data,
    };
  };

  it("moves drafts, theme and panel layout", () => {
    const store = memory({ "trellis.draft.u.p.python": "d", "trellis.theme": "dark", "react-resizable-panels:trellis.ws.3col": "l", unrelated: "keep" });
    expect(migrateStorage(store as unknown as Storage)).toBe(3);
    expect(Object.fromEntries(store.data)).toEqual({ "codepath.draft.u.p.python": "d", "codepath.theme": "dark", "react-resizable-panels:codepath.ws.3col": "l", unrelated: "keep" });
  });
  it("never overwrites newer data under the new name", () => {
    const store = memory({ "trellis.theme": "dark", "codepath.theme": "light" });
    migrateStorage(store as unknown as Storage);
    expect(Object.fromEntries(store.data)).toEqual({ "codepath.theme": "light" });
  });
  it("copes with storage that refuses access", () => {
    expect(migrateStorage({ get length(): number { throw new Error("denied"); } } as unknown as Storage)).toBe(0);
  });
});

describe("links that open in a new tab carry the theme", () => {
  it("adds the theme to the query, before any section", () => {
    expect(withTheme("/path/loops?tab=lesson", "dark")).toBe("/path/loops?tab=lesson&theme=dark");
    expect(withTheme("/path/loops?tab=lesson#for-loops", "dark")).toBe("/path/loops?tab=lesson&theme=dark#for-loops");
    expect(withTheme("/path/loops", "light")).toBe("/path/loops?theme=light");
  });
});
