import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function AuthForm({ onLogin }) {
  const [authMode, setAuthMode] = useState('login');
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authRole, setAuthRole] = useState('student');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);

    const endpoint = authMode === 'register' ? `${API}/auth/register` : `${API}/auth/login`;
    const payload = authMode === 'register' 
      ? { email: authEmail, password: authPassword, full_name: authName, role: authRole }
      : { email: authEmail, password: authPassword };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Authentication failed');
      
      onLogin(data.user, data.token);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleDemoLogin = () => {
    setAuthEmail('demo@student.edu');
    setAuthPassword('demo123');
    setAuthMode('login');
    // We don't automatically submit here to let them see it, or we could trigger login
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
  );
}
