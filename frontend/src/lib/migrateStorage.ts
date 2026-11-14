/** The product was renamed. Move browser-saved drafts, timers, theme and layout to the new keys, so nobody loses work. */
const OLD_PREFIX = "trellis.";
const NEW_PREFIX = "codepath.";
const PANEL_PREFIX = "react-resizable-panels:";

export function migrateStorage(storage: Storage = window.localStorage): number {
  let moved = 0;
  try {
    const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index)).filter((key): key is string => key !== null);
    for (const key of keys) {
      let target: string | null = null;
      if (key.startsWith(OLD_PREFIX)) target = NEW_PREFIX + key.slice(OLD_PREFIX.length);
      else if (key.startsWith(PANEL_PREFIX + OLD_PREFIX)) target = PANEL_PREFIX + NEW_PREFIX + key.slice(PANEL_PREFIX.length + OLD_PREFIX.length);
      if (!target) continue;
      const value = storage.getItem(key);
      if (value !== null && storage.getItem(target) === null) storage.setItem(target, value);
      storage.removeItem(key);
      moved += 1;
    }
  } catch {
    /* Storage can be unavailable in private windows. There is nothing to move then. */
  }
  return moved;
}
