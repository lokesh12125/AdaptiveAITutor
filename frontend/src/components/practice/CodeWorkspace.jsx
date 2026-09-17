import React from 'react';
import Editor from '@monaco-editor/react';
import { Code2, Timer, Play, RefreshCw, CheckCircle2, XCircle, Lightbulb, BrainCircuit } from 'lucide-react';

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
            <span>Active Time: {activeSeconds}s</span>
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
            <div className="agent-card-header">
              <Lightbulb size={18} color="#0d9488" />
              <span>Adaptive Scaffolding Agent • Level {submitResult.scaffolding?.level || 1}</span>
            </div>
            <div className="agent-card-body">
              <p style={{ margin: 0, fontWeight: 600 }}>{submitResult.scaffolding?.hint}</p>
              {submitResult.scaffolding?.intervention_applied && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#0369a1', background: '#f0f9ff', padding: '4px 8px', borderRadius: 4 }}>
                  ChromaDB Intervention: {submitResult.scaffolding.intervention_applied}
                </div>
              )}
            </div>
          </div>

          {/* Card 3: Reflection Agent */}
          <div className="agent-card reflection" style={{ gridColumn: 'span 2' }}>
            <div className="agent-card-header">
              <BrainCircuit size={18} color="#6366f1" />
              <span>Reflection Agent</span>
            </div>
            <div className="agent-card-body">
              <p style={{ margin: 0, fontSize: 14, color: '#1e293b' }}>{submitResult.reflection}</p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
