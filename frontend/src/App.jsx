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

  const [chatMessages, setChatMessages] = useState([]);

  // --- 1. INITIAL SYSTEM LOAD & HEALTH CHECK ---
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(data => setSystemHealth(data))
      .catch(() => setSystemHealth({ backend: 'offline', llm: 'demo' }));

    fetch(`${API}/concepts`)
      .then(r => r.json())
      .then(data => {
        setConcepts(data);
        if (data.length > 0) setSelectedConcept(data[0]);
      })
      .catch(() => {});

    fetch(`${API}/problems`)
      .then(r => r.json())
      .then(data => {
        setProblems(data);
        if (data.length > 0 && !problem) {
          setProblem(data[0]);
          setCode(data[0].starter_code);
        }
      })
      .catch(() => {});
  }, []);

  // --- 2. USER DATA REFRESH ---
  const refreshUserData = (learnerId) => {
    if (!learnerId) return;
    fetch(`${API}/learner/${learnerId}`)
      .then(r => r.json())
      .then(st => {
        if (submitResult) {
          setSubmitResult(prev => prev ? { ...prev, learner_state: st } : prev);
        }
      })
      .catch(() => {});

    fetch(`${API}/learner/${learnerId}/progress`)
      .then(r => r.json())
      .then(p => setConceptProgress(p))
      .catch(() => {});

    fetch(`${API}/learner/${learnerId}/history`)
      .then(r => r.json())
      .then(h => setHistoryList(h))
      .catch(() => {});

    fetch(`${API}/metrics/${learnerId}`)
      .then(r => r.json())
      .then(m => {
        setEvalMetrics(m);
        if (m.satisfaction_score) setSatisfactionRating(m.satisfaction_score);
      })
      .catch(() => {});

    fetch(`${API}/chat/${learnerId}`)
      .then(r => r.json())
      .then(msgs => setChatMessages(msgs))
      .catch(() => {});
  };

  useEffect(() => {
    if (user?.id) {
      refreshUserData(user.id);
    }
  }, [user]);

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

  const selectProblem = (prob) => {
    setProblem(prob);
    setCode(prob.starter_code);
    setSubmitResult(null);
    setActiveSeconds(0);
    setIsTimerRunning(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('adaptive_tutor_token');
    localStorage.removeItem('adaptive_tutor_user');
    setUser(null);
    setToken('');
    setSubmitResult(null);
  };

  const handleRunCode = async () => {
    if (!problem || !user) return;
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
      setRunResult(data.execution);
    } catch (err) {
      alert('Failed to run code: ' + err.message);
    } finally {
      setRunLoading(false);
    }
  };

  const handleSubmitCode = async () => {
    if (!problem || !user) return;
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
          response_time: responseTime
        })
      });
      const data = await res.json();
      setSubmitResult(data);
      refreshUserData(user.id);
    } catch (err) {
      alert('Failed to communicate with tutor backend: ' + err.message);
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
        headers: { 'Content-Type': 'application/json' },
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
      />

      <div className="container">
        {currentTab === 'teacher' && <TeacherDashboard token={token} />}

        {currentTab === 'dashboard' && (
          <DashboardPanel 
            user={user}
            activeState={activeState}
            evalMetrics={evalMetrics}
            submitResult={submitResult}
            problems={problems}
            selectProblem={selectProblem}
            setCurrentTab={setCurrentTab}
            concepts={concepts}
            conceptProgress={conceptProgress}
            setSelectedConcept={setSelectedConcept}
            satisfactionRating={satisfactionRating}
            setSatisfactionRating={handleRateSatisfaction}
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
