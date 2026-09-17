import React, { useState } from 'react';
import { History as HistoryIcon } from 'lucide-react';

export default function HistoryPanel({ historyList }) {
  const [selectedHistoryCode, setSelectedHistoryCode] = useState(null);

  return (
    <>
      <div className="card">
        <div className="card-header">
          <h3><HistoryIcon size={18} /> Recorded Submissions & Learning Audit</h3>
          <span style={{ fontSize: 13, color: '#64748b' }}>Stored in SQLite (tutor.db)</span>
        </div>

        <div className="table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Date / Time</th>
                <th>Problem</th>
                <th>Concept</th>
                <th>Result</th>
                <th>Error Category</th>
                <th>Scaffolding</th>
                <th>Hints</th>
                <th>Pace</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {historyList.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 24, color: '#94a3b8' }}>
                    No submission history found for this student account.
                  </td>
                </tr>
              ) : (
                historyList.map(item => (
                  <tr key={item.id}>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td><strong>{item.problem_title || `Problem #${item.problem_id}`}</strong></td>
                    <td><span className="pill source">{item.concept_id || 'general'}</span></td>
                    <td>
                      {item.passed ? (
                        <span style={{ color: '#10b981', fontWeight: 700 }}>Passed</span>
                      ) : (
                        <span style={{ color: '#ef4444', fontWeight: 700 }}>Failed</span>
                      )}
                    </td>
                    <td><code>{item.error_type}</code></td>
                    <td>Level {item.scaffolding_level || 1}</td>
                    <td>{item.hints_used}</td>
                    <td>{item.response_time ? `${Math.round(item.response_time)}s` : '—'}</td>
                    <td>
                      <button
                        style={{ background: 'transparent', border: '1px solid #cbd5e1', borderRadius: 4, padding: '4px 8px', fontSize: 11, cursor: 'pointer' }}
                        onClick={() => setSelectedHistoryCode(item.code)}
                      >
                        View Code
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL: VIEW CODE FROM HISTORY */}
      {selectedHistoryCode !== null && (
        <div className="modal-overlay" onClick={() => setSelectedHistoryCode(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ margin: 0 }}>Submitted Solution</h3>
              <button style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 18 }} onClick={() => setSelectedHistoryCode(null)}>✕</button>
            </div>
            <pre style={{ background: '#1e1e1e', color: '#f8fafc', padding: 16, borderRadius: 8, fontFamily: 'Fira Code, monospace', fontSize: 13, overflowX: 'auto' }}>
              {selectedHistoryCode}
            </pre>
          </div>
        </div>
      )}
    </>
  );
}
