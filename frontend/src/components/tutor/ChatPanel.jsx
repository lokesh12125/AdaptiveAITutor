import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
const API = `${API_BASE}/api`;

export default function ChatPanel({ user, token, problem, initialMessages = [] }) {
  const [chatMessages, setChatMessages] = useState(initialMessages);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Update messages if parent fetches them
  useEffect(() => {
    setChatMessages(initialMessages);
  }, [initialMessages]);

  const handleSendChat = async (presetText) => {
    const textToSend = presetText || chatInput;
    if (!textToSend.trim() || !user) return;
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
      const assistantMsg = { id: Date.now() + 1, role: 'assistant', content: data.reply, created_at: new Date().toISOString() };
      setChatMessages(prev => [...prev, assistantMsg]);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch {
      const errorMsg = { id: Date.now() + 1, role: 'assistant', content: 'Connection issue. Please verify backend is running.', created_at: new Date().toISOString() };
      setChatMessages(prev => [...prev, errorMsg]);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } finally {
      setChatLoading(false);
    }
  };

  return (
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
  );
}
