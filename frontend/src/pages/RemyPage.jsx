import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function RemyPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const bottomRef = useRef(null);
  const chatRef = useRef(null);

  useEffect(() => {
    Promise.all([
      api.listRemyQueries(),
      api.listRemyTasks(),
      api.listRemyRuns({ limit: 5 }),
      api.listRemyListings({ limit: 5 }),
      api.listRemyThreads(),
    ])
      .then(([d1, d2, d3, d4, d5]) => {
        setStatus({
          queries: d1.queries || [],
          tasks: d2.tasks || [],
          runs: d3.runs || [],
          recentListings: d4.listings || [],
        });
        setThreads(d5.threads || []);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  async function handleSend() {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setStreaming(true);
    setStreamingText('');
    try {
      await api.streamRemyChat(text, activeThread, (event) => {
        if (event.type === 'delta') {
          setStreamingText((prev) => prev + event.content);
        } else if (event.type === 'done') {
          setStreamingText((prev) => {
            setMessages((msgs) => [...msgs, { role: 'assistant', content: prev }]);
            return '';
          });
          setStreaming(false);
          if (event.thread_id) setActiveThread(event.thread_id);
          api.listRemyThreads().then((d) => setThreads(d.threads || []));
        } else if (event.type === 'error') {
          setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${event.detail}` }]);
          setStreamingText('');
          setStreaming(false);
        }
      });
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
      setStreamingText('');
      setStreaming(false);
    }
  }

  async function loadThread(threadId) {
    if (!threadId) {
      setMessages([]);
      setActiveThread(null);
      return;
    }
    try {
      const data = await api.getRemyThread(threadId);
      setMessages(data.thread?.messages || []);
      setActiveThread(threadId);
    } catch {
      setMessages([]);
      setActiveThread(null);
    }
  }

  async function deleteThread(threadId) {
    try {
      await api.deleteRemyThread(threadId);
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
      if (activeThread === threadId) {
        setActiveThread(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (loading) return <LoadingSpinner text="Loading Remy dashboard..." />;

  const { queries, tasks, runs, recentListings } = status || {};

  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="page-header">
        <h1>Remy Dashboard</h1>
        <p>Your AI job-search agent. Chat, monitor, and take action.</p>
      </div>

      <div className="grid-2 mb-3" ref={chatRef}>
        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Status</h3>
          <div className="inline-row mb-1 gap-1 text-sm">
            <span className="badge badge-new">{queries?.length || 0} profiles</span>
            <span className="badge badge-tailored">{tasks?.length || 0} tasks</span>
            <span className="badge badge-exported">{recentListings?.length || 0} listings</span>
          </div>
          {tasks?.length > 0 && (
            <div className="mt-2">
              <h4 className="text-sm text-secondary" style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                Scheduled Tasks
              </h4>
              {tasks.slice(0, 5).map((t) => (
                <div key={t.id} className="text-sm text-secondary" style={{ padding: '0.125rem 0' }}>
                  {t.type} — {t.frequency}{t.frequency === 'weekly' ? ` (day ${t.day_of_week})` : ''} at {t.time}
                  {!t.enabled && ' [disabled]'}
                </div>
              ))}
            </div>
          )}
          {runs?.length > 0 && (
            <div className="mt-2">
              <h4 className="text-sm text-secondary" style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                Recent Runs
              </h4>
              {runs.map((r) => (
                <div key={r.id} className="text-sm text-secondary" style={{ padding: '0.125rem 0' }}>
                  <span className={`badge badge-${r.status === 'success' ? 'exported' : r.status === 'failed' ? 'new' : 'tailoring'} text-sm`} style={{ textTransform: 'lowercase' }}>
                    {r.status}
                  </span>
                  {' '}{r.trigger} · {r.listings_found} found
                  {r.error ? ` · ${r.error.slice(0, 60)}` : ''}
                </div>
              ))}
            </div>
          )}
          <div className="mt-2">
            <Link to="/remy/queries" className="btn btn-secondary btn-sm">Manage Queries</Link>
            {' '}
            <Link to="/remy/tasks" className="btn btn-secondary btn-sm">Manage Tasks</Link>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div className="flex-between">
            <h3 style={{ fontSize: '1rem' }}>Chat with Remy</h3>
            <div className="inline-row gap-1 text-sm">
              {activeThread && (
                <button className="btn btn-secondary btn-sm" onClick={() => loadThread(null)}>New</button>
              )}
            </div>
          </div>

          {threads.length > 0 && (
            <div className="inline-row gap-1 text-sm" style={{ flexWrap: 'wrap' }}>
              {threads.map((t) => (
                <div key={t.thread_id} className="inline-row gap-1">
                  <button
                    className="btn btn-sm"
                    style={{
                      background: activeThread === t.thread_id ? 'var(--color-primary)' : 'var(--color-bg)',
                      color: activeThread === t.thread_id ? 'white' : 'var(--color-text)',
                      border: '1px solid var(--color-border)',
                    }}
                    onClick={() => loadThread(t.thread_id)}
                  >
                    {t.title || t.thread_id}
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    style={{ fontSize: '0.75rem', padding: '0.15rem 0.4rem' }}
                    onClick={() => deleteThread(t.thread_id)}
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          )}

          <div
            className="chat-messages"
            style={{
              flex: 1,
              minHeight: '300px',
              maxHeight: '400px',
              overflowY: 'auto',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              padding: '0.75rem',
              background: 'var(--color-bg)',
            }}
          >
            {messages.length === 0 && !streaming && (
              <p className="text-sm text-secondary" style={{ textAlign: 'center', padding: '2rem' }}>
                Ask Remy about your job search, market trends, or CV improvements.
              </p>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble ${msg.role}`}>
                <div className="chat-role">{msg.role === 'assistant' ? 'Remy' : 'You'}</div>
                <div className="chat-content">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            {streaming && (
              <div className="chat-bubble assistant">
                <div className="chat-role">Remy</div>
                <div className="chat-content">
                  {streamingText ? (
                    <ReactMarkdown>{streamingText}</ReactMarkdown>
                  ) : (
                    <div className="typing-indicator">
                      <span className="dot" />
                      <span className="dot" />
                      <span className="dot" />
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            className="chat-input-row"
            style={{ padding: 0 }}
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          >
            <input
              type="text"
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Remy a question..."
              disabled={streaming}
            />
            <button type="submit" className="btn btn-primary" disabled={streaming || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}