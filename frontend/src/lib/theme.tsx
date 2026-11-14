import { useSyncExternalStore } from "react";
import { Link, type LinkProps } from "react-router-dom";

export type Theme = "light" | "dark";

const current = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

/** The theme on screen now. It updates when the learner switches theme, wherever that happens. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, current, () => "light");
}

/** Adds the theme to a link, before any #section. index.html applies it before the first paint, saves it, and removes it from the address. */
export function withTheme(to: string, theme: Theme): string {
  const at = to.indexOf("#");
  const path = at === -1 ? to : to.slice(0, at);
  const hash = at === -1 ? "" : to.slice(at);
  return `${path}${path.includes("?") ? "&" : "?"}theme=${theme}${hash}`;
}

/**
 * A link to another CodePath page that opens in a new tab or window. It carries the theme on screen, so the page
 * there opens in the same mode from its first frame, even when the desktop app opens it in a browser that has not
 * saved this tab's theme.
 */
export function NewTabLink({ to, ...rest }: Omit<LinkProps, "to" | "target" | "rel"> & { to: string }) {
  const theme = useTheme();
  return <Link to={withTheme(to, theme)} target="_blank" rel="noreferrer" {...rest} />;
}
