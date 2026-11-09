import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { Assessment } from "@/api/types";
import { Button, errorText, ErrorState, Notice, PageLoading } from "@/components/ui";

export function AssessmentPage() {
  const { phase = "pre" } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const query = useQuery<Assessment>({ queryKey: ["assessment", phase], queryFn: () => api<Assessment>(`/assessments/${phase}`) });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const submit = useMutation({
    mutationFn: () => api<Assessment>(`/assessments/${phase}`, { method: "POST", body: { answers } }),
    onSuccess: () => { for (const key of ["assessment", "progress", "home", "path"]) void client.invalidateQueries({ queryKey: [key] }); },
  });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="This check" onRetry={() => void query.refetch()} />;
  const data = submit.data ?? query.data;
  if (data.completed) {
    return (
      <div className="stack">
        <h1>{data.title}: done</h1>
        <p>You answered <strong>{data.score} of {data.max_score}</strong> correctly.</p>
        <p className="muted prose">{phase === "pre" ? "This gives the tutor a starting point. It carries little weight, so your coding work soon matters more." : "See your measured improvement on your progress page."}</p>
        <div className="row"><Link className="btn btn-primary" to="/">Go to home</Link><Link className="btn" to="/progress">See your progress</Link></div>
      </div>
    );
  }
  const questions = data.questions as { id: string; prompt: string; code?: string | null; options: string[] }[];
  return (
    <form className="stack-l" onSubmit={(event) => { event.preventDefault(); submit.mutate(); }}>
      <div className="stack-s"><h1>{data.title}</h1><p className="muted prose">{data.note}</p></div>
      {submit.isError && <Notice tone="danger">{errorText(submit.error)}</Notice>}
      {questions.map((question, index) => (
        <fieldset key={question.id} className="card stack-s" style={{ margin: 0 }}>
          <legend className="sr-only">Question {index + 1}</legend>
          <strong>{index + 1}. {question.prompt}</strong>
          {question.code && <pre className="console"><code>{question.code}</code></pre>}
          {question.options.map((option) => (
            <label key={option} className="row" style={{ gap: 8, cursor: "pointer" }}>
              <input type="radio" name={question.id} checked={answers[question.id] === option} onChange={() => setAnswers({ ...answers, [question.id]: option })} /> <code style={{ background: "none", padding: 0, fontFamily: "inherit" }}>{option}</code>
            </label>
          ))}
        </fieldset>
      ))}
      <div className="row">
        <Button variant="primary" type="submit" disabled={submit.isPending} data-testid="submit-check">Finish</Button>
        <Button variant="ghost" onClick={() => navigate("/")}>Not now</Button>
      </div>
    </form>
  );
}
