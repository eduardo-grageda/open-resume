import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '../api';
import MdEditor from '../components/MdEditor';
import AdaptedPreview from '../components/AdaptedPreview';
import LoadingSpinner from '../components/LoadingSpinner';

const TABS = ['description', 'tailored', 'export'];

export default function PositionPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [position, setPosition] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('description');
  const [saving, setSaving] = useState(false);
  const [adapting, setAdapting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editField, setEditField] = useState('');

  useEffect(() => {
    loadPosition();
  }, [id]);

  async function loadPosition() {
    try {
      const data = await api.getPosition(id);
      setPosition(data.position);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const data = await api.updatePosition(id, position);
      setPosition(data.position);
      setEditMode(false);
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  async function handleAdapt() {
    setAdapting(true);
    setError(null);
    try {
      const data = await api.adaptPosition(id);
      setPosition(data.position);
    } catch (err) {
      setError(err.message);
    }
    setAdapting(false);
  }

  async function handleDelete() {
    if (!confirm('Delete this position permanently?')) return;
    try {
      await api.deletePosition(id);
      navigate('/positions');
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <LoadingSpinner text="Loading position..." />;
  if (error && !position && error !== 'Position not found') {
    return (
      <div>
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }
  if (!position) {
    return (
      <div>
        <div className="alert alert-error">Position not found.</div>
        <button className="btn btn-secondary" onClick={() => navigate('/positions')}>Back to Positions</button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>{position.job_title || 'Untitled Position'}</h1>
          <p>{position.company_name} &middot; <span className={`badge badge-${position.status === 'exported' ? 'exported' : position.status === 'tailored' ? 'tailored' : 'new'}`}>{position.status}</span></p>
        </div>
        <div className="inline-row gap-1">
          {editMode ? (
            <>
              <button className="btn btn-secondary btn-sm" onClick={() => { setEditMode(false); loadPosition(); }}>Cancel</button>
              <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/positions')}>Back</button>
              <button className="btn btn-danger btn-sm" onClick={handleDelete}>Delete</button>
            </>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="tabs">
        <button className={`tab ${activeTab === 'description' ? 'active' : ''}`} onClick={() => setActiveTab('description')}>
          Job Description
        </button>
        <button className={`tab ${activeTab === 'tailored' ? 'active' : ''}`} onClick={() => setActiveTab('tailored')}>
          Tailored CV
        </button>
        <button className={`tab ${activeTab === 'export' ? 'active' : ''}`} onClick={() => setActiveTab('export')}>
          Export
        </button>
      </div>

      {activeTab === 'description' && (
        <div className="card">
          {position.job_source_url && (
            <p className="text-sm text-secondary mb-2">
              Source: <a href={position.job_source_url} target="_blank" rel="noopener noreferrer">{position.job_source_url}</a>
            </p>
          )}
          {editMode ? (
            <div>
              <div className="form-group">
                <label>Job Title</label>
                <input
                  value={position.job_title}
                  onChange={e => setPosition(prev => ({ ...prev, job_title: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Company Name</label>
                <input
                  value={position.company_name}
                  onChange={e => setPosition(prev => ({ ...prev, company_name: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Job Description (Markdown)</label>
                <textarea
                  value={position.job_description_md}
                  onChange={e => setPosition(prev => ({ ...prev, job_description_md: e.target.value }))}
                  rows={12}
                />
              </div>
            </div>
          ) : position.job_description_md ? (
            <div style={{ padding: '0.5rem 0' }}>
              <ReactMarkdown>{position.job_description_md}</ReactMarkdown>
              <button className="btn btn-secondary btn-sm mt-2" onClick={() => { setEditMode(true); setEditField('description'); }}>Edit</button>
            </div>
          ) : (
            <div className="empty-state">
              <p>No job description yet.</p>
              <button className="btn btn-primary btn-sm" onClick={() => { setEditMode(true); setEditField('description'); }}>Add Description</button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'tailored' && (
        <div className="card">
          {position.tailored_cv_md ? (
            <div>
              <MdEditor
                value={position.tailored_cv_md}
                onChange={val => setPosition(prev => ({ ...prev, tailored_cv_md: val }))}
              />
              {position.change_summary && (
                <div className="alert alert-info mt-2">
                  <strong>Change Summary:</strong>
                  <ReactMarkdown>{position.change_summary}</ReactMarkdown>
                </div>
              )}
              <div className="inline-row gap-1 mt-2">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleAdapt}
                  disabled={adapting}
                >
                  {adapting ? 'Regenerating...' : 'Regenerate'}
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <h3>No tailored CV yet</h3>
              <p>Generate a CV tailored to this job description using AI.</p>
              <button
                className="btn btn-primary"
                onClick={handleAdapt}
                disabled={adapting}
              >
                {adapting ? 'Generating...' : 'Generate Tailored CV'}
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'export' && (
        <div className="card">
          {position.tailored_cv_md ? (
            <div>
              <AdaptedPreview
                markdown={position.tailored_cv_md}
                jobTitle={position.job_title}
                companyName={position.company_name}
              />
              <div className="inline-row gap-1 mt-2">
                <a
                  className="btn btn-primary btn-sm"
                  href={api.exportMarkdownUrl(id)}
                  download
                >
                  Download Markdown
                </a>
                <a
                  className="btn btn-secondary btn-sm"
                  href={api.exportPdfUrl(id)}
                  download
                  onClick={() => setExporting(true)}
                >
                  {exporting ? 'Exporting...' : 'Download PDF'}
                </a>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <h3>Nothing to export</h3>
              <p>Generate a tailored CV first.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}