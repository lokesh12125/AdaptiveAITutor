import React, { useState } from 'react';
import { Sparkles, Eye, EyeOff, ShieldCheck, Key } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function AuthForm({ onLogin }) {
  const [authMode, setAuthMode] = useState('login');
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authRole, setAuthRole] = useState('student');
  const [authInviteCode, setAuthInviteCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  const executeLogin = async (email, password) => {
    setAuthError('');
    setAuthLoading(true);
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Authentication failed. Please check your credentials.');
      onLogin(data.user, data.token);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');

    const emailTrimmed = authEmail.trim();
    if (!emailTrimmed.includes('@') || !emailTrimmed.includes('.')) {
      setAuthError('Please enter a valid email address.');
      return;
    }

    if (authPassword.length < 6) {
      setAuthError('Password must be at least 6 characters.');
      return;
    }

    if (authMode === 'login') {
      await executeLogin(emailTrimmed, authPassword);
      return;
    }

    // Register flow
    setAuthLoading(true);
    const payload = {
      name: authName.trim(),
      full_name: authName.trim(),
      email: emailTrimmed,
      password: authPassword,
      role: authRole,
      ...(authRole === 'teacher' ? { invite_code: authInviteCode.trim() } : {})
    };

    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Registration failed');
      onLogin(data.user, data.token);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  // 1-Click Instant Demo Logins
  const handleStudentDemoClick = () => {
    setAuthEmail('demo@student.edu');
    setAuthPassword('demo123');
    setAuthMode('login');
    executeLogin('demo@student.edu', 'demo123');
  };

  const handleTeacherDemoClick = () => {
    setAuthEmail('teacher@adaptive.edu');
    setAuthPassword('teacher123');
    setAuthMode('login');
    executeLogin('teacher@adaptive.edu', 'teacher123');
  };

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
          <button 
            type="button"
            className={`auth-tab ${authMode === 'login' ? 'active' : ''}`} 
            onClick={() => { setAuthMode('login'); setAuthError(''); }}
          >
            Log In
          </button>
          <button 
            type="button"
            className={`auth-tab ${authMode === 'register' ? 'active' : ''}`} 
            onClick={() => { setAuthMode('register'); setAuthError(''); }}
          >
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
                <option value="student">Student (Programming Practice & AI Guidance)</option>
                <option value="teacher">Teacher (Cohort Analytics & Student Drilldown)</option>
              </select>
            </div>
          )}

          {authMode === 'register' && authRole === 'teacher' && (
            <div className="form-group" style={{ background: '#f0fdfa', padding: 12, borderRadius: 6, border: '1px solid #99f6e4' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#0f766e' }}>
                <Key size={14} /> Teacher Invitation Key
              </label>
              <input
                className="form-control"
                type="text"
                required
                placeholder="e.g. TEACH-2026-ADAPTIVE"
                value={authInviteCode}
                onChange={e => setAuthInviteCode(e.target.value)}
              />
              <small style={{ color: '#0d9488', fontSize: 11, marginTop: 4, display: 'block' }}>
                Required for faculty access. Default key: <code>TEACH-2026-ADAPTIVE</code>
              </small>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label style={{ margin: 0 }}>Password</label>
              <button
                type="button"
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                <span>{showPassword ? 'Hide' : 'Show'}</span>
              </button>
            </div>
            <input
              className="form-control"
              type={showPassword ? 'text' : 'password'}
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

        <div style={{ marginTop: 18, borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
          <div style={{ fontSize: 12, textAlign: 'center', color: '#64748b', marginBottom: 10, fontWeight: 600 }}>
            ⚡ Instant Evaluation Accounts:
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className="btn-demo-login" 
              type="button" 
              onClick={handleStudentDemoClick} 
              disabled={authLoading}
              style={{ flex: 1, marginTop: 0 }}
            >
              ⚡ Student Demo
            </button>
            <button 
              className="btn-demo-login" 
              type="button" 
              onClick={handleTeacherDemoClick} 
              disabled={authLoading}
              style={{ flex: 1, marginTop: 0 }}
            >
              🎓 Teacher Demo
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
