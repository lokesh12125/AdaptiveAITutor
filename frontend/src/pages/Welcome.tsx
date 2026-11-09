import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { User } from "@/api/types";
import { LogoMark, ThemeToggle } from "@/components/Shell";
import { Button, errorText, Field, Notice } from "@/components/ui";
import { useSession } from "@/lib/session";

const RUNGS = [
  ["L1", "A question that gets you thinking"],
  ["L2", "A hint pointing at the issue"],
  ["L3", "A step-by-step outline"],
  ["L4", "A worked example on a different problem"],
];

export function Welcome() {
  const { user, setUser, status } = useSession();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [invite, setInvite] = useState("");
  const after = (next: User) => { setUser(next); navigate(next.role === "teacher" ? "/teacher" : next.onboarding_completed ? "/" : "/onboarding"); };
  const auth = useMutation({
    mutationFn: () => mode === "signin"
      ? api<User>("/auth/login", { method: "POST", body: { email, password } })
      : api<User>("/auth/register", { method: "POST", body: { name, email, password, role, invite_code: role === "teacher" ? invite : undefined } }),
    onSuccess: after,
  });
  const demo = useMutation({ mutationFn: (demoRole: "student" | "teacher") => api<User>("/auth/demo", { method: "POST", body: { role: demoRole } }), onSuccess: after });

  if (user) return <Navigate to={user.role === "teacher" ? "/teacher" : "/"} replace />;
  return (
    <div className="welcome">
      <section className="welcome-story">
        <div className="row-between">
          <span className="logo"><LogoMark /> Trellis</span>
          <ThemeToggle />
        </div>
        <div className="stack">
          <h1 style={{ fontSize: "clamp(1.8rem, 1.4rem + 2vw, 2.6rem)", maxWidth: "18ch" }}>Learn Python with just enough help.</h1>
          <p className="muted prose" style={{ fontSize: "1.05rem" }}>Trellis watches how your attempts go, then gives the smallest hint that keeps you moving. It will not write the answer for you, so what you learn stays with you.</p>
        </div>
        <div className="ladder" aria-label="The four levels of help">
          {RUNGS.map(([level, text]) => <div className="ladder-rung" key={level}><b>{level}</b><span>{text}</span></div>)}
        </div>
        <p className="subtle prose">Beginner or preparing for coding interviews, you use the same workspace. You can also bring in a question from anywhere.</p>
      </section>
      <main className="welcome-form" id="main">
        <div className="stack-s">
          <h2>{mode === "signin" ? "Sign in" : "Create your account"}</h2>
          <p className="muted">{mode === "signin" ? "Pick up where you left off." : "Your progress is saved to your account."}</p>
        </div>
        {auth.isError && <Notice tone="danger">{errorText(auth.error)}</Notice>}
        <form className="stack" onSubmit={(event) => { event.preventDefault(); auth.mutate(); }}>
          {mode === "register" && <Field label="Your name">{(p) => <input {...p} className="input" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={80} autoComplete="name" />}</Field>}
          <Field label="Email">{(p) => <input {...p} className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />}</Field>
          <Field label="Password" help={mode === "register" ? "At least 8 characters." : undefined}>{(p) => <input {...p} className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "register" ? 8 : 1} autoComplete={mode === "register" ? "new-password" : "current-password"} />}</Field>
          {mode === "register" && (
            <fieldset className="row" style={{ border: "none", padding: 0, margin: 0 }}>
              <legend className="field-label" style={{ padding: 0, marginBottom: 4 }}>I am a</legend>
              <label className="row" style={{ gap: 5 }}><input type="radio" name="role" checked={role === "student"} onChange={() => setRole("student")} /> Learner</label>
              <label className="row" style={{ gap: 5 }}><input type="radio" name="role" checked={role === "teacher"} onChange={() => setRole("teacher")} /> Teacher</label>
            </fieldset>
          )}
          {mode === "register" && role === "teacher" && <Field label="Teacher invite code" help="Provided by whoever runs this server.">{(p) => <input {...p} className="input" value={invite} onChange={(e) => setInvite(e.target.value)} required />}</Field>}
          <Button type="submit" variant="primary" block disabled={auth.isPending}>{auth.isPending ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}</Button>
        </form>
        <p className="muted">
          {mode === "signin" ? "New here? " : "Already have an account? "}
          <button type="button" className="btn-link" onClick={() => { setMode(mode === "signin" ? "register" : "signin"); auth.reset(); }}>{mode === "signin" ? "Create an account" : "Sign in"}</button>
        </p>
        {status?.demo_mode && (
          <div className="stack-s" style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <strong className="row" style={{ gap: 6 }}><Sparkles size={15} aria-hidden /> Just looking?</strong>
            <p className="subtle">Demo access needs no password. It is <strong>not a secure account</strong>: it is temporary, and it is for trying things out only. The teacher demo shows a class of synthetic learners.</p>
            {demo.isError && <Notice tone="danger">{errorText(demo.error)}</Notice>}
            <div className="row">
              <Button onClick={() => demo.mutate("student")} disabled={demo.isPending} data-testid="demo-student">Try as a learner</Button>
              <Button onClick={() => demo.mutate("teacher")} disabled={demo.isPending} data-testid="demo-teacher">Try as a teacher</Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
