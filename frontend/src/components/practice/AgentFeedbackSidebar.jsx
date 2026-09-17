import React from 'react';
import { BrainCircuit, Check, User } from 'lucide-react';

export default function AgentFeedbackSidebar({ submitResult, problems, selectProblem }) {
  return (
    <aside className="sidebar-right">
      <div className="card">
        <div className="card-header" style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 14 }}><BrainCircuit size={16} /> Multi-Agent Pipeline</h3>
        </div>
        <ul className="agent-checklist">
          {['Diagnostic Agent', 'Learner State Agent', 'Similar Learner Retrieval Agent', 'Adaptive Scaffolding Agent', 'Reflection Agent', 'Learning Planner Agent'].map(name => {
            const completed = submitResult?.agent_activity?.includes(name);
            return (
              <li key={name} className="agent-checklist-item" style={{ opacity: completed ? 1 : 0.6 }}>
                {completed ? <Check size={16} color="#10b981" /> : <div style={{ width: 16, height: 16, borderRadius: '50%', border: '1px dashed #94a3b8' }} />}
                <span>{name}</span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Similar Historical Learners from ChromaDB */}
      {submitResult?.similar_learners?.length > 0 && (
        <div className="card">
          <div className="card-header" style={{ marginBottom: 8 }}>
            <h3 style={{ fontSize: 13 }}><User size={15} /> ChromaDB Nearest Learners</h3>
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {submitResult.similar_learners.map((sl, i) => (
              <div key={i} style={{ background: '#f8fafc', padding: 8, borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                  <span>{sl.id}</span>
                  <span style={{ color: '#0d9488' }}>{Math.round(sl.similarity * 100)}% sim</span>
                </div>
                <p style={{ margin: '4px 0 0 0', color: '#64748b', fontSize: 11 }}>{sl.intervention}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Recommendation */}
      {submitResult?.recommendation && (
        <div className="card" style={{ background: '#f0fdfa', border: '1px solid #99f6e4' }}>
          <h4 style={{ margin: '0 0 6px 0', fontSize: 14, color: '#0f766e' }}>Learning Planner</h4>
          <p style={{ margin: 0, fontSize: 12, color: '#334155' }}>{submitResult.recommendation.reason}</p>
          <button
            className="btn-primary"
            style={{ marginTop: 10, padding: '6px 12px', fontSize: 12 }}
            onClick={() => {
              const nextP = problems.find(p => p.id === submitResult.recommendation.next_problem_id);
              if (nextP) selectProblem(nextP);
            }}
          >
            Open Next Challenge
          </button>
        </div>
      )}
    </aside>
  );
}
