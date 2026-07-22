import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function PositionsPage() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showUrlForm, setShowUrlForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');

  const [form, setForm] = useState({
    company_name: '',
    job_title: '',
    job_description_md: '',
    job_source_url: '',
    job_source_type: 'paste',
  });

  const [urlForm, setUrlForm] = useState({ url: '' });

  useEffect(() => {
    loadPositions();
  }, []);

  async function loadPositions() {
    try {
      const data = await api.listPositions();
      setPositions(data.positions || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const data = await api.createPosition(form);
      setPositions(prev => [...prev, data.position]);
      setShowForm(false);
      setForm({ company_name: '', job_title: '', job_description_md: '', job_source_url: '', job_source_type: 'paste' });
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  async function handleUrlIngest(e) {
    e.preventDefault();
    if (!urlForm.url.trim()) {
      setError('Please enter a URL.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data = await api.ingestUrl(urlForm);
      setPositions(prev => [...prev, data.position]);
      setShowUrlForm(false);
      setUrlForm({ url: '' });
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  async function handleDelete(id) {
    if (!confirm('Delete this position?')) return;
    try {
      await api.deletePosition(id);
      setPositions(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  const grouped = {};
  for (const p of positions) {
    const key = p.company_name || 'Unknown';
    if (filter && !key.toLowerCase().includes(filter.toLowerCase()) && !(p.job_title || '').toLowerCase().includes(filter.toLowerCase())) {
      continue;
    }
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(p);
  }

  const companies = Object.keys(grouped).sort();

  if (loading) return <LoadingSpinner text="Loading positions..." />;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Positions</h1>
          <p>Manage your job applications and tailored resumes.</p>
        </div>
        <div className="inline-row gap-1">
          <button className="btn btn-secondary btn-sm" onClick={() => { setShowUrlForm(!showUrlForm); setShowForm(false); }}>
            {showUrlForm ? 'Cancel' : 'Add from URL'}
          </button>
          <button className="btn btn-primary" onClick={() => { setShowForm(!showForm); setShowUrlForm(false); }}>
            {showForm ? 'Cancel' : 'Add Position'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {showUrlForm && (
        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Import Job from URL</h3>
          <p className="text-sm text-secondary mb-2">
            Paste a link to a job listing. The AI will scrape the page and extract the job description.
          </p>
          <form onSubmit={handleUrlIngest}>
            <div className="form-group">
              <label htmlFor="url-input">Job Listing URL *</label>
              <input id="url-input" name="url" value={urlForm.url} onChange={e => setUrlForm({ url: e.target.value })} required placeholder="https://..." />
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Importing...' : 'Import from URL'}
            </button>
          </form>
        </div>
      )}

      {showForm && (
        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>New Position</h3>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label htmlFor="company_name">Company Name *</label>
              <input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} required placeholder="e.g. Acme Corp" />
            </div>
            <div className="form-group">
              <label htmlFor="job_title">Job Title *</label>
              <input id="job_title" name="job_title" value={form.job_title} onChange={handleChange} required placeholder="e.g. Senior Developer" />
            </div>
            <div className="form-group">
              <label htmlFor="job_source_url">Source URL (optional)</label>
              <input id="job_source_url" name="job_source_url" value={form.job_source_url} onChange={handleChange} placeholder="https://..." />
            </div>
            <div className="form-group">
              <label htmlFor="job_description_md">Job Description (Markdown) *</label>
              <textarea id="job_description_md" name="job_description_md" value={form.job_description_md} onChange={handleChange} required placeholder="Paste the job description here..." rows={8} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Creating...' : 'Create Position'}
            </button>
          </form>
        </div>
      )}

      {positions.length > 0 && (
        <div className="inline-row mb-3" style={{ justifyContent: 'space-between' }}>
          <input
            type="text"
            placeholder="Filter by company or title..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{
              padding: '0.375rem 0.75rem',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              fontSize: '0.8125rem',
              width: '280px',
              outline: 'none',
            }}
            onFocus={e => e.target.style.borderColor = 'var(--color-primary)'}
            onBlur={e => e.target.style.borderColor = 'var(--color-border)'}
          />
        </div>
      )}

      {companies.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No positions yet</h3>
            <p>Add your first job position to get started.</p>
            {!showForm && (
              <button className="btn btn-primary" onClick={() => setShowForm(true)}>Add Position</button>
            )}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {companies.map(company => (
            <div key={company} className="card">
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>{company}</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                {grouped[company].map(p => (
                  <div key={p.id} className="flex-between" style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                    <Link
                      to={`/positions/${p.id}`}
                      style={{ fontWeight: 500, color: 'var(--color-text)', textDecoration: 'none' }}
                    >
                      {p.job_title || 'Untitled'}
                      {p.status === 'new' && <span className="badge badge-new" style={{ marginLeft: '0.5rem' }}>new</span>}
                      {p.status === 'tailored' && <span className="badge badge-tailored" style={{ marginLeft: '0.5rem' }}>tailored</span>}
                      {p.status === 'exported' && <span className="badge badge-exported" style={{ marginLeft: '0.5rem' }}>exported</span>}
                    </Link>
                    <div className="inline-row gap-1">
                      <span className="badge badge-new text-sm">{p.job_source_type}</span>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
