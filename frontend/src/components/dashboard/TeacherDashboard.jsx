import React, { useState, useEffect } from 'react';
import { AlertTriangle, BarChart2, CheckCircle, Download, Eye, X, User } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function TeacherDashboard({ token }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [drilldownData, setDrilldownData] = useState(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);

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

  const handleOpenDrilldown = (studentId) => {
    setSelectedStudentId(studentId);
    setDrilldownLoading(true);
    fetch(`${API}/teacher/students/${studentId}/drilldown`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load student drilldown');
        return res.json();
      })
      .then(data => {
        setDrilldownData(data);
        setDrilldownLoading(false);
      })
      .catch(() => {
        setDrilldownLoading(false);
      });
  };

  const handleExportCSV = () => {
    if (!students || students.length === 0) return;
    const headers = ['ID', 'Name', 'Email', 'Mastery (%)', 'Progress (%)', 'Avg Hints', 'Time/Task (s)', 'Learning Gain'];
    const rows = students.map(s => [
      s.id,
      `"${s.name}"`,
      s.email,
      (s.mastery * 100).toFixed(1),
      (s.progress * 100).toFixed(1),
      s.metrics?.avg_hints_per_problem?.toFixed(1) || '0.0',
      s.metrics?.time_to_completion?.toFixed(1) || '0.0',
      s.metrics?.learning_gain?.toFixed(2) || '0.00'
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `students_cohort_analytics_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) return <div className="card"><div className="card-body">Loading teacher dashboard...</div></div>;
  if (error) return <div className="card"><div className="card-body error-text">{error}</div></div>;

  return (
    <div className="card" style={{ animation: 'slideUp 0.4s ease-out' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 className="card-title">Teacher Cohort Dashboard</h3>
          <p className="card-subtitle">Student mastery distribution, cognitive indicators, and at-risk alerts</p>
        </div>
        <button
          onClick={handleExportCSV}
          className="btn-secondary"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', fontSize: 13, background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 6, cursor: 'pointer' }}
        >
          <Download size={15} /> Export Cohort CSV
        </button>
      </div>

      <div className="card-body">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left', background: '#f8fafc' }}>
                <th style={{ padding: '12px' }}>Student Name</th>
                <th style={{ padding: '12px' }}>Email</th>
                <th style={{ padding: '12px' }}>BKT Mastery</th>
                <th style={{ padding: '12px' }}>Progress</th>
                <th style={{ padding: '12px' }}>Avg Hints</th>
                <th style={{ padding: '12px' }}>Time/Task</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {students.map(s => {
                const masteryPct = (s.mastery * 100).toFixed(0);
                return (
                  <tr key={s.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '12px', fontWeight: 600 }}>{s.name}</td>
                    <td style={{ padding: '12px', color: '#64748b' }}>{s.email}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: 12,
                        fontSize: 12,
                        fontWeight: 700,
                        background: s.mastery >= 0.75 ? '#ecfdf5' : s.mastery >= 0.40 ? '#eff6ff' : '#fef2f2',
                        color: s.mastery >= 0.75 ? '#047857' : s.mastery >= 0.40 ? '#1d4ed8' : '#b91c1c'
                      }}>
                        {masteryPct}%
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>{(s.progress * 100).toFixed(0)}%</td>
                    <td style={{ padding: '12px' }}>{s.metrics?.avg_hints_per_problem?.toFixed(1) || '0.0'}</td>
                    <td style={{ padding: '12px' }}>{s.metrics?.time_to_completion?.toFixed(1) || '0.0'}s</td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        onClick={() => handleOpenDrilldown(s.id)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '5px 10px',
                          fontSize: 12,
                          background: '#0d9488',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 6,
                          cursor: 'pointer'
                        }}
                      >
                        <Eye size={13} /> Drilldown
                      </button>
                    </td>
                  </tr>
                );
              })}
              {students.length === 0 && (
                <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center' }}>No students found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* R-14: Per-Student Longitudinal Drilldown Modal */}
      {selectedStudentId && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: 12,
            width: '100%',
            maxWidth: 780,
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: 24,
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <User size={22} color="#0d9488" />
                <div>
                  <h3 style={{ margin: 0, fontSize: 18 }}>Student Detailed Analytics</h3>
                  <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>{drilldownData?.student?.name} ({drilldownData?.student?.email})</p>
                </div>
              </div>
              <button
                onClick={() => { setSelectedStudentId(null); setDrilldownData(null); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={20} />
              </button>
            </div>

            {drilldownLoading ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>Loading detailed analytics...</div>
            ) : drilldownData ? (
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 20 }}>
                {/* At-Risk Banner */}
                {drilldownData.is_at_risk ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#fef2f2', border: '1px solid #fecaca', padding: 12, borderRadius: 8, color: '#991b1b' }}>
                    <AlertTriangle size={20} color="#dc2626" />
                    <div>
                      <strong>At-Risk Advisory Flagged:</strong> {drilldownData.at_risk_reason}. Recommended pedagogical intervention: targeted prerequisite review.
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#f0fdf4', border: '1px solid #bbf7d0', padding: 10, borderRadius: 8, color: '#166534', fontSize: 13 }}>
                    <CheckCircle size={18} color="#16a34a" />
                    <span>Progression trajectory stable. No acute struggle triggers observed.</span>
                  </div>
                )}

                {/* Concept Breakdown */}
                <div>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: 14, color: '#334155' }}>Concept Mastery Distribution</h4>
                  <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                    <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                          <th style={{ padding: 8 }}>Concept</th>
                          <th style={{ padding: 8 }}>Category</th>
                          <th style={{ padding: 8 }}>BKT Mastery</th>
                          <th style={{ padding: 8 }}>Attempts</th>
                        </tr>
                      </thead>
                      <tbody>
                        {drilldownData.concept_breakdown?.map(cb => (
                          <tr key={cb.concept_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: 8, fontWeight: 500 }}>{cb.concept_title}</td>
                            <td style={{ padding: 8, color: '#64748b' }}>{cb.category}</td>
                            <td style={{ padding: 8, fontWeight: 700, color: cb.mastery >= 0.75 ? '#16a34a' : '#d97706' }}>
                              {(cb.mastery * 100).toFixed(0)}%
                            </td>
                            <td style={{ padding: 8 }}>{cb.attempts_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Recurring Misconceptions */}
                <div>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: 14, color: '#334155' }}>Recurring Misconceptions (R-03 Tracking)</h4>
                  {drilldownData.misconceptions?.length > 0 ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                      {drilldownData.misconceptions.map((m, idx) => (
                        <div key={idx} style={{ background: '#fffbeb', border: '1px solid #fef3c7', padding: '8px 12px', borderRadius: 6, fontSize: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <strong>{m.concept_id}:</strong> <span style={{ color: '#92400e' }}>{m.misconception_code}</span>
                          </div>
                          <span style={{ background: '#fef3c7', padding: '2px 8px', borderRadius: 10, fontWeight: 700, color: '#b45309' }}>
                            {m.occurrence_count}x detected
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#64748b', fontSize: 12 }}>No persistent semantic misconceptions recorded for this student.</div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
