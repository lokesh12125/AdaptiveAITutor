import React from 'react';
import { Folder, ChevronDown, ChevronRight } from 'lucide-react';

export default function ProblemSidebar({
  problemSearch,
  setProblemSearch,
  filteredProblems,
  expandedTopics,
  toggleTopic,
  problem,
  selectProblem
}) {
  return (
    <aside className="sidebar-problems">
      <input
        className="problem-search"
        type="text"
        placeholder="Search practice problems..."
        value={problemSearch}
        onChange={e => setProblemSearch(e.target.value)}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {(() => {
          const grouped = {};
          filteredProblems.forEach(p => {
            const topic = p.concept_id || p.topic || 'general';
            if (!grouped[topic]) grouped[topic] = [];
            grouped[topic].push(p);
          });
          const diffScore = { 'easy': 1, 'medium': 2, 'hard': 3 };
          
          return Object.entries(grouped).map(([topic, probs]) => {
            const isExpanded = expandedTopics[topic];
            return (
              <div key={topic} className="problem-group" style={{ background: '#ffffff', color: '#0f172a', overflow: 'hidden', border: '1px solid #e2e8f0', borderRadius: '6px', marginBottom: '8px' }}>
                <div 
                  style={{ 
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
                    padding: '12px 16px', cursor: 'pointer', background: isExpanded ? '#f8fafc' : '#ffffff',
                    transition: 'background 0.2s', borderBottom: isExpanded ? '1px solid #e2e8f0' : 'none'
                  }}
                  onClick={() => toggleTopic(topic)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Folder size={18} color="#0d9488" />
                    <span style={{ fontSize: 15, fontWeight: 600, textTransform: 'capitalize', color: '#1e293b' }}>
                      {topic.replace(/-/g, ' ')}
                    </span>
                  </div>
                  {isExpanded ? <ChevronDown size={16} color="#64748b" /> : <ChevronRight size={16} color="#64748b" />}
                </div>
                
                {isExpanded && (
                  <div style={{ display: 'flex', flexDirection: 'column', borderLeft: '2px solid #e2e8f0', marginLeft: 24, paddingLeft: 4, paddingBottom: 8, marginTop: 4 }}>
                    {probs.sort((a, b) => (diffScore[a.difficulty] || 0) - (diffScore[b.difficulty] || 0)).map(p => {
                      const isActive = problem?.id === p.id;
                      return (
                        <button
                          key={p.id}
                          className={`problem-item-btn ${isActive ? 'active' : ''}`}
                          style={{ 
                            background: isActive ? '#ecfdf5' : 'transparent',
                            border: isActive ? '1px solid #6ee7b7' : '1px solid transparent',
                            padding: '10px 12px', textAlign: 'left',
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            color: isActive ? '#0d9488' : '#475569', 
                            cursor: 'pointer', borderRadius: 4, margin: '2px 8px 2px 0',
                            fontWeight: isActive ? 600 : 400
                          }}
                          onClick={() => selectProblem(p)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <Folder size={15} color={isActive ? "#0d9488" : "#94a3b8"} />
                            <span style={{ fontSize: 13, textTransform: 'capitalize' }}>{p.title}</span>
                          </div>
                          <ChevronRight size={14} color={isActive ? "#0d9488" : "#cbd5e1"} />
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          });
        })()}
      </div>
    </aside>
  );
}
