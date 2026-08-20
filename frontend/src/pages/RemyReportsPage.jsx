import { useState, useEffect } from 'react';
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

export default function RemyReportsPage() {
  const [reports, setReports] = useState([]);
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [running, setRunning] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    Promise.all([api.listRemyReports({ limit: 100 }), api.listRemyQueries()])
      .then(([d1, d2]) => {
        setReports(d1.reports || []);
        setQueries(d2.queries || []);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  async function openReport(r) {
    setSelected(r);
    setSelectedDetail(null);
    try {
      const data = await api.getRemyReport(r.id);
      setSelectedDetail(data.report);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAnalyze() {
    const queryId = window.prompt('Analyze which search profile? Enter its name or leave blank to pick:');
    const query = queries.find((q) => (queryId ? (q.name || '').toLowerCase() === queryId.toLowerCase() || q.id === queryId : true));
    if (!query && queryId) {
      setActionMsg(`Profile "${queryId}" not found.`);
      return;
    }
    if (!query) {
      setActionMsg('No search profiles yet. Create one first.');
      return;
    }
    setRunning('analyze');
    setActionMsg(null);
    try {
      const data = await api.analyzeRemy(query.id);
      setActionMsg(`Analysis ${data.run.status}. Report saved.`);
      const d = await api.listRemyReports({ limit: 100 });
      setReports(d.reports || []);
    } catch (err) {
      setActionMsg(`Analysis failed: ${err.message}`);
    }
    setRunning(null);
  }

  async function handleRecommend() {
    const query = queries[0];
    if (!query) {
      setActionMsg('No search profiles yet. Create one first.');
      return;
    }
    setRunning('recommend');
    setActionMsg(null);
    try {
      const data = await api.recommendRemy(query.id);
      setActionMsg(`Recommendations ${data.run.status}. Report saved.`);
      const d = await api.listRemyReports({ limit: 100 });
      setReports(d.reports || []);
    } catch (err) {
      setActionMsg(`Recommendation failed: ${err.message}`);
    }
    setRunning(null);
  }

  const detail = selectedDetail || selected;

  if (loading) return <LoadingSpinner text="Loading reports..." />;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Remy — Reports</h1>
          <p>Market analyses and top-match recommendations.</p>
        </div>
        <div className="inline-row gap-1">
          <button className="btn btn-secondary" onClick={handleRecommend} disabled={running !== null}>
            {running === 'recommend' ? 'Running...' : 'Run Recommendations'}
          </button>
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={running !== null}>
            {running === 'analyze' ? 'Running...' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-info">{actionMsg}</div>}

      {reports.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No reports yet</h3>
            <p>Run a market analysis or recommendations from a search profile, or schedule them as tasks.</p>
            <button className="btn btn-primary" onClick={handleAnalyze}>Run Analysis</button>
          </div>
        </div>
      ) : (
        <div className="grid-2" style={{ alignItems: 'start' }}>
          <div className="card" style={{ padding: '0.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
            {reports.map((r) => (
              <div
                key={r.id}
                onClick={() => openReport(r)}
                style={{
                  padding: '0.625rem 0.75rem',
                  borderRadius: 'var(--radius)',
                  cursor: 'pointer',
                  background: selected && selected.id === r.id ? 'var(--color-bg)' : 'transparent',
                }}
              >
                <div className="inline-row gap-1">
                  <strong className="text-sm" style={{ textTransform: 'capitalize' }}>{r.type}</strong>
                  {r.top_matches && r.top_matches.length > 0 && (
                    <span className="badge badge-new text-sm">{r.top_matches.length} matches</span>
                  )}
                </div>
                <p className="text-sm text-secondary">{formatDate(r.created_at)}</p>
              </div>
            ))}
          </div>

          <div className="card">
            {!detail ? (
              <div className="empty-state" style={{ padding: '2rem 1rem' }}>
                <p>Select a report to view.</p>
              </div>
            ) : (
              <div>
                <div className="flex-between mb-2">
                  <h3 style={{ fontSize: '1.05rem', textTransform: 'capitalize' }}>{detail.type} report</h3>
                  <span className="text-sm text-secondary">{formatDate(detail.created_at)}</span>
                </div>
                {detail.top_matches && detail.top_matches.length > 0 && (
                  <div className="card mb-2" style={{ padding: '1rem', background: 'var(--color-bg)' }}>
                    <h4 style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Top Matches</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {detail.top_matches.map((m) => (
                        <div key={m.listing_id} className="flex-between" style={{ gap: '1rem' }}>
                          <div className="text-sm">
                            <strong>{m.score}/100</strong>
                            {m.listing_title ? ` — ${m.listing_title}` : ''}
                            {m.listing_company ? ` at ${m.listing_company}` : ''}
                            <br />
                            <span className="text-secondary">{m.reason}</span>
                          </div>
                          <Link to={`/remy/listings/${m.listing_id}`} className="btn btn-secondary btn-sm" style={{ flexShrink: 0 }}>View Listing</Link>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="adapted-preview" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                  <ReactMarkdown>{detail.content_md || '*No content.*'}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
