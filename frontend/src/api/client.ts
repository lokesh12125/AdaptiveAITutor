/** Thin typed fetch wrapper. Sessions use an HttpOnly cookie, so nothing sensitive is stored in the browser. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
    public correlationId?: string,
  ) {
    super(message);
  }
  /** The request never reached the server, or the server failed: not the learner's fault. */
  get isConnectivity(): boolean {
    return this.status === 0 || this.status >= 500;
  }
}

let onSessionLost: (() => void) | null = null;
export function setSessionLostHandler(handler: () => void): void {
  onSessionLost = handler;
}

export async function api<T>(path: string, options: { method?: string; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      signal: options.signal,
      headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network", "We could not reach the server. Check your connection and try again.");
  }
  if (response.status === 204) return undefined as T;
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = (payload as { error?: { code: string; message: string; details?: unknown }; correlation_id?: string } | null)?.error;
    if (response.status === 401 && error?.code !== "bad_credentials") onSessionLost?.();
    throw new ApiError(
      response.status,
      error?.code ?? "unknown",
      error?.message ?? "Something went wrong on our side. Your work is safe. Please try again.",
      error?.details,
      (payload as { correlation_id?: string } | null)?.correlation_id,
    );
  }
  return payload as T;
}

export function newKey(): string {
  return (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g, "");
}
