import React from 'react';

export default function CurriculumPanel({
  concepts,
  problems,
  conceptPillar,
  setConceptPillar,
  selectedConcept,
  setSelectedConcept,
  selectProblem,
  setCurrentTab
}) {
  return (
    <div>
      {/* Pillar Selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {['All', 'Foundations', 'Collections', 'Intermediate Python', 'Problem Solving'].map(p => (
          <button
            key={p}
            className={`nav-link ${conceptPillar === p ? 'active' : ''}`}
            style={{ border: '1px solid #cbd5e1' }}
            onClick={() => setConceptPillar(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
        {/* Concept List */}
        <div className="sidebar-problems" style={{ maxHeight: 'calc(100vh - 180px)' }}>
          {concepts
            .filter(c => conceptPillar === 'All' || c.category.toLowerCase().includes(conceptPillar.toLowerCase()))
            .map(c => (
              <button
                key={c.id}
                className={`problem-item-btn ${selectedConcept?.id === c.id ? 'active' : ''}`}
                onClick={() => setSelectedConcept(c)}
              >
                <div className="problem-item-title">{c.order_index}. {c.title}</div>
                <div className="problem-item-meta">
                  <span className="pill source">{c.category}</span>
                  <span className={`pill ${c.difficulty}`}>{c.difficulty}</span>
                </div>
              </button>
            ))}
        </div>

        {/* Concept Detailed Study Card */}
        {selectedConcept && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span className="pill source" style={{ marginBottom: 6, display: 'inline-block' }}>{selectedConcept.category}</span>
                <h2 style={{ fontSize: 24, margin: '0 0 8px 0' }}>{selectedConcept.title}</h2>
              </div>
              <span className={`pill ${selectedConcept.difficulty}`} style={{ fontSize: 12 }}>{selectedConcept.difficulty}</span>
            </div>

            <p style={{ color: '#475569', fontSize: 15, margin: '12px 0' }}>{selectedConcept.description}</p>

            <div style={{ background: '#f8fafc', padding: 16, borderRadius: 8, margin: '16px 0', border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 6px 0', color: '#0f766e' }}>🎯 Learning Objectives:</h4>
              <p style={{ margin: 0, fontSize: 14, color: '#334155' }}>{selectedConcept.learning_objectives}</p>
            </div>

            <h3 style={{ fontSize: 17, marginTop: 20 }}>Concept Explanation</h3>
            <p style={{ lineHeight: 1.6, color: '#334155' }}>{selectedConcept.explanation}</p>

            <h3 style={{ fontSize: 17, marginTop: 24 }}>Runnable Python Example</h3>
            <pre style={{ background: '#1e1e1e', color: '#f8fafc', padding: 16, borderRadius: 8, fontFamily: 'Fira Code, monospace', fontSize: 13, overflowX: 'auto' }}>
              {JSON.parse(selectedConcept.examples_json || '[]')[0]?.code || '# Example code'}
            </pre>

            <h3 style={{ fontSize: 17, marginTop: 24 }}>Practice Challenges for this Concept</h3>
            <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
              {problems.filter(p => p.concept_id === selectedConcept.id || p.topic === selectedConcept.id).map(p => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                  <div>
                    <strong style={{ fontSize: 14 }}>{p.title}</strong>
                    <p style={{ margin: '3px 0 0 0', fontSize: 12, color: '#64748b' }}>{p.description}</p>
                  </div>
                  <button
                    className="btn-primary"
                    style={{ width: 'auto', padding: '8px 16px', fontSize: 12 }}
                    onClick={() => {
                      selectProblem(p);
                      setCurrentTab('practice');
                    }}
                  >
                    Solve Challenge
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
