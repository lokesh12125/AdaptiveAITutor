import React from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  Code2, 
  Bot, 
  History as HistoryIcon, 
  PlusCircle, 
  Sparkles, 
  User, 
  LogOut 
} from 'lucide-react';

export default function TopHeader({ 
  currentTab, 
  setCurrentTab, 
  user, 
  systemHealth, 
  handleLogout, 
  setIsTimerRunning,
  sessionId,
  handleEndSession
}) {
  return (
    <header className="navbar">
      <div className="nav-brand" onClick={() => setCurrentTab('dashboard')}>
        <Sparkles size={22} />
        Adaptive Tutor
        <span>Multi-Agent Lab</span>
      </div>

      <nav className="nav-links">
        <button className={`nav-link ${currentTab === 'dashboard' ? 'active' : ''}`} onClick={() => setCurrentTab('dashboard')}>
          <LayoutDashboard size={17} /> Dashboard
        </button>
        {user?.role === 'teacher' && (
          <button className={`nav-link ${currentTab === 'teacher' ? 'active' : ''}`} onClick={() => setCurrentTab('teacher')}>
            <LayoutDashboard size={17} /> Teacher Portal
          </button>
        )}
        <button className={`nav-link ${currentTab === 'curriculum' ? 'active' : ''}`} onClick={() => setCurrentTab('curriculum')}>
          <BookOpen size={17} /> Curriculum
        </button>
        <button className={`nav-link ${currentTab === 'practice' ? 'active' : ''}`} onClick={() => { setCurrentTab('practice'); setIsTimerRunning(true); }}>
          <Code2 size={17} /> Practice Lab
        </button>
        <button className={`nav-link ${currentTab === 'tutor' ? 'active' : ''}`} onClick={() => setCurrentTab('tutor')}>
          <Bot size={17} /> AI Tutor
        </button>
        <button className={`nav-link ${currentTab === 'history' ? 'active' : ''}`} onClick={() => setCurrentTab('history')}>
          <HistoryIcon size={17} /> History
        </button>
        <button className={`nav-link ${currentTab === 'create' ? 'active' : ''}`} onClick={() => setCurrentTab('create')}>
          <PlusCircle size={17} /> Create Question
        </button>
      </nav>

      <div className="nav-right">
        {sessionId && (
          <div className="session-badge" style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '4px 10px', borderRadius: '16px', fontSize: '0.8rem', color: '#10b981' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
            <span>Session #{sessionId}</span>
            <button
              onClick={handleEndSession}
              title="Explicitly end current session"
              style={{
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#ef4444',
                borderRadius: '8px',
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600
              }}
            >
              End
            </button>
          </div>
        )}

        <div className={`mode-tag ${systemHealth.llm === 'live' ? 'live' : 'demo'}`}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: systemHealth.llm === 'live' ? '#10b981' : '#f59e0b' }} />
          {systemHealth.llm === 'live' ? 'OpenAI Live' : 'Demo Mode (Fallback Active)'}
        </div>

        <div className="user-badge">
          <User size={15} />
          {user.name}
          <button className="btn-logout" title="Log out" onClick={handleLogout}>
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}
