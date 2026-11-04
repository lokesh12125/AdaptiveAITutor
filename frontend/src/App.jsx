import React, { useEffect, useRef, useState } from 'react';

// Import our new modular components
import AuthForm from './components/auth/AuthForm';
import TopHeader from './components/layout/TopHeader';
import DashboardPanel from './components/dashboard/DashboardPanel';
import TeacherDashboard from './components/dashboard/TeacherDashboard';
import CurriculumPanel from './components/curriculum/CurriculumPanel';
import PracticeLab from './components/practice/PracticeLab';
import ChatPanel from './components/tutor/ChatPanel';
import HistoryPanel from './components/history/HistoryPanel';
import CreateQuestionPanel from './components/authoring/CreateQuestionPanel';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('adaptive_tutor_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('adaptive_tutor_token') || '');

  // Global Navigation & Pre-fetched Data
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [expandedTopics, setExpandedTopics] = useState({ 'variables-01': true });
  const toggleTopic = (topic) => {
    setExpandedTopics(prev => ({ ...prev, [topic]: !prev[topic] }));
  };

  const [systemHealth, setSystemHealth] = useState({ backend: 'checking', llm: 'demo' });
  const [concepts, setConcepts] = useState([]);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [conceptPillar, setConceptPillar] = useState('All');
  const [conceptProgress, setConceptProgress] = useState({});

  const [problems, setProblems] = useState([]);
  const [problem, setProblem] = useState(null);
  const [problemSearch, setProblemSearch] = useState('');

  const [code, setCode] = useState('');
  const [activeSeconds, setActiveSeconds] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const timerRef = useRef(null);

  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [runLoading, setRunLoading] = useState(false);

  const [historyList, setHistoryList] = useState([]);
  const [evalMetrics, setEvalMetrics] = useState(null);
  const [satisfactionRating, setSatisfactionRating] = useState(0);
  const [recommendation, setRecommendation] = useState(null);
  const [sessionId, setSessionId] = useState(() => {
    try {
      const stored = sessionStorage.getItem('adaptive_tutor_session_id');
      return stored ? parseInt(stored, 10) : null;
    } catch {
      return null;
    }
  });
  const sessionStartingRef = useRef(false);

  const [chatMessages, setChatMessages] = useState([]);

  // --- 1. INITIAL SYSTEM LOAD & HEALTH CHECK ---
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(data => setSystemHealth(data))
      .catch(() => setSystemHealth({ backend: 'offline', llm: 'demo' }));

    const loadConcepts = () => {
      fetch(`${API}/concepts`)
        .then(r => r.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            setConcepts(data);
            setSelectedConcept(prev => prev || data[0]);
          }
        })
        .catch(() => {});
    };

    const loadProblems = () => {
      fetch(`${API}/problems`)
        .then(r => r.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            setProblems(data);
            setProblem(prev => {
              if (prev) return prev;
              setCode(data[0].starter_code);
              return data[0];
            });
            // Auto-expand all topics so practice problems are immediately visible
            const topicsMap = {};
            data.forEach(p => {
              const topicKey = p.concept_id || p.topic || 'general';
              topicsMap[topicKey] = true;
            });
            setExpandedTopics(topicsMap);
          }
        })
        .catch(() => {});
    };

    loadConcepts();
    loadProblems();
  }, []);

  // --- 2. USER DATA REFRESH ---
  const refreshUserData = (learnerId) => {
    if (!learnerId) return;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

    fetch(`${API}/learner/${learnerId}`, { headers: authHeaders })
      .then(r => r.json())
      .then(st => {
        if (submitResult) {
          setSubmitResult(prev => prev ? { ...prev, learner_state: st } : prev);
        }
      })
      .catch(() => {});

    fetch(`${API}/learner/${learnerId}/progress`, { headers: authHeaders })
      .then(r => r.json())
      .then(p => setConceptProgress(p))
      .catch(() => {});

    fetch(`${API}/learner/${learnerId}/history`, { headers: authHeaders })
      .then(r => r.json())
      .then(h => setHistoryList(h))
      .catch(() => {});

    fetch(`${API}/metrics/${learnerId}`, { headers: authHeaders })
      .then(r => r.json())
      .then(m => {
        setEvalMetrics(m);
        if (m.satisfaction_score) setSatisfactionRating(m.satisfaction_score);
      })
      .catch(() => {});

    fetch(`${API}/learner/${learnerId}/recommendation`, { headers: authHeaders })
      .then(r => r.json())
      .then(rec => setRecommendation(rec))
      .catch(() => {});

    fetch(`${API}/chat/${learnerId}`, { headers: authHeaders })
      .then(r => r.json())
      .then(msgs => setChatMessages(msgs))
      .catch(() => {});
  };

  useEffect(() => {
    if (user?.id) {
      refreshUserData(user.id);
    }
  }, [user]);

  // --- 2b. LEARNING SESSION LIFECYCLE ---
  useEffect(() => {
    if (!user?.id || !token || sessionId || sessionStartingRef.current) return;

    // Check if there is already a stored session for this user
    try {
      const storedUserId = sessionStorage.getItem('adaptive_tutor_session_user');
      const storedSessionId = sessionStorage.getItem('adaptive_tutor_session_id');
      if (storedUserId === user.id && storedSessionId) {
        setSessionId(parseInt(storedSessionId, 10));
        return;
      }
    } catch {}

    sessionStartingRef.current = true;
    fetch(`${API}/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ learner_id: user.id })
    })
      .then(r => r.json())
      .then(sess => {
        if (sess?.id) {
          setSessionId(sess.id);
          try {
            sessionStorage.setItem('adaptive_tutor_session_id', sess.id.toString());
            sessionStorage.setItem('adaptive_tutor_session_user', user.id);
          } catch {}
        }
      })
      .catch((err) => {
        console.warn('Session start error:', err);
      })
      .finally(() => {
        sessionStartingRef.current = false;
      });
  }, [user?.id, token, sessionId]);

  useEffect(() => {
    const handleUnload = () => {
      if (sessionId && token) {
        try {
          fetch(`${API}/sessions/${sessionId}/end`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            keepalive: true
          });
        } catch {
          navigator.sendBeacon?.(`${API}/sessions/${sessionId}/end`);
        }
      }
    };
    window.addEventListener('pagehide', handleUnload);
    window.addEventListener('beforeunload', handleUnload);
    return () => {
      window.removeEventListener('pagehide', handleUnload);
      window.removeEventListener('beforeunload', handleUnload);
    };
  }, [sessionId, token]);

  const handleEndSession = async () => {
    if (!sessionId || !token) return;
    try {
      await fetch(`${API}/sessions/${sessionId}/end`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (e) {
      console.warn('Error ending session:', e);
    } finally {
      try {
        sessionStorage.removeItem('adaptive_tutor_session_id');
        sessionStorage.removeItem('adaptive_tutor_session_user');
      } catch {}
      setSessionId(null);
    }
  };

  // --- 3. RESPONSE TIME STOPWATCH ---
  useEffect(() => {
    if (isTimerRunning) {
      timerRef.current = setInterval(() => {
        setActiveSeconds(s => s + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isTimerRunning]);

  useEffect(() => {
    if (currentTab === 'practice' && problem && !submitLoading) {
      setIsTimerRunning(true);
    }
  }, [currentTab, problem, submitLoading]);

  const selectProblem = (prob) => {
    setProblem(prob);
    setCode(prob.starter_code);
    setSubmitResult(null);
    setActiveSeconds(0);
    setIsTimerRunning(true);
  };

  const handleLogout = () => {
    if (sessionId && token) {
      fetch(`${API}/sessions/${sessionId}/end`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      }).catch(() => {});
    }
    try {
      sessionStorage.removeItem('adaptive_tutor_session_id');
      sessionStorage.removeItem('adaptive_tutor_session_user');
    } catch {}
    localStorage.removeItem('adaptive_tutor_token');
    localStorage.removeItem('adaptive_tutor_user');
    setUser(null);
    setToken('');
    setSessionId(null);
    setSubmitResult(null);
    setRecommendation(null);
  };

  const handleRunCode = async () => {
    if (!problem || !user || runLoading || submitLoading) return;
    setRunLoading(true);
    setRunResult(null);
    setSubmitResult(null);

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
      });
      const data = await res.json();
      if (!res.ok) {
        setRunResult({
          passed: false,
          error: data.detail || 'Execution service returned an error.',
          output: data.detail || 'Execution error.'
        });
      } else {
        setRunResult(data.execution);
      }
    } catch (err) {
      setRunResult({
        passed: false,
        error: err.message,
        output: `Network/Backend error: ${err.message}`
      });
    } finally {
      setRunLoading(false);
    }
  };

  const handleSubmitCode = async () => {
    if (!problem || !user || submitLoading || runLoading) return;
    setSubmitLoading(true);
    setRunResult(null);
    setIsTimerRunning(false);
    const responseTime = Math.max(1.0, activeSeconds);

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
          response_time: responseTime,
          session_id: sessionId
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setSubmitResult({
          evaluation: {
            passed: false,
            feedback: data.detail || 'Evaluation failed.',
            tests_passed: 0,
            tests_total: problem.tests?.length || 1,
            test_results: []
          },
          pedagogical_guidance: 'An error occurred during evaluation. Please verify your connection or try again.'
        });
      } else {
        setSubmitResult(data);
        refreshUserData(user.id);
      }
    } catch (err) {
      setSubmitResult({
        evaluation: {
          passed: false,
          feedback: `Submission communication error: ${err.message}`,
          tests_passed: 0,
          tests_total: problem.tests?.length || 1,
          test_results: []
        },
        pedagogical_guidance: `Failed to communicate with tutor backend: ${err.message}`
      });
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleRateSatisfaction = async (rating) => {
    if (!user) return;
    setSatisfactionRating(rating);
    try {
      await fetch(`${API}/metrics/satisfaction`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ learner_id: user.id, score: rating })
      });
      refreshUserData(user.id);
    } catch {}
  };

  const activeState = submitResult?.learner_state || {
    mastery: 0.35,
    confidence: 0.50,
    confusion: 0.10,
    cognitive_load: 0.40,
    progress: 0.20
  };

  const filteredProblems = problems.filter(p => {
    const term = problemSearch.toLowerCase();
    return p.title.toLowerCase().includes(term) || (p.topic && p.topic.toLowerCase().includes(term));
  });

  if (!user) {
    return (
      <AuthForm 
        onLogin={(userData, userToken) => {
          localStorage.setItem('adaptive_tutor_token', userToken);
          localStorage.setItem('adaptive_tutor_user', JSON.stringify(userData));
          setToken(userToken);
          setUser(userData);
          refreshUserData(userData.id);
        }} 
      />
    );
  }

  return (
    <main>
      <TopHeader 
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        user={user}
        systemHealth={systemHealth}
        handleLogout={handleLogout}
        setIsTimerRunning={setIsTimerRunning}
        sessionId={sessionId}
        handleEndSession={handleEndSession}
      />

      <div className="container">
        {currentTab === 'teacher' && <TeacherDashboard token={token} />}

        {currentTab === 'dashboard' && (
          <DashboardPanel 
            user={user}
            activeState={activeState}
            evalMetrics={evalMetrics}
            submitResult={submitResult}
            recommendation={recommendation}
            problems={problems}
            selectProblem={selectProblem}
            setCurrentTab={setCurrentTab}
            concepts={concepts}
            conceptProgress={conceptProgress}
            setSelectedConcept={setSelectedConcept}
            satisfactionRating={satisfactionRating}
            setSatisfactionRating={handleRateSatisfaction}
            historyList={historyList}
          />
        )}

        {currentTab === 'curriculum' && (
          <CurriculumPanel 
            concepts={concepts}
            problems={problems}
            conceptPillar={conceptPillar}
            setConceptPillar={setConceptPillar}
            selectedConcept={selectedConcept}
            setSelectedConcept={setSelectedConcept}
            selectProblem={selectProblem}
            setCurrentTab={setCurrentTab}
          />
        )}

        {currentTab === 'practice' && (
          <PracticeLab 
            problemSearch={problemSearch}
            setProblemSearch={setProblemSearch}
            filteredProblems={filteredProblems}
            expandedTopics={expandedTopics}
            toggleTopic={toggleTopic}
            problem={problem}
            selectProblem={selectProblem}
            code={code}
            setCode={setCode}
            activeSeconds={activeSeconds}
            setActiveSeconds={setActiveSeconds}
            setIsTimerRunning={setIsTimerRunning}
            runLoading={runLoading}
            submitLoading={submitLoading}
            handleRunCode={handleRunCode}
            handleSubmitCode={handleSubmitCode}
            runResult={runResult}
            setRunResult={setRunResult}
            submitResult={submitResult}
            setSubmitResult={setSubmitResult}
            problems={problems}
          />
        )}

        {currentTab === 'tutor' && (
          <ChatPanel 
            user={user}
            token={token}
            problem={problem}
            initialMessages={chatMessages}
          />
        )}

        {currentTab === 'history' && (
          <HistoryPanel historyList={historyList} />
        )}

        {currentTab === 'create' && (
          <CreateQuestionPanel 
            user={user}
            token={token}
            concepts={concepts}
            setProblems={setProblems}
            selectProblem={selectProblem}
            setCurrentTab={setCurrentTab}
          />
        )}
      </div>
    </main>
  );
}
