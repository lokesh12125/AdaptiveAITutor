import React from 'react';
import { 
  BrainCircuit, 
  CheckCircle2, 
  Timer, 
  Award, 
  Play, 
  BookOpen, 
  Star,
  Clock,
  Trophy,
  Sparkles,
  ChevronRight
} from 'lucide-react';

export default function DashboardPanel({
  user,
  activeState,
  evalMetrics,
  submitResult,
  recommendation,
  problems = [],
  selectProblem,
  setCurrentTab,
  concepts = [],
  conceptProgress = {},
  setSelectedConcept,
  satisfactionRating,
  setSatisfactionRating,
  historyList = []
}) {

  // --- 1. RECENTLY STUDIED TOPICS ---
  // Extract unique concept IDs from recent history attempts, fallback to concepts with attempts > 0, fallback to first concepts
  const recentConceptIds = [];
  if (Array.isArray(historyList) && historyList.length > 0) {
    historyList.forEach(h => {
      const cId = h.concept_id || h.topic;
      if (cId && !recentConceptIds.includes(cId)) {
        recentConceptIds.push(cId);
      }
    });
  }

  // Also include any concepts from conceptProgress with attempts > 0
  Object.keys(conceptProgress).forEach(cId => {
    if (conceptProgress[cId]?.attempts_count > 0 && !recentConceptIds.includes(cId)) {
      recentConceptIds.push(cId);
    }
  });

  // Map to concept objects
  let recentTopics = recentConceptIds
    .map(id => {
      const c = concepts.find(item => item.id === id || item.title.toLowerCase() === id.toLowerCase());
      const prog = conceptProgress[id] || {};
      const mastery = prog.mastery !== undefined ? Math.round(prog.mastery * 100) : 0;
      return {
        id: id,
        title: c ? c.title : (id.charAt(0).toUpperCase() + id.slice(1)),
        category: c ? c.category : 'General',
        mastery: mastery,
        attempts: prog.attempts_count || 1,
        successes: prog.success_count || 0,
        conceptObj: c
      };
    })
    .slice(0, 6);

  // Fallback if user has not attempted any topics yet: show first foundational concepts as "Starting Topics"
  const hasStudiedBefore = recentTopics.length > 0;
  if (!hasStudiedBefore && concepts.length > 0) {
    recentTopics = concepts.slice(0, 4).map(c => ({
      id: c.id,
      title: c.title,
      category: c.category || 'Foundations',
      mastery: Math.round((conceptProgress[c.id]?.mastery || 0.20) * 100),
      attempts: conceptProgress[c.id]?.attempts_count || 0,
      successes: conceptProgress[c.id]?.success_count || 0,
      conceptObj: c,
      isSuggested: true
    }));
  }

  // --- 2. MOST COMPLETED TOPICS ---
  // Sort concepts by mastery percentage descending
  const conceptsWithMastery = concepts.map(c => {
    const prog = conceptProgress[c.id];
    const masteryVal = prog?.mastery !== undefined ? prog.mastery : 0;
    return {
      ...c,
      masteryPct: Math.round(masteryVal * 100),
      attempts: prog?.attempts_count || 0,
      successes: prog?.success_count || 0
    };
  });

  // Sort: highest mastery first, then most attempts
  conceptsWithMastery.sort((a, b) => {
    if (b.masteryPct !== a.masteryPct) return b.masteryPct - a.masteryPct;
    return b.attempts - a.attempts;
  });

  const topCompletedTopics = conceptsWithMastery.slice(0, 8);

  return (
    <div className="dashboard-grid">
      {/* Welcome Hero Banner */}
      <div className="welcome-card">
        <div>
          <h2>Welcome back, {user?.name || 'Learner'}!</h2>
          <p>Your cognitive model continuously adapts to your problem-solving evidence using Bayesian Knowledge Tracing.</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: 13, textTransform: 'uppercase', opacity: 0.8, fontWeight: 700 }}>Curriculum Progress</span>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{Math.round((activeState?.progress || 0) * 100)}%</div>
        </div>
      </div>

      {/* Quick Metrics Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon"><BrainCircuit size={24} /></div>
          <div className="stat-content">
            <div className="stat-label">BKT Mastery</div>
            <div className="stat-value">{Math.round((activeState?.mastery || 0) * 100)}%</div>
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

      {/* Recommended Next Step Card */}
      <div className="recommendation-card">
        <div className="recommendation-content">
          <h4>🎯 Recommended Next Learning Step: {recommendation?.topic || submitResult?.recommendation?.topic || 'Python Foundations'}</h4>
          <p>{recommendation?.reason || submitResult?.recommendation?.reason || 'Build and solidify your foundational programming concepts through active practice.'}</p>
        </div>
        <button
          className="btn-primary"
          style={{ width: 'auto', padding: '10px 20px' }}
          onClick={() => {
            const targetId = recommendation?.next_problem_id || submitResult?.recommendation?.next_problem_id;
            const target = problems.find(p => p.id === targetId) || problems[0];
            if (target) selectProblem(target);
            setCurrentTab('practice');
          }}
        >
          <Play size={16} /> Practice Challenge
        </button>
      </div>

      {/* Main Dashboard 2-Column Section */}
      <div className="dashboard-columns">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* SECTION 1: RECENTLY STUDIED TOPICS */}
          <div className="card">
            <div className="card-header">
              <h3>
                <Clock size={18} style={{ color: '#0d9488' }} /> 
                {hasStudiedBefore ? 'Recently Studied Topics' : 'Recommended Starting Topics'}
              </h3>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                {hasStudiedBefore ? 'Based on your recent attempts' : 'Get started with foundational concepts'}
              </span>
            </div>

            <div className="concept-progress-grid">
              {recentTopics.map(item => {
                const prog = item.mastery;
                return (
                  <div
                    key={item.id}
                    className="concept-bar-item"
                    onClick={() => { 
                      if (item.conceptObj) setSelectedConcept(item.conceptObj); 
                      setCurrentTab('curriculum'); 
                    }}
                    title="Click to view concept curriculum"
                    style={{ borderLeft: '4px solid #0d9488' }}
                  >
                    <div className="concept-bar-head">
                      <span style={{ fontWeight: 700 }}>{item.title}</span>
                      <span style={{ color: prog >= 75 ? '#059669' : '#0d9488', fontWeight: 800 }}>
                        {prog}%
                      </span>
                    </div>

                    <div style={{ fontSize: 11, color: '#64748b', margin: '4px 0 8px 0', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{item.category}</span>
                      <span>{item.attempts > 0 ? `${item.attempts} attempts` : 'Not started'}</span>
                    </div>

                    <div className="progress-track">
                      <div 
                        className="progress-fill" 
                        style={{ 
                          width: `${prog}%`, 
                          background: prog >= 75 ? '#10b981' : 'linear-gradient(90deg, #0d9488, #2dd4bf)',
                          opacity: prog === 0 ? 0.2 : 1 
                        }} 
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SECTION 2: MOST COMPLETED TOPICS */}
          <div className="card">
            <div className="card-header">
              <h3>
                <Trophy size={18} style={{ color: '#f59e0b' }} /> 
                Most Completed Topics ({concepts.length > 0 ? concepts.length : 49} Total Concepts)
              </h3>
              <span style={{ fontSize: 12, color: '#64748b' }}>Sorted by BKT Mastery Level</span>
            </div>

            {topCompletedTopics.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
                Loading concept progress...
              </div>
            ) : (
              <div className="concept-progress-grid">
                {topCompletedTopics.map(c => {
                  const prog = c.masteryPct;
                  const isMastered = prog >= 75;
                  const isInProgress = prog > 0 && prog < 75;

                  return (
                    <div
                      key={c.id}
                      className="concept-bar-item"
                      onClick={() => { setSelectedConcept(c); setCurrentTab('curriculum'); }}
                      title="Click to view concept curriculum"
                    >
                      <div className="concept-bar-head">
                        <span style={{ fontWeight: 600 }}>{c.title}</span>
                        <span style={{ 
                          fontSize: 11, 
                          padding: '2px 8px', 
                          borderRadius: 12, 
                          fontWeight: 700,
                          background: isMastered ? '#ecfdf5' : isInProgress ? '#eff6ff' : '#f8fafc',
                          color: isMastered ? '#047857' : isInProgress ? '#1d4ed8' : '#64748b'
                        }}>
                          {isMastered ? 'Mastered' : isInProgress ? 'In Progress' : 'Not Started'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '6px 0 4px 0' }}>
                        <span style={{ fontSize: 11, color: '#64748b' }}>{c.category}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: isMastered ? '#059669' : '#0f766e' }}>
                          {prog}%
                        </span>
                      </div>

                      <div className="progress-track">
                        <div 
                          className="progress-fill" 
                          style={{ 
                            width: `${prog}%`, 
                            background: isMastered ? '#059669' : '#0d9488',
                            opacity: prog === 0 ? 0.15 : 1 
                          }} 
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* Cognitive State Monitor Right Side Column */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-header">
            <h3><BrainCircuit size={18} /> Cognitive State Monitor</h3>
          </div>
          <div className="gauge-grid">
            <div className="gauge-item">
              <div className="gauge-header">
                <span>Concept Mastery (BKT)</span>
                <strong>{Math.round((activeState?.mastery || 0) * 100)}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(activeState?.mastery || 0) * 100}%`, opacity: activeState?.mastery === 0 ? 0 : 1 }} />
              </div>
            </div>

            <div className="gauge-item">
              <div className="gauge-header">
                <span>Confidence Indicator</span>
                <strong>{Math.round((activeState?.confidence || 0) * 100)}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(activeState?.confidence || 0) * 100}%`, background: '#6366f1', opacity: activeState?.confidence === 0 ? 0 : 1 }} />
              </div>
            </div>

            <div className="gauge-item">
              <div className="gauge-header">
                <span>Confusion Detection</span>
                <strong>{Math.round((activeState?.confusion || 0) * 100)}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(activeState?.confusion || 0) * 100}%`, background: '#f59e0b', opacity: activeState?.confusion === 0 ? 0 : 1 }} />
              </div>
            </div>

            <div className="gauge-item">
              <div className="gauge-header">
                <span>Interaction Cognitive Load Proxy</span>
                <strong>{Math.round((activeState?.cognitive_load || 0) * 100)}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(activeState?.cognitive_load || 0) * 100}%`, background: '#ef4444', opacity: activeState?.cognitive_load === 0 ? 0 : 1 }} />
              </div>
            </div>

            <hr style={{ margin: '14px 0', border: '0', borderTop: '1px solid #e2e8f0' }} />

            {/* Student Satisfaction Widget */}
            <div>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>Session Satisfaction Rating:</span>
              <div className="satisfaction-widget" style={{ marginTop: 8 }}>
                {[1, 2, 3, 4, 5].map(star => (
                  <button
                    key={star}
                    className={`star-btn ${satisfactionRating >= star ? 'filled' : ''}`}
                    onClick={() => setSatisfactionRating && setSatisfactionRating(star)}
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
