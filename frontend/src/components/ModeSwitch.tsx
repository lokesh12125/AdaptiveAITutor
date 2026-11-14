import type { LearningMode } from "@/api/types";
import { useSession } from "@/lib/session";

export const MODES: { id: LearningMode; label: string; detail: string }[] = [
  { id: "guided", label: "Guided", detail: "More explanation and support. Hints can appear after a failed attempt." },
  { id: "practice", label: "Practice", detail: "Guidance stays closed, and hints wait until you ask for them." },
  { id: "revision", label: "Revision", detail: "Concise notes, key patterns and common mistakes come first." },
  { id: "interview", label: "Interview prep", detail: "Constraints, complexity, patterns and edge cases come first." },
];

export function useLearningMode(): [LearningMode, (mode: LearningMode) => void] {
  const { preferences, updatePreferences } = useSession();
  return [preferences.learning_mode ?? "guided", (mode) => void updatePreferences({ learning_mode: mode })];
}

/** How much support to show. It changes what is shown first and what the tutor offers unprompted. A request for help is always answered. */
export function ModeSwitch({ showDetail = true }: { showDetail?: boolean }) {
  const [mode, setMode] = useLearningMode();
  const current = MODES.find((item) => item.id === mode) ?? MODES[0];
  return (
    <div className="stack-s" style={{ gap: 4 }}>
      <div className="mode-switch" role="radiogroup" aria-label="Learning mode" data-testid="mode-switch">
        {MODES.map((item) => (
          <button key={item.id} type="button" role="radio" aria-checked={mode === item.id} className="mode-option" onClick={() => setMode(item.id)} data-testid={`mode-${item.id}`}>{item.label}</button>
        ))}
      </div>
      {showDetail && <p className="subtle" data-testid="mode-detail">{current.detail}</p>}
    </div>
  );
}
