import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Download, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { ClassInfo, Preferences, User } from "@/api/types";
import { Button, errorText, Field, Modal, Notice, Select, Toggle, useToast } from "@/components/ui";
import { useSession } from "@/lib/session";

function Row({ title, help, control }: { title: string; help?: string; control: React.ReactNode }) {
  return <div className="setting-row"><div><div style={{ fontWeight: 550 }}>{title}</div>{help && <div className="subtle">{help}</div>}</div><div style={{ flex: "none", minWidth: 0 }}>{control}</div></div>;
}

function Classes() {
  const client = useQueryClient();
  const toast = useToast();
  const [code, setCode] = useState("");
  const classes = useQuery<ClassInfo[]>({ queryKey: ["my-classes"], queryFn: () => api<ClassInfo[]>("/me/classes") });
  const join = useMutation({ mutationFn: () => api<ClassInfo>("/me/classes", { method: "POST", body: { join_code: code } }), onSuccess: (joined) => { setCode(""); toast({ tone: "ok", title: `You joined ${joined.name}` }); void client.invalidateQueries({ queryKey: ["my-classes"] }); } });
  const leave = useMutation({ mutationFn: (id: string) => api(`/me/classes/${id}`, { method: "DELETE" }), onSuccess: () => void client.invalidateQueries({ queryKey: ["my-classes"] }) });
  return (
    <section className="card stack-s" aria-labelledby="class-heading">
      <h2 id="class-heading">Class</h2>
      <p className="subtle">Joining lets that teacher see your progress, hints and attempts. They cannot see anything until you join, and you can leave at any time.</p>
      {classes.data?.map((item) => <div className="row-between" key={item.id}><span>{item.name}</span><Button size="small" onClick={() => leave.mutate(item.id)}>Leave</Button></div>)}
      <form className="row" style={{ alignItems: "flex-end" }} onSubmit={(event) => { event.preventDefault(); join.mutate(); }}>
        <div className="grow"><Field label="Join code">{(p) => <input {...p} className="input mono" value={code} onChange={(e) => setCode(e.target.value)} data-testid="join-code-input" />}</Field></div>
        <Button type="submit" disabled={code.trim().length < 4 || join.isPending} data-testid="join-class">Join class</Button>
      </form>
      {join.isError && <Notice tone="danger">{errorText(join.error)}</Notice>}
    </section>
  );
}

export function SettingsPage() {
  const { user, preferences, updatePreferences, setUser, status } = useSession();
  const navigate = useNavigate();
  const client = useQueryClient();
  const toast = useToast();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState("");
  const set = (patch: Preferences) => updatePreferences(patch).catch((error) => toast({ tone: "error", title: "That setting could not be saved", detail: errorText(error) }));
  const onboarding = useMutation({
    mutationFn: (patch: { experience_level: string; goal: string }) => api<User>("/auth/onboarding", { method: "POST", body: { ...patch, research_consent: user?.research_consent ?? false } }),
    onSuccess: (updated) => { setUser(updated); toast({ tone: "ok", title: "Your starting point is updated" }); void client.invalidateQueries({ queryKey: ["home"] }); void client.invalidateQueries({ queryKey: ["path"] }); },
  });
  const consent = useMutation({
    mutationFn: (value: boolean) => api<User>("/auth/onboarding", { method: "POST", body: { experience_level: user?.experience_level ?? "some", goal: user?.goal ?? "explore", research_consent: value } }),
    onSuccess: (updated) => setUser(updated),
  });
  const exportData = async () => {
    try {
      const data = await api("/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "trellis-my-data.json";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast({ tone: "error", title: "Your data could not be exported", detail: errorText(error) });
    }
  };
  const remove = useMutation({
    mutationFn: () => api("/me/delete", { method: "POST", body: { password } }),
    onSuccess: () => { setUser(null); client.clear(); navigate("/welcome"); },
  });
  const student = user?.role === "student";
  const execution = status?.execution;
  const model = status?.tutor_model;
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}><div><h1>Settings</h1><p>Changes save automatically.</p></div></div>
      <section className="card" aria-labelledby="look-heading">
        <h2 id="look-heading">Appearance</h2>
        <Row title="Theme" control={<div style={{ width: 150 }}><Select label="Theme" value={preferences.theme ?? "system"} onChange={(value) => void set({ theme: value as Preferences["theme"] })} options={[{ value: "system", label: "Match system" }, { value: "light", label: "Light" }, { value: "dark", label: "Dark" }]} /></div>} />
        <Row title="Layout density" help="Compact fits more on screen." control={<div style={{ width: 150 }}><Select label="Layout density" value={preferences.density ?? "comfortable"} onChange={(value) => void set({ density: value as Preferences["density"] })} options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]} /></div>} />
        <Row title="Reduce motion" help="Turns off animations. Your device's own setting is always respected." control={<Toggle checked={preferences.motion === "reduced"} onChange={(value) => void set({ motion: value ? "reduced" : "system" })} label="Reduce motion" />} />
      </section>
      <section className="card" aria-labelledby="editor-heading">
        <h2 id="editor-heading">Code editor</h2>
        <Row title="Font size" control={<div className="row" style={{ gap: 6 }}><Button size="small" aria-label="Smaller code text" onClick={() => void set({ editor_font_size: Math.max(11, (preferences.editor_font_size ?? 14) - 1) })}>−</Button><span data-testid="font-size" style={{ minWidth: 40, textAlign: "center" }}>{preferences.editor_font_size ?? 14}px</span><Button size="small" aria-label="Larger code text" onClick={() => void set({ editor_font_size: Math.min(24, (preferences.editor_font_size ?? 14) + 1) })}>+</Button></div>} />
        <Row title="Indent size" control={<div style={{ width: 120 }}><Select label="Indent size" value={String(preferences.editor_tab_size ?? 4)} onChange={(value) => void set({ editor_tab_size: Number(value) })} options={[{ value: "2", label: "2 spaces" }, { value: "4", label: "4 spaces" }]} /></div>} />
        <Row title="Line numbers" control={<Toggle checked={preferences.editor_line_numbers ?? true} onChange={(value) => void set({ editor_line_numbers: value })} label="Line numbers" />} />
        <Row title="Wrap long lines" control={<Toggle checked={preferences.editor_line_wrap ?? false} onChange={(value) => void set({ editor_line_wrap: value })} label="Wrap long lines" />} />
        <Row title="Light syntax feedback" help="Marks code Python may not be able to read, in your browser, with nothing sent or run." control={<Toggle checked={preferences.syntax_feedback ?? true} onChange={(value) => void set({ syntax_feedback: value })} label="Light syntax feedback" />} />
      </section>
      {student && (
        <section className="card" aria-labelledby="tutor-heading">
          <h2 id="tutor-heading">Tutor</h2>
          <Row title="Show hints automatically" help="When this is off, the tutor only offers help after a failed submission, and waits for you to ask." control={<Toggle checked={preferences.auto_hints ?? true} onChange={(value) => void set({ auto_hints: value })} label="Show hints automatically" />} />
          <Row title="Show walkthroughs" help="Short explanations for people new to the workspace." control={<Toggle checked={preferences.show_walkthroughs ?? true} onChange={(value) => void set({ show_walkthroughs: value })} label="Show walkthroughs" />} />
          <Row title="Show the tutor's working estimates" help="Confusion, workload and progress estimates. The tutor still uses them when they are hidden." control={<Toggle checked={preferences.show_estimates ?? true} onChange={(value) => void set({ show_estimates: value })} label="Show working estimates" />} />
          <Row title="Experience" help="Only a starting point. Recommendations also follow your work." control={<div style={{ width: 170 }}><Select label="Experience" value={user?.experience_level ?? "some"} onChange={(value) => onboarding.mutate({ experience_level: value, goal: user?.goal ?? "explore" })} options={[{ value: "new", label: "Brand new" }, { value: "some", label: "Some basics" }, { value: "intermediate", label: "Comfortable" }, { value: "advanced", label: "Experienced" }]} /></div>} />
          <Row title="Goal" control={<div style={{ width: 170 }}><Select label="Goal" value={user?.goal ?? "explore"} onChange={(value) => onboarding.mutate({ experience_level: user?.experience_level ?? "some", goal: value })} options={[{ value: "basics", label: "Learn the basics" }, { value: "course", label: "Keep up with a course" }, { value: "dsa", label: "Data structures and algorithms" }, { value: "explore", label: "Just explore" }]} /></div>} />
        </section>
      )}
      {student && <Classes />}
      <section className="card" aria-labelledby="privacy-heading">
        <h2 id="privacy-heading">Privacy and your data</h2>
        <p className="subtle" style={{ marginTop: 4 }}>Stored about you: your account, code you run or submit, drafts, results, hints, estimates, and answers you give. Not stored: individual keystrokes. Time is counted only while the page is visible and you are active.</p>
        {student && <Row title="Let anonymous hint outcomes help other learners" help="Saves which kind of hint helped in which kind of situation, with no name, code or problem text." control={<Toggle checked={preferences.share_anonymous_outcomes ?? true} onChange={(value) => void set({ share_anonymous_outcomes: value })} label="Share anonymous hint outcomes" />} />}
        {student && <Row title="Allow use in research results" help="Includes your anonymised activity in this project's research analysis." control={<Toggle checked={user?.research_consent ?? false} onChange={(value) => consent.mutate(value)} label="Allow use in research" />} />}
        <Row title="Download my data" help="Everything stored about your account, as a JSON file." control={<Button onClick={() => void exportData()} data-testid="export-data"><Download size={15} aria-hidden /> Download</Button>} />
        {!user?.email.includes("demo-teacher") && <Row title="Delete my account" help="Permanently removes your account, code and history. Anonymous pooled outcomes cannot be traced to you, so they remain." control={<Button onClick={() => setDeleteOpen(true)} data-testid="delete-account">Delete account</Button>} />}
      </section>
      <section className="card stack-s" aria-labelledby="about-heading">
        <h2 id="about-heading">About this server</h2>
        <div className="row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
          {execution?.available && execution.secure ? <CircleCheck size={16} aria-hidden style={{ color: "var(--ok)", flex: "none", marginTop: 3 }} /> : <ShieldAlert size={16} aria-hidden style={{ color: "var(--warn)", flex: "none", marginTop: 3 }} />}
          <div><strong>Code execution:</strong> {execution?.available ? String(execution.label) : "Unavailable"}{execution?.note ? <span className="subtle"> {String(execution.note)}</span> : null}</div>
        </div>
        <p><strong>Tutor wording:</strong> {model?.enabled ? `AI model (${String(model.provider)}), with built-in hints as a fallback.` : "Built-in hints. No AI model is configured on this server."} <span className="subtle">How much help you get is always decided by rules, not by the model.</span></p>
        <p><strong>Languages:</strong> Python. Others are planned only after this is stable.</p>
      </section>
      <Modal open={deleteOpen} onOpenChange={setDeleteOpen} title="Delete your account?">
        <form className="stack" onSubmit={(event) => { event.preventDefault(); remove.mutate(); }}>
          <p className="muted">This permanently removes your account, code and history. It cannot be undone. You may want to download your data first.</p>
          {!user?.is_demo && <Field label="Your password">{(p) => <input {...p} className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />}</Field>}
          {remove.isError && <Notice tone="danger">{errorText(remove.error)}</Notice>}
          <div className="dialog-actions"><Button onClick={() => setDeleteOpen(false)}>Keep my account</Button><Button type="submit" variant="danger" disabled={remove.isPending} data-testid="confirm-delete">Delete permanently</Button></div>
        </form>
      </Modal>
    </div>
  );
}
