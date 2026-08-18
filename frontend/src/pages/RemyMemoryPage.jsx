import { useState, useEffect } from 'react';
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

export default function RemyMemoryPage() {
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    loadMemory();
  }, []);

  async function loadMemory() {
    try {
      const data = await api.getRemyMemory();
      setMemory(data);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  async function handleClear() {
    if (!confirm('Clear all Remy memory (profile, CV history, run index)? This cannot be undone.')) return;
    setClearing(true);
    try {
      await api.clearRemyMemory();
      setActionMsg('Memory cleared.');
      await loadMemory();
    } catch (err) {
      setActionMsg(`Failed: ${err.message}`);
    }
    setClearing(false);
  }

  if (loading) return <LoadingSpinner text="Loading memory..." />;

  const profile = memory?.profile || {};
  const cvHistory = memory?.cv_history || [];
  const recentRuns = memory?.recent_runs || [];
  const signals = profile.market_signals || {};

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Remy — Memory</h1>
          <p>What Remy remembers about you and your CV history.</p>
        </div>
        <button className="btn btn-danger" onClick={handleClear} disabled={clearing}>
          {clearing ? 'Clearing...' : 'Clear Memory'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-info">{actionMsg}</div>}

      <div className="grid-2 mb-3">
        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Profile</h3>
          {profile.role ? (
            <>
              <p style={{ fontWeight: 600 }}>{profile.role}</p>
              <p className="text-sm text-secondary">
                CV snapshots: {cvHistory.length} · tracked runs: {recentRuns.length}
              </p>
              {profile.preferences && Object.keys(profile.preferences).length > 0 && (
                <div className="mt-2">
                  <h4 className="text-sm text-secondary" style={{ textTransform: 'uppercase', fontSize: '0.6875rem' }}>Preferences</h4>
                  <ul className="text-sm" style={{ paddingLeft: '1.25rem' }}>
                    {Object.entries(profile.preferences).map(([k, v]) => (
                      <li key={k}><strong>{k}</strong>: {String(v)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-secondary">No profile yet — Remy learns about you as you save your CV.</p>
          )}
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Market Signals</h3>
          {signals.top_skills && signals.top_skills.length > 0 ? (
            <div className="inline-row" style={{ flexWrap: 'wrap' }}>
              {signals.top_skills.map((s) => (
                <span key={s} className="badge badge-tailored text-sm" style={{ textTransform: 'none' }}>{s}</span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-secondary">No market signals yet. Run analyses to teach Remy which skills the market wants.</p>
          )}
          {signals.updated_at && (
            <p className="text-sm text-secondary mt-2">Last updated: {formatDate(signals.updated_at)}</p>
          )}
        </div>
      </div>

      <div className="card mb-3">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>CV Change History</h3>
        {cvHistory.length === 0 ? (
          <p className="text-sm text-secondary">No CV snapshots yet. Every CV save is recorded here automatically.</p>
        ) : (
          <div className="cv-timeline">
            {cvHistory.map((entry, i) => {
              const sig = entry.signature || {};
              return (
                <div key={entry.timestamp + i} className="cv-timeline-item">
                  <div className="cv-timeline-dot" />
                  <div>
                    <p className="text-sm"><strong>{sig.name || 'CV'}</strong> saved</p>
                    <p className="text-sm text-secondary">
                      {formatDate(entry.timestamp)} · {sig.skills_count ?? 0} skills · {sig.career_count ?? 0} positions
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Recent Tracked Runs</h3>
        {recentRuns.length === 0 ? (
          <p className="text-sm text-secondary">No runs recorded yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {recentRuns.map((r) => (
              <div key={r.run_id} className="flex-between text-sm" style={{ padding: '0.375rem 0', borderBottom: '1px solid var(--color-border)' }}>
                <span style={{ textTransform: 'capitalize' }}>{r.report_type || 'run'}</span>
                <span className="text-secondary">{formatDate(r.recorded_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
