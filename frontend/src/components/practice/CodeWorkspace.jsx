import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Code2, 
  Timer, 
  Play, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Lightbulb, 
  BrainCircuit, 
  Sparkles, 
  Copy, 
  Check, 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle,
  HelpCircle,
  Eye
} from 'lucide-react';

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
  const outputSectionRef = useRef(null);
  const [hintsUnlocked, setHintsUnlocked] = useState([]);
  const [hintLoading, setHintLoading] = useState(false);
  const [showHintPanel, setShowHintPanel] = useState(false);
  const [copiedId, setCopiedId] = useState('');

  // Reset progressive hints when problem changes
  useEffect(() => {
    setHintsUnlocked([]);
    setShowHintPanel(false);
  }, [problem?.id]);

  // PHASE 4: Automatic smooth scrolling to results whenever execution finishes or starts
  useEffect(() => {
    if (runResult || submitResult || runLoading || submitLoading) {
      const timer = setTimeout(() => {
        if (outputSectionRef.current) {
          outputSectionRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'nearest' 
          });
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [runResult, submitResult, runLoading, submitLoading]);

  const formatActiveTime = (secs) => {
    if (!secs) return '0s';
    if (secs < 60) return `${secs}s`;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  };

  const copyToClipboard = (text, id) => {
    try {
      navigator.clipboard?.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(''), 2000);
    } catch (e) {
      console.warn('Copy failed', e);
    }
  };

  // PHASE 3.3: Fetch progressive hints (Levels 1-4)
  const fetchProgressiveHint = async (level) => {
    if (!problem || hintLoading) return;
    if (level === 4) {
      const confirmWalkthrough = window.confirm(
        'Would you like to unlock the complete solution walkthrough?\n(We recommend trying with Hint 1-3 first!)'
      );
      if (!confirmWalkthrough) return;
    }

    setHintLoading(true);
    try {
      const token = localStorage.getItem('adaptive_tutor_token');
      const userStr = localStorage.getItem('adaptive_tutor_user');
      const user = userStr ? JSON.parse(userStr) : null;
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

      const res = await fetch(`${API_BASE}/api/hint/progressive`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          learner_id: user?.id || 'demo-student',
          problem_id: problem.id,
          level: level,
          code: code || ''
        })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setHintsUnlocked(prev => {
          const filtered = prev.filter(h => h.level !== level);
          return [...filtered, data].sort((a, b) => a.level - b.level);
        });
        setShowHintPanel(true);
      }
    } catch (err) {
      console.warn('Failed to fetch progressive hint:', err);
    } finally {
      setHintLoading(false);
    }
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

      {/* PHASE 3.3: Progressive Hint Ladder Bar */}
      <div className="progressive-hints-bar">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Lightbulb size={18} color="#0d9488" />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#0f766e' }}>Progressive Socratic Hints:</span>
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button
              className={`hint-tier-btn ${hintsUnlocked.some(h => h.level === 1) ? 'unlocked' : ''}`}
              onClick={() => fetchProgressiveHint(1)}
              disabled={hintLoading}
              title="Unlock a gentle conceptual nudge"
            >
              Hint 1: Nudge
            </button>
            <button
              className={`hint-tier-btn ${hintsUnlocked.some(h => h.level === 2) ? 'unlocked' : ''}`}
              onClick={() => fetchProgressiveHint(2)}
              disabled={hintLoading}
              title="Unlock specific direction and constraints"
            >
              Hint 2: Direction
            </button>
            <button
              className={`hint-tier-btn ${hintsUnlocked.some(h => h.level === 3) ? 'unlocked' : ''}`}
              onClick={() => fetchProgressiveHint(3)}
              disabled={hintLoading}
              title="Unlock pseudocode and structural approach"
            >
              Hint 3: Pseudocode
            </button>
            <button
              className={`hint-tier-btn walkthrough ${hintsUnlocked.some(h => h.level === 4) ? 'unlocked' : ''}`}
              onClick={() => fetchProgressiveHint(4)}
              disabled={hintLoading}
              title="Unlock full solution explanation walkthrough"
            >
              <Eye size={13} style={{ marginRight: 4 }} /> Walkthrough
            </button>
            {hintsUnlocked.length > 0 && (
              <button
                className="btn-toggle-hints"
                onClick={() => setShowHintPanel(!showHintPanel)}
                title={showHintPanel ? "Collapse hints" : "Expand hints"}
              >
                {showHintPanel ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            )}
          </div>
        </div>

        {/* Unlocked Hints Panel */}
        {showHintPanel && hintsUnlocked.length > 0 && (
          <div className="hints-unlocked-container">
            {hintsUnlocked.map(h => (
              <div key={h.level} className={`hint-unlocked-card level-${h.level}`}>
                <div className="hint-unlocked-header">
                  <span style={{ fontWeight: 700, fontSize: 12 }}>{h.title}</span>
                  <button
                    className="btn-copy-small"
                    onClick={() => copyToClipboard(h.hint, `hint-${h.level}`)}
                    title="Copy hint to clipboard"
                  >
                    {copiedId === `hint-${h.level}` ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                    <span>{copiedId === `hint-${h.level}` ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <div className="hint-unlocked-body">
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.5 }}>
                    {h.hint}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Monaco Code Editor Container */}
      <div className="editor-container">
        <div className="editor-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Code2 size={16} color="#38bdf8" />
            <span>solution.py</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button 
              className="btn-copy-small" 
              style={{ color: '#94a3b8', border: '1px solid #334155', background: '#1e293b' }}
              onClick={() => copyToClipboard(code, 'editor-code')}
              title="Copy code"
            >
              {copiedId === 'editor-code' ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
              <span>{copiedId === 'editor-code' ? 'Copied' : 'Copy Code'}</span>
            </button>
            <div className="timer-tag">
              <Timer size={15} />
              <span>Active Time: {formatActiveTime(activeSeconds)}</span>
            </div>
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
          <button 
            className="btn-secondary" 
            style={{ width: 'auto', padding: '10px 18px', display: 'flex', alignItems: 'center', gap: 8, background: '#f1f5f9', color: '#1e293b', border: '1px solid #cbd5e1', borderRadius: 6, fontWeight: 700, cursor: (runLoading || submitLoading) ? 'not-allowed' : 'pointer' }}
            onClick={handleRunCode} 
            disabled={runLoading || submitLoading}
          >
            {runLoading ? <RefreshCw size={16} className="spin" color="#0d9488" /> : <Play size={16} color="#0d9488" />}
            <span>{runLoading ? 'Running Code...' : 'Run Code'}</span>
          </button>

          <button 
            className="btn-primary" 
            style={{ width: 'auto', padding: '10px 20px' }}
            onClick={handleSubmitCode} 
            disabled={runLoading || submitLoading}
          >
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

      {/* PHASE 4: SCROLL TARGET ANCHOR & OUTPUT SECTION */}
      <div ref={outputSectionRef} id="execution-output-section" style={{ scrollMarginTop: '85px' }}>
        
        {/* Loading In-Progress Card: Run Code */}
        {runLoading && (
          <div className="agent-card running" style={{ marginTop: 16, borderLeft: '4px solid #0284c7' }}>
            <div className="agent-card-header">
              <RefreshCw size={18} className="spin" color="#0284c7" />
              <span>Executing in Isolated Python Sandbox...</span>
            </div>
            <div className="agent-card-body" style={{ color: '#475569', fontSize: 13 }}>
              Evaluating test assertions against resource-limited sandbox (CPU, Memory, AST filter, 3.0s timeout)...
            </div>
          </div>
        )}

        {/* Loading In-Progress Card: Submit Solution */}
        {submitLoading && (
          <div className="agent-card running" style={{ marginTop: 16, borderLeft: '4px solid #0d9488' }}>
            <div className="agent-card-header">
              <RefreshCw size={18} className="spin" color="#0d9488" />
              <span>LangGraph 6-Agent Pipeline Reasoning...</span>
            </div>
            <div className="agent-card-body" style={{ color: '#475569', fontSize: 13 }}>
              Evaluating solution against test assertions, tracking BKT concept mastery, updating continuous cognitive load indicators, querying peer archetypes in ChromaDB, and applying cyclic anti-leak verifiers...
            </div>
          </div>
        )}

        {/* Run Code Output Section */}
        {runResult && !submitResult && !runLoading && (
          <div className={`agent-card ${runResult.passed ? 'passed' : 'failed'}`} style={{ marginTop: 16 }}>
            <div className="agent-card-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {runResult.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
                <span>Execution Output • {runResult.passed ? 'All Assertions Passed' : (runResult.error_type || 'Execution Failed').toUpperCase()}</span>
              </div>
              <button
                className="btn-copy-small"
                onClick={() => copyToClipboard(runResult.output, 'run-output')}
                title="Copy output"
              >
                {copiedId === 'run-output' ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                <span>{copiedId === 'run-output' ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="agent-card-body">
              <div className={`status-pill ${runResult.passed ? 'success' : 'danger'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 8, padding: '4px 10px', borderRadius: 4, fontSize: 12, fontWeight: 700 }}>
                {runResult.passed ? '✓ SUCCESS' : `✗ ${runResult.error_type ? runResult.error_type.toUpperCase() : 'FAILED'}`}
              </div>
              <pre style={{ margin: 0, padding: 12, background: '#1e293b', color: '#f8fafc', borderRadius: 6, whiteSpace: 'pre-wrap', fontFamily: 'Fira Code, monospace', fontSize: 13, lineHeight: 1.5 }}>
                {runResult.output}
              </pre>
            </div>
          </div>
        )}

        {/* Multi-Agent Full Feedback Cards on Submission */}
        {submitResult && !submitLoading && (
          <div className="feedback-grid" style={{ marginTop: 16 }}>
            {/* Card 1: Diagnostic Agent */}
            <div className={`agent-card ${submitResult.execution?.passed ? 'passed' : 'failed'}`}>
              <div className="agent-card-header" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {submitResult.execution?.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
                  <span>Diagnostic Agent • {submitResult.execution?.passed ? 'Verified Solution' : submitResult.diagnostic?.error_type}</span>
                </div>
                <button
                  className="btn-copy-small"
                  onClick={() => copyToClipboard(submitResult.diagnostic?.explanation || submitResult.execution?.output, 'diag-text')}
                  title="Copy diagnostic feedback"
                >
                  {copiedId === 'diag-text' ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                </button>
              </div>
              <div className="agent-card-body">
                <strong>{submitResult.execution?.output}</strong>
                <p style={{ marginTop: 6, color: '#475569' }}>{submitResult.diagnostic?.explanation}</p>
                {!submitResult.execution?.passed && (
                  <>
                    <div style={{ marginTop: 8, fontSize: 12, color: '#b91c1c', background: '#fef2f2', padding: '8px 10px', borderRadius: 6, border: '1px solid #fecaca' }}>
                      <strong>Misconception:</strong> {submitResult.diagnostic?.misconception}
                    </div>
                    <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                      <button 
                        className="btn-primary" 
                        style={{ padding: '6px 14px', fontSize: 12, width: 'auto' }} 
                        onClick={() => {
                          setSubmitResult(null);
                          setRunResult(null);
                          setActiveSeconds(0);
                          setIsTimerRunning(true);
                        }}
                      >
                        Try Again
                      </button>
                      <button 
                        className="btn-secondary" 
                        style={{ padding: '6px 14px', fontSize: 12, background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' }} 
                        onClick={() => {
                          setCode(problem?.starter_code || '');
                          setSubmitResult(null);
                          setRunResult(null);
                          setActiveSeconds(0);
                          setIsTimerRunning(true);
                        }}
                      >
                        Reset Starter Code
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
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {submitResult.scaffolding?.focus && submitResult.scaffolding?.focus !== 'None' && (
                    <span style={{ fontSize: 11, background: 'rgba(13, 148, 136, 0.15)', color: '#0d9488', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
                      {submitResult.scaffolding.focus} Focus
                    </span>
                  )}
                  <button
                    className="btn-copy-small"
                    onClick={() => copyToClipboard(submitResult.scaffolding?.hint || '', 'scaff-text')}
                    title="Copy scaffolding hint"
                  >
                    {copiedId === 'scaff-text' ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>
              <div className="agent-card-body">
                <p style={{ margin: 0, fontWeight: 600, color: '#0f172a' }}>
                  {submitResult.scaffolding?.hint || 'Review your code structure and logic.'}
                </p>
                {submitResult.scaffolding?.rationale && (
                  <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    <strong>Pedagogical Rationale:</strong> {submitResult.scaffolding.rationale}
                  </div>
                )}
                {submitResult.scaffolding?.remediation_flag && (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#b45309', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '8px 10px', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertTriangle size={15} color="#b45309" />
                    <span><strong>Remediation Advisory:</strong> High cognitive struggle detected across multiple attempts. Consider reviewing foundational concepts.</span>
                  </div>
                )}
                {submitResult.scaffolding?.intervention_applied && (
                  <div style={{ marginTop: 8, fontSize: 11, color: '#0284c7', background: 'rgba(2, 132, 199, 0.1)', padding: '4px 8px', borderRadius: 4 }}>
                    ChromaDB Peer Strategy: {submitResult.scaffolding.intervention_applied}
                  </div>
                )}
              </div>
            </div>

            {/* Card 3: Metacognitive Reflection Agent */}
            <div className="agent-card reflection" style={{ gridColumn: 'span 2' }}>
              <div className="agent-card-header" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BrainCircuit size={18} color="#6366f1" />
                  <span>Reflection Agent • Metacognitive Reasoning</span>
                </div>
              </div>
              <div className="agent-card-body">
                <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#312e81' }}>{submitResult.reflection}</p>
                <div style={{ marginTop: 12 }}>
                  <textarea
                    id="reflection-answer-input"
                    placeholder="Reflect on your thought process: explain your invariant, Big-O reasoning, or why your logic behaved this way..."
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 6,
                      border: '1px solid #cbd5e1',
                      fontSize: 13,
                      fontFamily: 'inherit',
                      minHeight: 60,
                      resize: 'vertical',
                      boxSizing: 'border-box'
                    }}
                  />
                  <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                    <button
                      className="btn-primary"
                      style={{ padding: '7px 16px', fontSize: 12, background: '#6366f1', width: 'auto' }}
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
                    <span style={{ fontSize: 11, color: '#10b981', fontWeight: 700 }}>
                      {submitResult.recommendation.difficulty.toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="agent-card-body">
                  <p style={{ margin: 0, fontWeight: 600, color: '#064e3b' }}>
                    {submitResult.recommendation.reason}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
