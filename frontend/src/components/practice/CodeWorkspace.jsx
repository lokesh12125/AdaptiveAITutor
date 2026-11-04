import React from 'react';
import Editor from '@monaco-editor/react';
import { Code2, Timer, Play, RefreshCw, CheckCircle2, XCircle, Lightbulb, BrainCircuit, Sparkles } from 'lucide-react';

export default function CodeWorkspace({
  problem,
  code,
  setCode,
  activeSeconds,
  setActiveSeconds,
  setIsTimerRunning,
  runLoading,
  submitLoading,
  handleRunCode,
  handleSubmitCode,
  runResult,
  setRunResult,
  submitResult,
  setSubmitResult
}) {
  const formatActiveTime = (secs) => {
    if (!secs) return '0s';
    if (secs < 60) return `${secs}s`;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  };

  return (
    <section className="workspace-center">
      {problem && (
        <div className="problem-header-card">
          <div className="problem-header-top">
            <div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                <span className="pill source">{problem.source || 'builtin'}</span>
                <span className={`pill ${problem.difficulty}`}>{problem.difficulty}</span>
                <span style={{ fontSize: 12, color: '#64748b' }}>Topic: {problem.topic}</span>
              </div>
              <h1>{problem.title}</h1>
              <p>{problem.description}</p>
            </div>
          </div>
          {problem.expected_behavior && (
            <div className="expected-box">
              <strong>Expected: </strong>{problem.expected_behavior}
            </div>
          )}
        </div>
      )}

      {/* Monaco Code Editor */}
      <div className="editor-container">
        <div className="editor-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Code2 size={16} color="#38bdf8" />
            <span>solution.py</span>
          </div>
          <div className="timer-tag">
            <Timer size={15} />
            <span>Active Time: {formatActiveTime(activeSeconds)}</span>
          </div>
        </div>

        <Editor
          height="340px"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onChange={val => {
            setCode(val || '');
            setSubmitResult(null);
            setRunResult(null);
            if (setIsTimerRunning) {
              setIsTimerRunning(true);
            }
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            tabSize: 4,
            automaticLayout: true
          }}
        />

        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn-primary" onClick={handleRunCode} disabled={runLoading || submitLoading}>
            {runLoading ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
            <span>Run Code</span>
          </button>
          <button className="btn-primary" onClick={handleSubmitCode} disabled={runLoading || submitLoading}>
            {submitLoading ? (
              <>
                <RefreshCw size={16} className="spin" />
                <span>LangGraph Agents Evaluating...</span>
              </>
            ) : (
              <>
                <CheckCircle2 size={16} />
                <span>Submit Solution</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Run Feedback */}
      {runResult && !submitResult && (
        <div className={`agent-card ${runResult.passed ? 'passed' : 'failed'}`} style={{ marginTop: 16 }}>
          <div className="agent-card-header">
            {runResult.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
            <span>Execution Output</span>
          </div>
          <div className="agent-card-body">
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'Fira Code, monospace', fontSize: 13 }}>{runResult.output}</pre>
          </div>
        </div>
      )}

      {/* Multi-Agent Feedback Cards */}
      {submitResult && (
        <div className="feedback-grid">
          {/* Card 1: Execution & Diagnostic Agent */}
          <div className={`agent-card ${submitResult.execution?.passed ? 'passed' : 'failed'}`}>
            <div className="agent-card-header">
              {submitResult.execution?.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
              <span>Diagnostic Agent • {submitResult.execution?.passed ? 'Verified Solution' : submitResult.diagnostic?.error_type}</span>
            </div>
            <div className="agent-card-body">
              <strong>{submitResult.execution?.output}</strong>
              <p style={{ marginTop: 6, color: '#475569' }}>{submitResult.diagnostic?.explanation}</p>
              {!submitResult.execution?.passed && (
                <>
                  <div style={{ marginTop: 8, fontSize: 12, color: '#b91c1c', background: '#fef2f2', padding: '6px 10px', borderRadius: 4 }}>
                    Misconception: {submitResult.diagnostic?.misconception}
                  </div>
                  <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                    <button className="btn-primary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => {
                      setSubmitResult(null);
                      setRunResult(null);
                      setActiveSeconds(0);
                      setIsTimerRunning(true);
                    }}>
                      Try Again
                    </button>
                    <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: 12, background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: 6, fontWeight: 500, cursor: 'pointer' }} onClick={() => {
                      setCode(problem?.starter_code || '');
                      setSubmitResult(null);
                      setRunResult(null);
                      setActiveSeconds(0);
                      setIsTimerRunning(true);
                    }}>
                      Rewrite
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Card 2: Adaptive Scaffolding Agent */}
          <div className="agent-card scaffolding">
            <div className="agent-card-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Lightbulb size={18} color="#0d9488" />
                <span>
                  Adaptive Scaffolding • {submitResult.scaffolding?.level === 0 ? 'Mastery Confirmed' : `Level ${submitResult.scaffolding?.level || 1}`}
                </span>
              </div>
              {submitResult.scaffolding?.focus && submitResult.scaffolding?.focus !== 'None' && (
                <span style={{ fontSize: 11, background: 'rgba(13, 148, 136, 0.15)', color: '#0d9488', padding: '2px 8px', borderRadius: 4, textTransform: 'none', fontWeight: 600 }}>
                  {submitResult.scaffolding.focus} Focus
                </span>
              )}
            </div>
            <div className="agent-card-body">
              <p style={{ margin: 0, fontWeight: 600 }}>
                {submitResult.scaffolding?.hint || 'Review your code structure and logic.'}
              </p>
              {submitResult.scaffolding?.rationale && (
                <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                  Pedagogical Rationale: {submitResult.scaffolding.rationale}
                </div>
              )}
              {submitResult.scaffolding?.remediation_flag && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#b45309', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '6px 10px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>⚠️</span>
                  <span><strong>Remediation Advisory:</strong> High cognitive struggle detected across multiple attempts. Consider reviewing prerequisite concepts.</span>
                </div>
              )}
              {submitResult.scaffolding?.intervention_applied && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#0284c7', background: 'rgba(2, 132, 199, 0.1)', padding: '4px 8px', borderRadius: 4 }}>
                  ChromaDB Peer Strategy: {submitResult.scaffolding.intervention_applied}
                </div>
              )}
            </div>
          </div>

          {/* Card 3: Reflection Agent (R-25: Metacognitive Loop Closure) */}
          <div className="agent-card reflection" style={{ gridColumn: 'span 2' }}>
            <div className="agent-card-header">
              <BrainCircuit size={18} color="#6366f1" />
              <span>Reflection Agent • Metacognitive Reasoning</span>
            </div>
            <div className="agent-card-body">
              <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>{submitResult.reflection}</p>
              <div style={{ marginTop: 12 }}>
                <textarea
                  id="reflection-answer-input"
                  placeholder="Explain your reasoning here in 1-2 sentences..."
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 6,
                    border: '1px solid #cbd5e1',
                    fontSize: 13,
                    fontFamily: 'inherit',
                    minHeight: 55,
                    resize: 'vertical',
                    boxSizing: 'border-box'
                  }}
                />
                <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <button
                    className="btn-primary"
                    style={{ padding: '6px 14px', fontSize: 12, background: '#6366f1' }}
                    onClick={async (e) => {
                      const input = document.getElementById('reflection-answer-input');
                      const val = input ? input.value.trim() : '';
                      if (!val) return;
                      const btn = e.currentTarget;
                      btn.disabled = true;
                      btn.textContent = 'Saving...';
                      try {
                        const token = localStorage.getItem('adaptive_tutor_token');
                        const userStr = localStorage.getItem('adaptive_tutor_user');
                        const user = userStr ? JSON.parse(userStr) : null;
                        const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
                        const API = `${API_BASE}/api`;
                        await fetch(`${API}/reflection/submit`, {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                          },
                          body: JSON.stringify({
                            learner_id: user?.id || 'demo-student',
                            problem_id: problem?.id || 1,
                            prompt_text: submitResult.reflection || '',
                            response_text: val
                          })
                        });
                        btn.textContent = '✓ Saved Insight';
                        btn.style.background = '#10b981';
                        if (input) input.disabled = true;
                      } catch {
                        btn.textContent = '✓ Recorded';
                      }
                    }}
                  >
                    Submit Reflection
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Card 4: Learning Planner Recommendation */}
          {submitResult.recommendation && submitResult.recommendation.reason && (
            <div className="agent-card" style={{ gridColumn: 'span 2', borderLeft: '4px solid #10b981', background: 'rgba(16, 185, 129, 0.05)' }}>
              <div className="agent-card-header" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Sparkles size={18} color="#10b981" />
                  <span>Learning Planner Agent • Next Step Recommendation</span>
                </div>
                {submitResult.recommendation.difficulty && (
                  <span style={{ fontSize: 11, color: '#10b981', fontWeight: 600 }}>
                    {submitResult.recommendation.difficulty.toUpperCase()}
                  </span>
                )}
              </div>
              <div className="agent-card-body">
                <p style={{ margin: 0, fontWeight: 500 }}>
                  {submitResult.recommendation.reason}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
