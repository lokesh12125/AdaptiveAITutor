import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { User } from "@/api/types";
import { Logo, SystemBanners } from "@/components/Shell";
import { Button, errorText, Notice, Toggle } from "@/components/ui";
import { useSession } from "@/lib/session";

const LEVELS = [
  { value: "new", title: "I'm brand new", detail: "Never written code, or only a little." },
  { value: "some", title: "I know some basics", detail: "Variables and loops feel familiar." },
  { value: "intermediate", title: "I'm comfortable with Python", detail: "Functions and lists are fine. I want to improve." },
  { value: "advanced", title: "I'm experienced", detail: "Skip the introductions and let me get to harder problems." },
] as const;
const GOALS = [
  { value: "basics", title: "Learn programming from the start" },
  { value: "course", title: "Keep up with a course" },
  { value: "dsa", title: "Practise data structures and algorithms" },
  { value: "explore", title: "Just explore" },
] as const;

export function Onboarding() {
  const { setUser } = useSession();
  const navigate = useNavigate();
  const [level, setLevel] = useState<(typeof LEVELS)[number]["value"]>("new");
  const [goal, setGoal] = useState<(typeof GOALS)[number]["value"]>("basics");
  const [consent, setConsent] = useState(false);
  const save = useMutation({
    mutationFn: (skip: boolean) => api<User>("/auth/onboarding", { method: "POST", body: { experience_level: level, goal, research_consent: consent, skip_walkthroughs: skip } }),
  });
  const finish = async (destination: string, skip = false) => {
    const user = await save.mutateAsync(skip);
    setUser(user);
    navigate(destination);
  };
  return (
    <div className="app">
      <SystemBanners />
      <header className="topbar"><Logo /></header>
      <main className="page page-narrow stack-l" id="main">
        <div className="stack-s">
          <h1>Welcome. Where shall we start?</h1>
          <p className="muted prose">This just sets your starting point. It is not a label: your recommendations change as you work, and you can change these any time in Settings.</p>
        </div>
        {save.isError && <Notice tone="danger">{errorText(save.error)}</Notice>}
        <fieldset className="stack-s" style={{ border: "none", padding: 0, margin: 0 }}>
          <legend><h2 style={{ marginBottom: 10 }}>How much Python have you written?</h2></legend>
          <div className="grid-2" role="radiogroup">
            {LEVELS.map((item) => (
              <button key={item.value} type="button" className="choice" role="radio" aria-checked={level === item.value} onClick={() => setLevel(item.value)} data-testid={`level-${item.value}`}>
                <span><strong>{item.title}</strong><br /><span className="subtle">{item.detail}</span></span>
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="stack-s" style={{ border: "none", padding: 0, margin: 0 }}>
          <legend><h2 style={{ marginBottom: 10 }}>What brings you here?</h2></legend>
          <div className="grid-2" role="radiogroup">
            {GOALS.map((item) => (
              <button key={item.value} type="button" className="choice" role="radio" aria-checked={goal === item.value} onClick={() => setGoal(item.value)} data-testid={`goal-${item.value}`}><strong>{item.title}</strong></button>
            ))}
          </div>
        </fieldset>
        <section className="card stack-s">
          <div className="setting-row" style={{ padding: 0 }}>
            <div>
              <strong>Help improve this project</strong>
              <p className="subtle">Optional. Allows your anonymised activity to be included in this student project's research results. You can still use everything if this is off.</p>
            </div>
            <Toggle checked={consent} onChange={setConsent} label="Allow anonymised activity to be used in research" />
          </div>
        </section>
        <section className="stack-s">
          <div className="row">
            <Button variant="primary" onClick={() => void finish("/", level === "advanced")} disabled={save.isPending} data-testid="finish-onboarding">Start learning</Button>
            {level !== "advanced" && <Button onClick={() => void finish("/check/pre")} disabled={save.isPending} data-testid="take-check">Take a 2-minute starting check first</Button>}
            <Button variant="ghost" onClick={() => void finish("/", true)} disabled={save.isPending} data-testid="skip-intro">Skip introductions</Button>
          </div>
          <p className="subtle">The starting check is optional. It gives a better starting point, and it lets you measure your improvement later. <Link to="/settings">Settings</Link> lets you change everything here.</p>
        </section>
      </main>
    </div>
  );
}
