import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";

export type SaveState = "saved" | "saving" | "failed" | "idle";
type Stored = { code: string; at: number };

const storageKey = (userId: string, problemId: string) => `codepath.draft.${userId}.${problemId}.python`;

function readLocal(key: string): Stored | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Stored) : null;
  } catch {
    return null;
  }
}

/** The newest of the browser copy and the server copy wins. */
export function chooseInitial(local: Stored | null, server: { code: string; updated_at: string } | null | undefined, starter: string): { code: string; restored: boolean } {
  const serverAt = server ? new Date(server.updated_at).getTime() : 0;
  if (local && local.at >= serverAt) return { code: local.code, restored: local.code !== starter };
  if (server) return { code: server.code, restored: server.code !== starter };
  return { code: starter, restored: false };
}

export function loadInitialCode(userId: string, problemId: string, server: { code: string; updated_at: string } | null | undefined, starter: string) {
  return chooseInitial(readLocal(storageKey(userId, problemId)), server, starter);
}

/** Saves to the browser almost immediately and to the server after a pause. Keystroke content is never logged. */
export function useDraft(userId: string, problemId: string, serverDelayMs = 1500) {
  const [state, setState] = useState<SaveState>("idle");
  const key = storageKey(userId, problemId);
  const latest = useRef<string | null>(null);
  const timer = useRef<number>();
  const sequence = useRef(0);

  const pushToServer = useCallback(async () => {
    const code = latest.current;
    if (code === null) return;
    const mine = ++sequence.current;
    setState("saving");
    try {
      await api(`/problems/${problemId}/draft`, { method: "PUT", body: { code } });
      if (mine === sequence.current) setState("saved");
    } catch {
      if (mine === sequence.current) setState("failed"); // the browser copy is still safe
    }
  }, [problemId]);

  const onCodeChange = useCallback((code: string) => {
    latest.current = code;
    try {
      localStorage.setItem(key, JSON.stringify({ code, at: Date.now() } satisfies Stored));
    } catch {
      /* Private windows can refuse storage. The server copy still applies. */
    }
    setState("saving");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void pushToServer(), serverDelayMs);
  }, [key, pushToServer, serverDelayMs]);

  const saveNow = useCallback(() => {
    window.clearTimeout(timer.current);
    if (latest.current !== null) void pushToServer();
    else setState("saved");
  }, [pushToServer]);

  const clear = useCallback(async () => {
    window.clearTimeout(timer.current);
    latest.current = null;
    sequence.current++;
    try {
      localStorage.removeItem(key);
    } catch {
      /* nothing to do */
    }
    setState("idle");
    await api(`/problems/${problemId}/draft`, { method: "DELETE" }).catch(() => undefined);
  }, [key, problemId]);

  // Flush a pending save when leaving the page.
  useEffect(() => {
    const flush = () => {
      if (latest.current !== null && state === "saving") {
        void fetch(`/api/problems/${problemId}/draft`, { method: "PUT", keepalive: true, credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: latest.current }) });
      }
    };
    window.addEventListener("pagehide", flush);
    return () => { window.removeEventListener("pagehide", flush); };
  }, [problemId, state]);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  return { state, onCodeChange, saveNow, clear, retry: pushToServer };
}

/** Counts time only while the page is visible and the learner has interacted in the last minute. */
export function useActiveSeconds(userId: string, problemId: string, serverSeconds: number) {
  const key = `codepath.active.${userId}.${problemId}`;
  const value = useRef(serverSeconds);
  const lastInteraction = useRef(Date.now());
  useEffect(() => {
    try {
      value.current = Math.max(serverSeconds, Number(localStorage.getItem(key) ?? 0));
    } catch {
      value.current = serverSeconds;
    }
    const mark = () => { lastInteraction.current = Date.now(); };
    window.addEventListener("keydown", mark);
    window.addEventListener("pointerdown", mark);
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible" && Date.now() - lastInteraction.current < 60_000) {
        value.current += 5;
        try {
          localStorage.setItem(key, String(value.current));
        } catch {
          /* best effort */
        }
      }
    }, 5000);
    return () => { window.clearInterval(interval); window.removeEventListener("keydown", mark); window.removeEventListener("pointerdown", mark); };
  }, [key, serverSeconds]);
  return value;
}
