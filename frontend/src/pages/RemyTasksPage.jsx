import { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const EMPTY_TASK = {
  query_id: '',
  type: 'scrape',
  frequency: 'daily',
  day_of_week: 1,
  time: '09:00',
  enabled: true,
};

function RemyTaskForm({ task, queries, onSave, onCancel, saving, error }) {
  const [form, setForm] = useState({ ...EMPTY_TASK, ...task });

  function set(field, value) { setForm((prev) => ({ ...prev, [field]: value })); }

  return (
    <div className="card mb-3">
      <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>{form.id ? 'Edit Task' : 'New Task'}</h3>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
        <div className="form-group">
          <label>Search Profile *</label>
          <select value={form.query_id} onChange={(e) => set('query_id', e.target.value)}>
            <option value="">— select —</option>
            {queries.map((q) => (
              <option key={q.id} value={q.id}>{q.name || 'unnamed'}</option>
            ))}
          </select>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label>Task type</label>
            <select value={form.type} onChange={(e) => set('type', e.target.value)}>
              <option value="scrape">Scrape listings</option>
              <option value="analyze">Market analysis</option>
              <option value="recommend">Recommendations</option>
            </select>
          </div>
          <div className="form-group">
            <label>Frequency</label>
            <select value={form.frequency} onChange={(e) => set('frequency', e.target.value)}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
        </div>
        {form.frequency === 'weekly' && (
          <div className="form-group">
            <label>Day of week</label>
            <select value={form.day_of_week} onChange={(e) => set('day_of_week', parseInt(e.target.value, 10))}>
              {DAYS.map((d, i) => (
                <option key={i} value={i}>{d}</option>
              ))}
            </select>
          </div>
        )}
        <div className="form-group">
          <label>Time</label>
          <input type="time" value={form.time} onChange={(e) => set('time', e.target.value)} />
        </div>
        <div className="form-group inline-row gap-1">
          <input
            type="checkbox"
            id="task-enabled"
            checked={form.enabled}
            onChange={(e) => set('enabled', e.target.checked)}
            style={{ width: 'auto' }}
          />
          <label htmlFor="task-enabled" style={{ marginBottom: 0, cursor: 'pointer' }}>Enabled</label>
        </div>
        <div className="inline-row gap-1">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : form.id ? 'Save Changes' : 'Create Task'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export default function RemyTasksPage() {
  const [tasks, setTasks] = useState([]);
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [runningId, setRunningId] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    Promise.all([api.listRemyTasks(), api.listRemyQueries()])
      .then(([d1, d2]) => {
        setTasks(d1.tasks || []);
        setQueries(d2.queries || []);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  async function handleRun(task) {
    setRunningId(task.id);
    setActionMsg(null);
    try {
      const data = await api.runRemyTask(task.id);
      setActionMsg(`Task "${data.run.type}" ran (status: ${data.run.status})`);
    } catch (err) {
      setActionMsg(`Run failed: ${err.message}`);
    }
    setRunningId(null);
  }

  async function handleSave(formData) {
    setSaving(true);
    setFormError(null);
    try {
      if (editingTask) {
        const data = await api.updateRemyTask(editingTask, formData);
        setTasks((prev) => prev.map((t) => (t.id === editingTask ? data.task : t)));
      } else {
        const data = await api.createRemyTask(formData);
        setTasks((prev) => [...prev, data.task]);
      }
      setShowForm(false);
      setEditingTask(null);
    } catch (err) {
      setFormError(err.message);
    }
    setSaving(false);
  }

  async function handleDelete(task) {
    if (!confirm('Delete this task?')) return;
    try {
      await api.deleteRemyTask(task.id);
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (err) {
      setError(err.message);
    }
  }

  function getQueryName(qId) {
    const q = queries.find((x) => x.id === qId);
    return q ? q.name || 'unnamed' : qId || '—';
  }

  if (loading) return <LoadingSpinner text="Loading tasks..." />;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Remy — Scheduled Tasks</h1>
          <p>Automated scraping, analysis, and recommendations.</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setShowForm(!showForm); setEditingTask(null); setFormError(null); }}>
          {showForm ? 'Cancel' : 'New Task'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-info">{actionMsg}</div>}

      {showForm && (
        <RemyTaskForm
          task={null}
          queries={queries}
          onSave={handleSave}
          onCancel={() => { setShowForm(false); setEditingTask(null); }}
          saving={saving}
          error={formError}
        />
      )}

      {editingTask && !showForm && (
        <RemyTaskForm
          task={tasks.find((t) => t.id === editingTask)}
          queries={queries}
          onSave={(f) => handleSave(f)}
          onCancel={() => setEditingTask(null)}
          saving={saving}
          error={formError}
        />
      )}

      {tasks.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No tasks yet</h3>
            <p>Create a task to schedule automated scraping, analysis, or recommendations.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {tasks.map((t) => (
            <div key={t.id} className="card flex-between" style={{ padding: '1rem' }}>
              <div>
                <div className="inline-row gap-1 mb-1">
                  <strong style={{ fontSize: '0.875rem' }}>{t.type}</strong>
                  <span className="badge badge-new text-sm">{t.frequency}</span>
                  {t.frequency === 'weekly' && <span className="text-sm text-secondary">{DAYS[t.day_of_week]}</span>}
                  <span className="text-sm text-secondary">at {t.time}</span>
                  {!t.enabled && <span className="badge badge-new" style={{ background: '#fee2e2', color: '#991b1b' }}>disabled</span>}
                </div>
                <p className="text-sm text-secondary">Profile: {getQueryName(t.query_id)}</p>
              </div>
              <div className="inline-row gap-1">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleRun(t)}
                  disabled={runningId === t.id}
                >
                  {runningId === t.id ? 'Running...' : 'Run now'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setEditingTask(t.id)}>Edit</button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(t)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
