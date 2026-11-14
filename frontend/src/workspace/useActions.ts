import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, api, newKey } from "@/api/client";
import type { Evaluation, Run, TutorResponse, Workspace } from "@/api/types";

export type ActionKind = "run" | "submit" | "hint";
const TERMINAL_EVAL = new Set(["completed", "failed", "cancelled"]);
const TERMINAL_RUN = new Set(["completed", "failed"]);

export type HintOptions = { request_size?: "nudge" | "more"; question?: string; self_state?: "stuck" | "overwhelmed"; focus_start?: number; focus_end?: number };
type SelfReport = { self_confidence?: "low" | "medium" | "high" };
type Pending = { kind: ActionKind; code: string; key: string; body: Record<string, unknown> };

/**
 * Run, Submit and Hint. Results are tied to an id and to the exact code they checked.
 * Only the newest request's result is displayed, so a slow older response cannot replace a newer one.
 * Retrying after a connection failure reuses the same key, so it cannot create a duplicate attempt.
 */
export function useActions(problemId: string, workspace: Workspace | undefined, getActiveSeconds: () => number) {
  const client = useQueryClient();
  const [evaluationId, setEvaluationId] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState<ActionKind | null>(null);
  const [startError, setStartError] = useState<{ pending: Pending; error: ApiError } | null>(null);
  const [focus, setFocus] = useState<"evaluation" | "run" | null>(null);
  const seeded = useRef(false);

  useEffect(() => {
    if (!workspace || seeded.current) return;
    seeded.current = true;
    setEvaluationId(workspace.latest_evaluation?.id ?? null);
    setRunId(workspace.latest_run?.id ?? null);
    const evalAt = workspace.latest_evaluation ? new Date(workspace.latest_evaluation.created_at).getTime() : 0;
    const runAt = workspace.latest_run ? new Date(workspace.latest_run.created_at).getTime() : 0;
    if (evalAt || runAt) setFocus(evalAt > runAt ? "evaluation" : "run");
  }, [workspace]);

  const evaluationQuery = useQuery<Evaluation>({
    queryKey: ["evaluation", evaluationId], enabled: !!evaluationId, queryFn: () => api<Evaluation>(`/evaluations/${evaluationId}`),
    refetchInterval: (q) => (q.state.data && TERMINAL_EVAL.has(q.state.data.status) ? false : 350), retry: 3,
  });
  const runQuery = useQuery<Run>({
    queryKey: ["run", runId], enabled: !!runId, queryFn: () => api<Run>(`/runs/${runId}`),
    refetchInterval: (q) => (q.state.data && TERMINAL_RUN.has(q.state.data.status) ? false : 350), retry: 3,
  });

  const evaluation = evaluationQuery.data ?? null;
  const run = runQuery.data ?? null;
  const evaluationBusy = !!evaluationId && (!evaluation || !TERMINAL_EVAL.has(evaluation.status));
  const runBusy = !!runId && (!run || !TERMINAL_RUN.has(run.status));

  // When a learning cycle finishes, anything showing progress should refresh.
  const finishedRun = run && TERMINAL_RUN.has(run.status) ? run.id : null;
  useEffect(() => {
    if (!finishedRun) return;
    for (const key of ["home", "progress", "path", "problems", "unit", "submissions", "profile"]) void client.invalidateQueries({ queryKey: [key] });
    void client.invalidateQueries({ queryKey: ["workspace", problemId] });
  }, [finishedRun, client, problemId]);

  const send = useCallback(async (pending: Pending) => {
    setStarting(pending.kind);
    setStartError(null);
    const path = pending.kind === "run" ? "run" : pending.kind === "submit" ? "submit" : "hint";
    try {
      const accepted = await api<{ id: string }>(`/problems/${problemId}/${path}`, { method: "POST", body: { code: pending.code, idempotency_key: pending.key, ...pending.body } });
      if (pending.kind === "run") {
        setEvaluationId(accepted.id);
        setFocus("evaluation");
      } else {
        setRunId(accepted.id);
        setFocus("run");
      }
    } catch (error) {
      setStartError({ pending, error: error instanceof ApiError ? error : new ApiError(0, "unknown", "That could not be started. Your code is safe.") });
    } finally {
      setStarting(null);
    }
  }, [problemId]);

  const start = useCallback((kind: ActionKind, code: string, options: HintOptions & SelfReport & { custom_args?: string; custom_stdin?: string; cases?: { test_id?: string; args?: string[]; stdin?: string }[] } = {}) => {
    const body: Record<string, unknown> = { ...options };
    if (kind !== "run") body.active_seconds = getActiveSeconds();
    void send({ kind, code, key: newKey(), body });
  }, [getActiveSeconds, send]);

  const retry = useCallback(() => { if (startError) void send(startError.pending); }, [send, startError]);
  const dismissError = useCallback(() => setStartError(null), []);

  const cancel = useCallback(async () => {
    if (evaluationBusy && evaluationId) await api(`/evaluations/${evaluationId}/cancel`, { method: "POST" }).catch(() => undefined);
    else if (runBusy && runId) await api(`/runs/${runId}/cancel`, { method: "POST" }).catch(() => undefined);
  }, [evaluationBusy, evaluationId, runBusy, runId]);

  return {
    evaluation, run, response: (run?.response ?? null) as TutorResponse | null, focus, setFocus, start, cancel, retry, dismissError, startError, starting, evaluationBusy, runBusy,
    busy: evaluationBusy || runBusy || !!starting,
    pollError: (evaluationQuery.isError ? evaluationQuery.error : runQuery.isError ? runQuery.error : null) as Error | null,
  };
}
