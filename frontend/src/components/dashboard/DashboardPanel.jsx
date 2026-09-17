import React from 'react';
import { 
  BrainCircuit, 
  CheckCircle2, 
  Timer, 
  Award, 
  Play, 
  BookOpen, 
  Star 
} from 'lucide-react';

export default function DashboardPanel({
  user,
  activeState,
  evalMetrics,
  submitResult,
  problems,
  selectProblem,
  setCurrentTab,
  concepts,
  conceptProgress,
  setSelectedConcept,
  satisfactionRating,
  setSatisfactionRating
}) {
  return (
    <div className="dashboard-grid">
      <div className="welcome-card">
        <div>
          <h2>Welcome back, {user.name}!</h2>
          <p>Your cognitive model is adapting to your problem solving evidence using Bayesian Knowledge Tracing.</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: 13, textTransform: 'uppercase', opacity: 0.8, fontWeight: 700 }}>Curriculum Progress</span>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{Math.round(activeState.progress * 100)}%</div>
        </div>
      </div>

      {/* Quick Metrics */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon"><BrainCircuit size={24} /></div>
          <div className="stat-content">
            <div className="stat-label">BKT Mastery</div>
            <div className="stat-value">{Math.round(activeState.mastery * 100)}%</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><CheckCircle2 size={24} /></div>
          <div className="stat-content">
            <div className="stat-label">Solved Problems</div>
            <div className="stat-value">{evalMetrics?.problems_solved || 0}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Timer size={24} /></div>
          <div className="stat-content">
            <div className="stat-label">Avg Pace</div>
            <div className="stat-value">{evalMetrics?.time_to_completion || 0}s</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Award size={24} /></div>
          <div className="stat-content">
            <div className="stat-label">Task Completion</div>
            <div className="stat-value">{Math.round((evalMetrics?.task_completion_rate || 0) * 100)}%</div>
          </div>
        </div>
      </div>

      {/* Learning Planner Next Recommendation */}
      <div className="recommendation-card">
        <div className="recommendation-content">
          <h4>🎯 Recommended Next Learning Step: {submitResult?.recommendation?.topic || 'Python Foundations'}</h4>
          <p>{submitResult?.recommendation?.reason || 'Build and solidify your foundational programming concepts through active practice.'}</p>
        </div>
        <button
          className="btn-primary"
          style={{ width: 'auto', padding: '10px 20px' }}
          onClick={() => {
            const targetId = submitResult?.recommendation?.next_problem_id;
            const target = problems.find(p => p.id === targetId) || problems[0];
            if (target) selectProblem(target);
            setCurrentTab('practice');
          }}
        >
          <Play size={16} /> Practice Challenge
        </button>
      </div>

      {/* 2-Column Section: Concept Progress & Cognitive State Gauge */}
      <div className="dashboard-columns">
        <div className="card">
          <div className="card-header">
            <h3><BookOpen size={18} /> Concept-Wise Learning Progress (49 Concepts)</h3>
            <span style={{ fontSize: 12, color: '#64748b' }}>Updated via Bayesian Knowledge Tracing</span>
          </div>
          <div className="concept-progress-grid">
            {concepts.slice(0, 16).map(c => {
              const prog = conceptProgress[c.id]?.mastery ? Math.round(conceptProgress[c.id].mastery * 100) : 0;
              return (
                <div
                  key={c.id}
                  className="concept-bar-item"
                  onClick={() => { setSelectedConcept(c); setCurrentTab('curriculum'); }}
                  title="Click to view concept curriculum"
                >
                  <div className="concept-bar-head">
                    <span>{c.title}</span>
                    <span style={{ color: prog >= 75 ? '#059669' : '#0d9488' }}>{prog}%</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${prog}%`, opacity: prog === 0 ? 0 : 1 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cognitive Monitor */}
        <div className="card">
          <div className="card-header">
            <h3><BrainCircuit size={18} /> Cognitive State Monitor</h3>
          </div>
          <div className="gauge-grid">
            <div className="gauge-item">
              <div className="gauge-header">
                <span>Concept Mastery (BKT)</span>
                <strong>{Math.round(activeState.mastery * 100)}%</strong>
              </div>
              <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.mastery * 100}%`, opacity: activeState.mastery === 0 ? 0 : 1 }} /></div>
            </div>
            <div className="gauge-item">
              <div className="gauge-header">
                <span>Confidence Indicator</span>
                <strong>{Math.round(activeState.confidence * 100)}%</strong>
              </div>
              <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.confidence * 100}%`, background: '#6366f1', opacity: activeState.confidence === 0 ? 0 : 1 }} /></div>
            </div>
            <div className="gauge-item">
              <div className="gauge-header">
                <span>Confusion Detection</span>
                <strong>{Math.round(activeState.confusion * 100)}%</strong>
              </div>
              <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.confusion * 100}%`, background: '#f59e0b', opacity: activeState.confusion === 0 ? 0 : 1 }} /></div>
            </div>
            <div className="gauge-item">
              <div className="gauge-header">
                <span>Interaction Cognitive Load Proxy</span>
                <strong>{Math.round(activeState.cognitive_load * 100)}%</strong>
              </div>
              <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.cognitive_load * 100}%`, background: '#ef4444', opacity: activeState.cognitive_load === 0 ? 0 : 1 }} /></div>
            </div>

            <hr style={{ margin: '14px 0', border: '0', borderTop: '1px solid #e2e8f0' }} />

            {/* Student Satisfaction Widget */}
            <div>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>Session Satisfaction Rating:</span>
              <div className="satisfaction-widget">
                {[1, 2, 3, 4, 5].map(star => (
                  <button
                    key={star}
                    className={`star-btn ${satisfactionRating >= star ? 'filled' : ''}`}
                    onClick={() => setSatisfactionRating(star)}
                    title={`Rate ${star} stars`}
                  >
                    <Star size={24} fill={satisfactionRating >= star ? '#f59e0b' : 'transparent'} color={satisfactionRating >= star ? '#f59e0b' : '#cbd5e1'} />
                  </button>
                ))}
                <span style={{ fontSize: 12, color: '#64748b', marginLeft: 8 }}>Tap to rate</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
