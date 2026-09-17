import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function TeacherDashboard({ token }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API}/admin/students`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load students');
        return res.json();
      })
      .then(data => {
        setStudents(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [token]);

  if (loading) return <div className="card"><div className="card-body">Loading teacher dashboard...</div></div>;
  if (error) return <div className="card"><div className="card-body error-text">{error}</div></div>;

  return (
    <div className="card" style={{ animation: 'slideUp 0.4s ease-out' }}>
      <div className="card-header">
        <h3 className="card-title">Teacher Dashboard</h3>
        <p className="card-subtitle">Overview of all students</p>
      </div>
      <div className="card-body">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '12px' }}>Name</th>
                <th style={{ padding: '12px' }}>Email</th>
                <th style={{ padding: '12px' }}>Mastery</th>
                <th style={{ padding: '12px' }}>Progress</th>
                <th style={{ padding: '12px' }}>Avg Hints</th>
                <th style={{ padding: '12px' }}>Time/Task</th>
              </tr>
            </thead>
            <tbody>
              {students.map(s => (
                <tr key={s.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '12px' }}>{s.name}</td>
                  <td style={{ padding: '12px' }}>{s.email}</td>
                  <td style={{ padding: '12px' }}>{(s.mastery * 100).toFixed(1)}%</td>
                  <td style={{ padding: '12px' }}>{(s.progress * 100).toFixed(1)}%</td>
                  <td style={{ padding: '12px' }}>{s.metrics?.avg_hints_per_problem?.toFixed(1) || '0.0'}</td>
                  <td style={{ padding: '12px' }}>{s.metrics?.time_to_completion?.toFixed(1) || '0.0'}s</td>
                </tr>
              ))}
              {students.length === 0 && (
                <tr><td colSpan="6" style={{ padding: '24px', textAlign: 'center' }}>No students found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
