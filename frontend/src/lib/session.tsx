import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";

import { ApiError, api, setSessionLostHandler } from "@/api/client";
import type { Preferences, Status, User } from "@/api/types";

type Session = { user: User | null; loading: boolean; refresh: () => Promise<void>; setUser: (user: User | null) => void; preferences: Preferences; updatePreferences: (patch: Preferences) => Promise<void>; status: Status | undefined };
const Context = createContext<Session | null>(null);
const THEME_KEY = "trellis.theme";

function resolveTheme(choice: Preferences["theme"]): "light" | "dark" {
  if (choice === "light" || choice === "dark") return choice;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Theme choice is kept in the browser too, so it applies before sign-in and before first paint. */
export function applyAppearance(preferences: Preferences): void {
  const root = document.documentElement;
  let choice = preferences.theme;
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (!choice && (saved === "light" || saved === "dark")) choice = saved;
    if (preferences.theme === "system") localStorage.removeItem(THEME_KEY);
    else if (preferences.theme) localStorage.setItem(THEME_KEY, preferences.theme);
  } catch {
    /* Storage can be unavailable in private windows. The theme still applies for this page. */
  }
  root.dataset.theme = resolveTheme(choice);
  root.dataset.density = preferences.density === "compact" ? "compact" : "comfortable";
  root.dataset.motion = preferences.motion === "reduced" ? "reduced" : "system";
  root.style.setProperty("--editor-font-size", `${preferences.editor_font_size ?? 14}px`);
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const me = useQuery<User | null>({
    queryKey: ["me"], staleTime: 60_000, retry: false,
    queryFn: async () => {
      try {
        return await api<User>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
  });
  const status = useQuery<Status>({ queryKey: ["status"], queryFn: () => api<Status>("/status"), staleTime: 30_000, refetchInterval: 60_000, retry: false });
  const setUser = useCallback((user: User | null) => client.setQueryData(["me"], user), [client]);
  useEffect(() => setSessionLostHandler(() => client.setQueryData(["me"], null)), [client]);

  const user = me.data ?? null;
  const preferences = useMemo(() => (user?.preferences ?? {}) as Preferences, [user]);
  useEffect(() => applyAppearance(preferences), [preferences]);
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const follow = () => applyAppearance((client.getQueryData<User | null>(["me"])?.preferences ?? {}) as Preferences);
    media?.addEventListener?.("change", follow);
    return () => media?.removeEventListener?.("change", follow);
  }, [client]);

  const updatePreferences = useCallback(async (patch: Preferences) => {
    const current = client.getQueryData<User | null>(["me"]);
    if (!current) {
      applyAppearance(patch);
      return;
    }
    client.setQueryData(["me"], { ...current, preferences: { ...current.preferences, ...patch } });
    applyAppearance({ ...current.preferences, ...patch } as Preferences);
    const updated = await api<User>("/me/preferences", { method: "PUT", body: { preferences: patch } });
    client.setQueryData(["me"], updated);
  }, [client]);

  const value = useMemo<Session>(() => ({
    user, loading: me.isLoading, refresh: async () => { await me.refetch(); }, setUser, preferences, updatePreferences, status: status.data,
  }), [user, me, setUser, preferences, updatePreferences, status.data]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useSession(): Session {
  const value = useContext(Context);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
