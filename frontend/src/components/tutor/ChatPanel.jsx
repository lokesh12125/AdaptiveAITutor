import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, Sparkles, Copy, Check, RefreshCw } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function ChatPanel({ user, token, problem, initialMessages = [] }) {
  const [chatMessages, setChatMessages] = useState(initialMessages);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [copiedMsgId, setCopiedMsgId] = useState(null);
  const chatEndRef = useRef(null);

  // Update messages if parent fetches them
  useEffect(() => {
    setChatMessages(initialMessages);
  }, [initialMessages]);

  const copyMessage = (text, id) => {
    try {
      navigator.clipboard?.writeText(text);
      setCopiedMsgId(id);
      setTimeout(() => setCopiedMsgId(null), 2000);
    } catch (e) {
      console.warn('Copy failed', e);
    }
  };

  const handleSendChat = async (presetText) => {
    const textToSend = (presetText || chatInput).trim();
    if (!textToSend || !user || chatLoading) return;
    if (!presetText) setChatInput('');
    setChatLoading(true);

    // Optimistic user bubble
    const userMsg = { id: Date.now(), role: 'user', content: textToSend, created_at: new Date().toISOString() };
    setChatMessages(prev => [...prev, userMsg]);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);

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
      });
      const data = await res.json();
      const assistantMsg = { 
        id: Date.now() + 1, 
        role: 'assistant', 
        content: data.reply || 'Let me help you understand that concept.', 
        created_at: new Date().toISOString() 
      };
      setChatMessages(prev => [...prev, assistantMsg]);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch {
      const errorMsg = { 
        id: Date.now() + 1, 
        role: 'assistant', 
        content: 'Connection issue. Please verify backend is running on http://127.0.0.1:8001.', 
        created_at: new Date().toISOString() 
      };
      setChatMessages(prev => [...prev, errorMsg]);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } finally {
      setChatLoading(false);
    }
  };

  const quickPrompts = problem ? [
    `💡 Socratic clue for ${problem.title}`,
    "🔍 Why might this produce an IndexError?",
    "⏱️ What is the optimal Big-O complexity?",
    "🧩 Explain Python list comprehensions",
    "🔄 How does recursion differ from iteration?"
  ] : [
    "🧩 Explain Python list comprehensions with an example",
    "📚 How do Python dictionaries handle lookups in O(1)?",
    "🔍 What causes an IndexError in Python?",
    "⏱️ Explain Big-O notation simply",
    "🔄 When should I use recursion vs a while loop?"
  ];

  return (
    <div className="chat-thread-card">
      <div className="chat-thread-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Bot size={20} color="#0d9488" />
          <strong style={{ fontSize: 15 }}>Socratic Python AI Tutor</strong>
        </div>
        <span style={{ fontSize: 12, color: '#64748b' }}>
          {problem ? `Context: ${problem.title}` : 'General Programming Inquiry'}
        </span>
      </div>

      {/* Suggested Quick Prompt Chips */}
      <div className="chat-chips-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, fontSize: 11, fontWeight: 700, color: '#64748b' }}>
          <Sparkles size={13} color="#0d9488" />
          <span>Quick Learning Prompts:</span>
        </div>
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
          {quickPrompts.map((qp, idx) => (
            <button
              key={idx}
              className="chat-chip-btn"
              onClick={() => handleSendChat(qp)}
              disabled={chatLoading}
            >
              {qp}
            </button>
          ))}
        </div>
      </div>

      <div className="chat-thread-body">
        {chatMessages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#94a3b8', margin: 'auto', padding: '24px 16px' }}>
            <Bot size={44} style={{ margin: '0 auto 12px auto', display: 'block', opacity: 0.6, color: '#0d9488' }} />
            <h4 style={{ margin: '0 0 6px 0', color: '#334155', fontSize: 15 }}>Ask Your AI Tutor Anything</h4>
            <p style={{ margin: 0, fontSize: 13, maxWidth: 380, lineHeight: 1.5 }}>
              Ask a conceptual Python question, debug an error message, or explore algorithmic approaches without spoiling solutions.
            </p>
          </div>
        ) : (
          chatMessages.map(msg => (
            <div key={msg.id} className={`chat-bubble ${msg.role}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, opacity: 0.85, marginBottom: 4, fontWeight: 700 }}>
                <span>{msg.role === 'user' ? 'You' : 'Socratic Tutor'}</span>
                {msg.role === 'assistant' && (
                  <button
                    className="btn-copy-bubble"
                    onClick={() => copyMessage(msg.content, msg.id)}
                    title="Copy response"
                  >
                    {copiedMsgId === msg.id ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
                {msg.content}
              </div>
            </div>
          ))
        )}

        {/* Live Typing Indicator */}
        {chatLoading && (
          <div className="chat-bubble assistant typing">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748b', fontSize: 12 }}>
              <RefreshCw size={14} className="spin" color="#0d9488" />
              <span>Tutor is formulating a Socratic explanation...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-bar">
        <input
          type="text"
          placeholder="Ask any Python question (e.g. 'What is a dictionary?', 'Why is my loop failing?')..."
          value={chatInput}
          onChange={e => setChatInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendChat()}
          disabled={chatLoading}
        />
        <button onClick={() => handleSendChat()} disabled={chatLoading || !chatInput.trim()}>
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
