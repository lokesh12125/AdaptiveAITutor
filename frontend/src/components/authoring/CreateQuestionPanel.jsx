import React, { useState } from 'react';
import { PlusCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function CreateQuestionPanel({
  user,
  token,
  concepts,
  setProblems,
  selectProblem,
  setCurrentTab
}) {
  const [cqTitle, setCqTitle] = useState('');
  const [cqConcept, setCqConcept] = useState('variables-01');
  const [cqDifficulty, setCqDifficulty] = useState('easy');
  const [cqDescription, setCqDescription] = useState('');
  const [cqStarterCode, setCqStarterCode] = useState('def solution(x):\n    return x\n');
  const [cqExpected, setCqExpected] = useState('');
  const [cqTestInput, setCqTestInput] = useState('');
  const [cqTestExpected, setCqTestExpected] = useState('');
  const [cqStatus, setCqStatus] = useState('');

  const handleCreateCustomQuestion = async (e) => {
    e.preventDefault();
    if (!user) return;
    setCqStatus('Submitting question...');

    let testCases = [];
    if (cqTestInput || cqTestExpected) {
      try {
        const parsedInput = JSON.parse(cqTestInput || '[]');
        const parsedExpected = JSON.parse(cqTestExpected || 'null');
        testCases.push({ input: Array.isArray(parsedInput) ? parsedInput : [parsedInput], expected: parsedExpected });
      } catch {
        testCases.push({ input: [cqTestInput], expected: cqTestExpected });
      }
    }

    try {
      const res = await fetch(`${API}/custom-questions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          title: cqTitle,
          concept_id: cqConcept,
          difficulty: cqDifficulty,
          description: cqDescription,
          starter_code: cqStarterCode,
          expected_behavior: cqExpected,
          test_cases: testCases
        })
      });
      const created = await res.json();
      if (!res.ok) throw new Error(created.detail || 'Failed to create question.');

      setCqStatus('Success! Question added.');
      // Append to problems and launch
      setProblems(prev => [created, ...prev]);
      selectProblem(created);
      setCurrentTab('practice');
    } catch (err) {
      setCqStatus('Error: ' + err.message);
    }
  };

  return (
    <div className="card" style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="card-header">
        <h3><PlusCircle size={20} /> Author Custom Programming Challenge</h3>
        <span style={{ fontSize: 13, color: '#64748b' }}>Saved to SQLite</span>
      </div>

      {cqStatus && (
        <div style={{ padding: '10px 14px', borderRadius: 6, marginBottom: 16, background: cqStatus.includes('Error') ? '#fef2f2' : '#f0fdfa', color: cqStatus.includes('Error') ? '#b91c1c' : '#0f766e' }}>
          {cqStatus}
        </div>
      )}

      <form onSubmit={handleCreateCustomQuestion}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 16 }}>
          <div className="form-group">
            <label>Challenge Title</label>
            <input
              className="form-control"
              required
              placeholder="e.g. Reverse a Linked Sequence"
              value={cqTitle}
              onChange={e => setCqTitle(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Curriculum Concept</label>
            <select className="form-control" value={cqConcept} onChange={e => setCqConcept(e.target.value)}>
              {concepts.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Difficulty</label>
            <select className="form-control" value={cqDifficulty} onChange={e => setCqDifficulty(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Problem Description</label>
          <textarea
            className="form-control"
            rows={3}
            required
            placeholder="Explain the required task, parameters, and constraints..."
            value={cqDescription}
            onChange={e => setCqDescription(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Starter Code Stub</label>
          <textarea
            className="form-control"
            style={{ fontFamily: 'Fira Code, monospace', fontSize: 13 }}
            rows={4}
            value={cqStarterCode}
            onChange={e => setCqStarterCode(e.target.value)}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="form-group">
            <label>Sample Test Input (JSON format, e.g. [5, 10])</label>
            <input
              className="form-control"
              placeholder="[5, 10]"
              value={cqTestInput}
              onChange={e => setCqTestInput(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Expected Return Value (JSON format, e.g. 15)</label>
            <input
              className="form-control"
              placeholder="15"
              value={cqTestExpected}
              onChange={e => setCqTestExpected(e.target.value)}
            />
          </div>
        </div>

        <button className="btn-primary" type="submit" style={{ marginTop: 12 }}>
          Save & Practice Custom Question
        </button>
      </form>
    </div>
  );
}
