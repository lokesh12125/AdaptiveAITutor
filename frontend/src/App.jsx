import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import {
  Award,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  CheckCircle2,
  Code2,
  HelpCircle,
  History as HistoryIcon,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Play,
  PlusCircle,
  RefreshCw,
  Send,
  Sparkles,
  Star,
  Timer,
  User,
  XCircle
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'
const API = `${API_BASE}/api`

function TeacherDashboard({ token }) {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/admin/students`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load students')
        return res.json()
      })
      .then(data => {
        setStudents(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [token])

  if (loading) return <div className="card"><div className="card-body">Loading teacher dashboard...</div></div>
  if (error) return <div className="card"><div className="card-body error-text">{error}</div></div>

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
  )
}

export default function App() {
  // --- AUTHENTICATION STATE ---
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('adaptive_tutor_user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('adaptive_tutor_token') || '')
  const [authMode, setAuthMode] = useState('login')
  const [authName, setAuthName] = useState('')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authRole, setAuthRole] = useState('student')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  // --- NAVIGATION STATE ---
  const [currentTab, setCurrentTab] = useState('dashboard') // dashboard | curriculum | practice | tutor | history | create

  // --- SYSTEM HEALTH & MODE ---
  const [systemHealth, setSystemHealth] = useState({ backend: 'checking', llm: 'demo' })

  // --- CURRICULUM & PROBLEMS ---
  const [concepts, setConcepts] = useState([])
  const [selectedConcept, setSelectedConcept] = useState(null)
  const [conceptPillar, setConceptPillar] = useState('All')
  const [conceptProgress, setConceptProgress] = useState({})
  const [problems, setProblems] = useState([])
  const [problem, setProblem] = useState(null)
  const [problemSearch, setProblemSearch] = useState('')

  // --- PRACTICE LAB WORKSPACE ---
  const [code, setCode] = useState('')
  const [activeSeconds, setActiveSeconds] = useState(0)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const timerRef = useRef(null)
  const [submitLoading, setSubmitLoading] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [runResult, setRunResult] = useState(null)
  const [runLoading, setRunLoading] = useState(false)

  // --- CONVERSATIONAL AI TUTOR ---
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  // --- AUDIT HISTORY & EVALUATION METRICS ---
  const [historyList, setHistoryList] = useState([])
  const [evalMetrics, setEvalMetrics] = useState(null)
  const [satisfactionRating, setSatisfactionRating] = useState(0)
  const [selectedHistoryCode, setSelectedHistoryCode] = useState(null)

  // --- CUSTOM QUESTION CREATION ---
  const [cqTitle, setCqTitle] = useState('')
  const [cqConcept, setCqConcept] = useState('variables')
  const [cqDifficulty, setCqDifficulty] = useState('easy')
  const [cqDescription, setCqDescription] = useState('')
  const [cqStarterCode, setCqStarterCode] = useState('def solution(x):\n    # Write logic here\n    pass')
  const [cqExpected, setCqExpected] = useState('')
  const [cqTestInput, setCqTestInput] = useState('')
  const [cqTestExpected, setCqTestExpected] = useState('')
  const [cqStatus, setCqStatus] = useState('')

  // --- 1. INITIAL SYSTEM LOAD & HEALTH CHECK ---
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(data => setSystemHealth(data))
      .catch(() => setSystemHealth({ backend: 'offline', llm: 'demo' }))

    fetch(`${API}/concepts`)
      .then(r => r.json())
      .then(data => {
        setConcepts(data)
        if (data.length > 0) setSelectedConcept(data[0])
      })
      .catch(() => {})

    fetch(`${API}/problems`)
      .then(r => r.json())
      .then(data => {
        setProblems(data)
        if (data.length > 0 && !problem) {
          setProblem(data[0])
          setCode(data[0].starter_code)
        }
      })
      .catch(() => {})
  }, [])

  // --- 2. USER DATA REFRESH ---
  const refreshUserData = (learnerId) => {
    if (!learnerId) return
    fetch(`${API}/learner/${learnerId}`)
      .then(r => r.json())
      .then(st => {
        if (submitResult) {
          setSubmitResult(prev => ({ ...prev, learner_state: st }))
        }
      })
      .catch(() => {})

    fetch(`${API}/learner/${learnerId}/progress`)
      .then(r => r.json())
      .then(p => setConceptProgress(p))
      .catch(() => {})

    fetch(`${API}/learner/${learnerId}/history`)
      .then(r => r.json())
      .then(h => setHistoryList(h))
      .catch(() => {})

    fetch(`${API}/metrics/${learnerId}`)
      .then(r => r.json())
      .then(m => {
        setEvalMetrics(m)
        if (m.satisfaction_score) setSatisfactionRating(m.satisfaction_score)
      })
      .catch(() => {})

    fetch(`${API}/chat/${learnerId}`)
      .then(r => r.json())
      .then(msgs => setChatMessages(msgs))
      .catch(() => {})
  }

  useEffect(() => {
    if (user?.id) {
      refreshUserData(user.id)
    }
  }, [user])

  // --- 3. RESPONSE TIME STOPWATCH ---
  useEffect(() => {
    if (isTimerRunning) {
      timerRef.current = setInterval(() => {
        setActiveSeconds(s => s + 1)
      }, 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [isTimerRunning])

  const selectProblem = (prob) => {
    setProblem(prob)
    setCode(prob.starter_code)
    setSubmitResult(null)
    setActiveSeconds(0)
    setIsTimerRunning(true)
  }

  // --- 4. AUTHENTICATION HANDLERS ---
  const handleAuth = async (e) => {
    if (e) e.preventDefault()
    setAuthError('')
    setAuthLoading(true)

    const endpoint = authMode === 'register' ? `${API}/auth/register` : `${API}/auth/login`
    const payload = authMode === 'register' 
      ? { name: authName, email: authEmail, password: authPassword, role: authRole }
      : { email: authEmail, password: authPassword }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Authentication failed.')

      localStorage.setItem('adaptive_tutor_token', data.token)
      localStorage.setItem('adaptive_tutor_user', JSON.stringify(data.user))
      setToken(data.token)
      setUser(data.user)
      refreshUserData(data.user.id)
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setAuthEmail('demo-student@adaptive.edu')
    setAuthPassword('demoPassword123')
    setAuthName('Demo Student')

    // Try login first; if 401, register then login
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'demo-student@adaptive.edu', password: 'demoPassword123' })
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('adaptive_tutor_token', data.token)
        localStorage.setItem('adaptive_tutor_user', JSON.stringify(data.user))
        setToken(data.token)
        setUser(data.user)
        refreshUserData(data.user.id)
        return
      }
    } catch {}

    // Register demo
    try {
      const reg = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Demo Student', email: 'demo-student@adaptive.edu', password: 'demoPassword123' })
      })
      const data = await reg.json()
      if (reg.ok) {
        localStorage.setItem('adaptive_tutor_token', data.token)
        localStorage.setItem('adaptive_tutor_user', JSON.stringify(data.user))
        setToken(data.token)
        setUser(data.user)
        refreshUserData(data.user.id)
      }
    } catch {}
  }

  const handleLogout = () => {
    localStorage.removeItem('adaptive_tutor_token')
    localStorage.removeItem('adaptive_tutor_user')
    setUser(null)
    setToken('')
    setSubmitResult(null)
  }

  const handleRunCode = async () => {
    if (!problem || !user) return
    setRunLoading(true)
    setRunResult(null)
    setSubmitResult(null)

    try {
      const res = await fetch(`${API}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          learner_id: user.id,
          problem_id: problem.id,
          code,
          response_time: activeSeconds
        })
      })
      const data = await res.json()
      setRunResult(data.execution)
    } catch (err) {
      alert('Failed to run code: ' + err.message)
    } finally {
      setRunLoading(false)
    }
  }

  // --- 5. CODE SUBMISSION ---
  const handleSubmitCode = async () => {
    if (!problem || !user) return
    setSubmitLoading(true)
    setRunResult(null)
    setIsTimerRunning(false)
    const responseTime = Math.max(1.0, activeSeconds)

    try {
      const res = await fetch(`${API}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          learner_id: user.id,
          problem_id: problem.id,
          code,
          response_time: responseTime
        })
      })
      const data = await res.json()
      setSubmitResult(data)
      refreshUserData(user.id)
    } catch (err) {
      alert('Failed to communicate with tutor backend: ' + err.message)
    } finally {
      setSubmitLoading(false)
    }
  }

  // --- 6. AI TUTOR CHAT ---
  const handleSendChat = async (presetText) => {
    const textToSend = presetText || chatInput
    if (!textToSend.trim() || !user) return
    if (!presetText) setChatInput('')
    setChatLoading(true)

    // Optimistic user bubble
    const userMsg = { id: Date.now(), role: 'user', content: textToSend, created_at: new Date().toISOString() }
    setChatMessages(prev => [...prev, userMsg])

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          learner_id: user.id,
          message: textToSend,
          problem_id: problem ? problem.id : null
        })
      })
      const data = await res.json()
      const assistantMsg = { id: Date.now() + 1, role: 'assistant', content: data.reply, created_at: new Date().toISOString() }
      setChatMessages(prev => [...prev, assistantMsg])
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    } catch {
      const errorMsg = { id: Date.now() + 1, role: 'assistant', content: 'Connection issue. Please verify backend is running.', created_at: new Date().toISOString() }
      setChatMessages(prev => [...prev, errorMsg])
    } finally {
      setChatLoading(false)
    }
  }

  // --- 7. SATISFACTION SURVEY ---
  const handleRateSatisfaction = async (rating) => {
    if (!user) return
    setSatisfactionRating(rating)
    try {
      await fetch(`${API}/metrics/satisfaction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ learner_id: user.id, score: rating })
      })
      refreshUserData(user.id)
    } catch {}
  }

  // --- 8. CUSTOM QUESTION CREATION ---
  const handleCreateCustomQuestion = async (e) => {
    e.preventDefault()
    if (!user) return
    setCqStatus('Submitting question...')

    let testCases = []
    if (cqTestInput || cqTestExpected) {
      try {
        const parsedInput = JSON.parse(cqTestInput || '[]')
        const parsedExpected = JSON.parse(cqTestExpected || 'null')
        testCases.push({ input: Array.isArray(parsedInput) ? parsedInput : [parsedInput], expected: parsedExpected })
      } catch {
        testCases.push({ input: [cqTestInput], expected: cqTestExpected })
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
      })
      const created = await res.json()
      if (!res.ok) throw new Error(created.detail || 'Failed to create question.')

      setCqStatus('Success! Question added.')
      // Append to problems and launch
      setProblems(prev => [created, ...prev])
      selectProblem(created)
      setCurrentTab('practice')
    } catch (err) {
      setCqStatus('Error: ' + err.message)
    }
  }

  // --- COMPUTED / ACTIVE STATE ---
  const activeState = submitResult?.learner_state || {
    mastery: 0.35,
    confidence: 0.50,
    confusion: 0.20,
    cognitive_load: 0.30,
    progress: 0.0
  }

  const filteredProblems = problems.filter(p => {
    const term = problemSearch.toLowerCase()
    return p.title.toLowerCase().includes(term) || (p.topic && p.topic.toLowerCase().includes(term))
  })

  // --- IF NOT LOGGED IN: SHOW AUTHENTICATION VIEW ---
  if (!user) {
    return (
      <main className="auth-wrapper">
        <div className="auth-card">
          <div className="auth-header">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <Sparkles size={34} color="#0d9488" />
            </div>
            <h1>Adaptive AI Tutor</h1>
            <p>Personalized Multi-Agent Programming Lab</p>
          </div>

          <div className="auth-tabs">
            <button className={`auth-tab ${authMode === 'login' ? 'active' : ''}`} onClick={() => setAuthMode('login')}>
              Log In
            </button>
            <button className={`auth-tab ${authMode === 'register' ? 'active' : ''}`} onClick={() => setAuthMode('register')}>
              Create Account
            </button>
          </div>

          {authError && <div className="error-banner">{authError}</div>}

          <form onSubmit={handleAuth}>
            {authMode === 'register' && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  className="form-control"
                  type="text"
                  required
                  placeholder="Ada Lovelace"
                  value={authName}
                  onChange={e => setAuthName(e.target.value)}
                />
              </div>
            )}
            {authMode === 'register' && (
              <div className="form-group">
                <label>Account Type</label>
                <select 
                  className="form-control" 
                  value={authRole} 
                  onChange={e => setAuthRole(e.target.value)}
                  style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: '1px solid var(--border)' }}
                >
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                </select>
              </div>
            )}
            <div className="form-group">
              <label>Email Address</label>
              <input
                className="form-control"
                type="email"
                required
                placeholder="student@adaptive.edu"
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                className="form-control"
                type="password"
                required
                placeholder="••••••••"
                value={authPassword}
                onChange={e => setAuthPassword(e.target.value)}
              />
            </div>
            <button className="btn-primary" type="submit" disabled={authLoading}>
              {authLoading ? 'Authenticating...' : authMode === 'register' ? 'Register Account' : 'Sign In'}
            </button>
          </form>

          <button className="btn-demo-login" onClick={handleDemoLogin}>
            ⚡ Fast 1-Click Demo Login (Demo Student)
          </button>
        </div>
      </main>
    )
  }

  // --- LOGGED IN: RENDER COMPLETE APPLICATION PLATFORM ---
  return (
    <main>
      {/* 1. TOP NAVBAR */}
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

      {/* 2. BODY CONTENT ROUTER */}
      <div className="container">
        {currentTab === 'teacher' && <TeacherDashboard token={token} />}

        {/* --- TAB 1: STUDENT DASHBOARD --- */}
        {currentTab === 'dashboard' && (
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
                  const targetId = submitResult?.recommendation?.next_problem_id
                  const target = problems.find(p => p.id === targetId) || problems[0]
                  if (target) selectProblem(target)
                  setCurrentTab('practice')
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
                    const prog = conceptProgress[c.id]?.mastery ? Math.round(conceptProgress[c.id].mastery * 100) : 0
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
                          <div className="progress-fill" style={{ width: `${Math.max(5, prog)}%` }} />
                        </div>
                      </div>
                    )
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
                    <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.mastery * 100}%` }} /></div>
                  </div>
                  <div className="gauge-item">
                    <div className="gauge-header">
                      <span>Confidence Indicator</span>
                      <strong>{Math.round(activeState.confidence * 100)}%</strong>
                    </div>
                    <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.confidence * 100}%`, background: '#6366f1' }} /></div>
                  </div>
                  <div className="gauge-item">
                    <div className="gauge-header">
                      <span>Confusion Detection</span>
                      <strong>{Math.round(activeState.confusion * 100)}%</strong>
                    </div>
                    <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.confusion * 100}%`, background: '#f59e0b' }} /></div>
                  </div>
                  <div className="gauge-item">
                    <div className="gauge-header">
                      <span>Interaction Cognitive Load Proxy</span>
                      <strong>{Math.round(activeState.cognitive_load * 100)}%</strong>
                    </div>
                    <div className="progress-track"><div className="progress-fill" style={{ width: `${activeState.cognitive_load * 100}%`, background: '#ef4444' }} /></div>
                  </div>

                  <hr style={{ margin: '14px 0', border: '0', borderTop: '1px solid #e2e8f0' }} />

                  {/* Student Satisfaction Widget */}
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>Session Satisfaction Rating:</span>
                    <div className="satisfaction-widget">
                      {[1, 2, 3, 4, 5].map(star => (
                        <button
                          key={star}
                          className={`star-btn ${satisfactionRating >= star ? 'active' : ''}`}
                          onClick={() => handleRateSatisfaction(star)}
                          title={`Rate ${star} star`}
                        >
                          <Star size={20} fill={satisfactionRating >= star ? '#f59e0b' : 'none'} />
                        </button>
                      ))}
                      <span style={{ fontSize: 12, color: '#64748b', marginLeft: 6 }}>
                        {satisfactionRating ? `${satisfactionRating}/5 stars` : 'Tap to rate'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 2: CURRICULUM EXPLORER --- */}
        {currentTab === 'curriculum' && (
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
                            selectProblem(p)
                            setCurrentTab('practice')
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
        )}

        {/* --- TAB 3: PRACTICE LAB WORKSPACE --- */}
        {currentTab === 'practice' && (
          <div className="practice-layout">
            {/* Left: Problem Navigator */}
            <aside className="sidebar-problems">
              <input
                className="problem-search"
                type="text"
                placeholder="Search practice problems..."
                value={problemSearch}
                onChange={e => setProblemSearch(e.target.value)}
              />
              <div style={{ display: 'grid', gap: 4 }}>
                {filteredProblems.map(p => (
                  <button
                    key={p.id}
                    className={`problem-item-btn ${problem?.id === p.id ? 'active' : ''}`}
                    onClick={() => selectProblem(p)}
                  >
                    <div className="problem-item-title">{p.title}</div>
                    <div className="problem-item-meta">
                      <span className="pill source">{p.source || 'builtin'}</span>
                      <span className={`pill ${p.difficulty}`}>{p.difficulty}</span>
                    </div>
                  </button>
                ))}
              </div>
            </aside>

            {/* Center: Coding Workspace & Results */}
            <section className="workspace-center">
              {problem && (
                <div className="problem-header-card">
                  <div className="problem-header-top">
                    <div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                        <span className="pill source">{problem.source || 'builtin'}</span>
                        <span className={`pill ${problem.difficulty}`}>{problem.difficulty}</span>
                        <span style={{ fontSize: 12, color: '#64748b' }}>Topic: {problem.topic}</span>
                      </div>
                      <h1>{problem.title}</h1>
                      <p>{problem.description}</p>
                    </div>
                  </div>
                  {problem.expected_behavior && (
                    <div className="expected-box">
                      <strong>Expected: </strong>{problem.expected_behavior}
                    </div>
                  )}
                </div>
              )}

              {/* Monaco Code Editor */}
              <div className="editor-container">
                <div className="editor-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Code2 size={16} color="#38bdf8" />
                    <span>solution.py</span>
                  </div>
                  <div className="timer-tag">
                    <Timer size={15} />
                    <span>Active Time: {activeSeconds}s</span>
                  </div>
                </div>

                <Editor
                  height="340px"
                  defaultLanguage="python"
                  theme="vs-dark"
                  value={code}
                  onChange={val => {
                    setCode(val || '')
                    setSubmitResult(null)
                    setRunResult(null)
                  }}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    tabSize: 4,
                    automaticLayout: true
                  }}
                />

                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 12 }}>
                  <button className="run-button" onClick={handleRunCode} disabled={runLoading || submitLoading} style={{ background: '#475569' }}>
                    {runLoading ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
                    <span>Run Code</span>
                  </button>
                  <button className="run-button" onClick={handleSubmitCode} disabled={runLoading || submitLoading}>
                    {submitLoading ? (
                      <>
                        <RefreshCw size={16} className="spin" />
                        <span>LangGraph Agents Evaluating...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={16} />
                        <span>Submit Solution</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Run Feedback */}
              {runResult && !submitResult && (
                <div className={`agent-card ${runResult.passed ? 'passed' : 'failed'}`} style={{ marginTop: 16 }}>
                  <div className="agent-card-header">
                    {runResult.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
                    <span>Execution Output</span>
                  </div>
                  <div className="agent-card-body">
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'Fira Code, monospace', fontSize: 13 }}>{runResult.output}</pre>
                  </div>
                </div>
              )}

              {/* Multi-Agent Feedback Cards */}
              {submitResult && (
                <div className="feedback-grid">
                  {/* Card 1: Execution & Diagnostic Agent */}
                  <div className={`agent-card ${submitResult.execution.passed ? 'passed' : 'failed'}`}>
                    <div className="agent-card-header">
                      {submitResult.execution.passed ? <CheckCircle2 size={18} color="#10b981" /> : <XCircle size={18} color="#ef4444" />}
                      <span>Diagnostic Agent • {submitResult.execution.passed ? 'Verified Solution' : submitResult.diagnostic.error_type}</span>
                    </div>
                    <div className="agent-card-body">
                      <strong>{submitResult.execution.output}</strong>
                      <p style={{ marginTop: 6, color: '#475569' }}>{submitResult.diagnostic.explanation}</p>
                      {!submitResult.execution.passed && (
                        <>
                          <div style={{ marginTop: 8, fontSize: 12, color: '#b91c1c', background: '#fef2f2', padding: '6px 10px', borderRadius: 4 }}>
                            Misconception: {submitResult.diagnostic.misconception}
                          </div>
                          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                            <button className="btn-primary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => {
                              setSubmitResult(null)
                              setRunResult(null)
                              setActiveSeconds(0)
                              setIsTimerRunning(true)
                            }}>
                              Try Again
                            </button>
                            <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: 12, background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: 6, fontWeight: 500, cursor: 'pointer' }} onClick={() => {
                              setCode(problem.starter_code)
                              setSubmitResult(null)
                              setRunResult(null)
                              setActiveSeconds(0)
                              setIsTimerRunning(true)
                            }}>
                              Rewrite
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Card 2: Adaptive Scaffolding Agent */}
                  <div className="agent-card scaffolding">
                    <div className="agent-card-header">
                      <Lightbulb size={18} color="#0d9488" />
                      <span>Adaptive Scaffolding Agent • Level {submitResult.scaffolding?.level || 1}</span>
                    </div>
                    <div className="agent-card-body">
                      <p style={{ margin: 0, fontWeight: 600 }}>{submitResult.scaffolding?.hint}</p>
                      {submitResult.scaffolding?.intervention_applied && (
                        <div style={{ marginTop: 8, fontSize: 11, color: '#0369a1', background: '#f0f9ff', padding: '4px 8px', borderRadius: 4 }}>
                          ChromaDB Intervention: {submitResult.scaffolding.intervention_applied}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card 3: Reflection Agent */}
                  <div className="agent-card reflection" style={{ gridColumn: 'span 2' }}>
                    <div className="agent-card-header">
                      <BrainCircuit size={18} color="#6366f1" />
                      <span>Reflection Agent</span>
                    </div>
                    <div className="agent-card-body">
                      <p style={{ margin: 0, fontSize: 14, color: '#1e293b' }}>{submitResult.reflection}</p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Right Sidebar: Agent Pipeline Activity & Live Cognitive Signals */}
            <aside className="sidebar-right">
              <div className="card">
                <div className="card-header" style={{ marginBottom: 12 }}>
                  <h3 style={{ fontSize: 14 }}><BrainCircuit size={16} /> Multi-Agent Pipeline</h3>
                </div>
                <ul className="agent-checklist">
                  {['Diagnostic Agent', 'Learner State Agent', 'Similar Learner Retrieval Agent', 'Adaptive Scaffolding Agent', 'Reflection Agent', 'Learning Planner Agent'].map(name => {
                    const completed = submitResult?.agent_activity?.includes(name)
                    return (
                      <li key={name} className="agent-checklist-item" style={{ opacity: completed ? 1 : 0.6 }}>
                        {completed ? <Check size={16} color="#10b981" /> : <div style={{ width: 16, height: 16, borderRadius: '50%', border: '1px dashed #94a3b8' }} />}
                        <span>{name}</span>
                      </li>
                    )
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
                      const nextP = problems.find(p => p.id === submitResult.recommendation.next_problem_id)
                      if (nextP) selectProblem(nextP)
                    }}
                  >
                    Open Next Challenge
                  </button>
                </div>
              )}
            </aside>
          </div>
        )}

        {/* --- TAB 4: CONVERSATIONAL AI TUTOR --- */}
        {currentTab === 'tutor' && (
          <div className="chat-page-container">
            {/* Quick Prompts Column */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h3 style={{ fontSize: 15, margin: 0 }}><Lightbulb size={16} /> Suggested Inquiries</h3>
              <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>Ask general Python conceptual questions or get specific debugging hints.</p>
              
              <button className="problem-item-btn" onClick={() => handleSendChat('What is the difference between a list and a tuple in Python?')}>
                <div className="problem-item-title">List vs Tuple</div>
                <div className="problem-item-meta">Concepts & mutability</div>
              </button>
              <button className="problem-item-btn" onClick={() => handleSendChat('Can you explain recursion with a simple base case example?')}>
                <div className="problem-item-title">Explain Recursion</div>
                <div className="problem-item-meta">Functions & call stack</div>
              </button>
              <button className="problem-item-btn" onClick={() => handleSendChat('How does list comprehension work in Python?')}>
                <div className="problem-item-title">List Comprehensions</div>
                <div className="problem-item-meta">Idiomatic transformations</div>
              </button>
              <button className="problem-item-btn" onClick={() => handleSendChat(`Can you give me a Socratic hint for the problem '${problem?.title || 'current'}'?`)}>
                <div className="problem-item-title">Current Challenge Hint</div>
                <div className="problem-item-meta">Socratic guidance</div>
              </button>
            </div>

            {/* Chat Thread */}
            <div className="chat-thread-card">
              <div className="chat-thread-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Bot size={20} color="#0d9488" />
                  <strong style={{ fontSize: 15 }}>Socratic Python AI Tutor</strong>
                </div>
                <span style={{ fontSize: 12, color: '#64748b' }}>Persistent Conversation History</span>
              </div>

              <div className="chat-thread-body">
                {chatMessages.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#94a3b8', margin: 'auto' }}>
                    <Bot size={40} style={{ margin: '0 auto 12px auto', display: 'block', opacity: 0.5 }} />
                    <p>No messages yet. Ask me any general Python question or ask for help with your code!</p>
                  </div>
                ) : (
                  chatMessages.map(msg => (
                    <div key={msg.id} className={`chat-bubble ${msg.role}`}>
                      <div style={{ fontSize: 11, opacity: 0.8, marginBottom: 4, fontWeight: 700 }}>
                        {msg.role === 'user' ? 'You' : 'Tutor'}
                      </div>
                      <div>{msg.content}</div>
                    </div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="chat-input-bar">
                <input
                  type="text"
                  placeholder="Ask any Python question (e.g. 'What is a dictionary?', 'Why is my loop failing?')..."
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSendChat()}
                />
                <button onClick={() => handleSendChat()} disabled={chatLoading}>
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 5: LEARNING HISTORY --- */}
        {currentTab === 'history' && (
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
        )}

        {/* --- TAB 6: CREATE CUSTOM QUESTION --- */}
        {currentTab === 'create' && (
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
        )}
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
    </main>
  )
}
