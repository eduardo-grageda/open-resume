import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function RemyListingsPage() {
  const [listings, setListings] = useState([]);
  const [sources, setSources] = useState([]);
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({ search: '', source: '', query_id: '', active: '', new: false });
  const [selected, setSelected] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [importingId, setImportingId] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    Promise.all([api.getRemySources(), api.listRemyQueries()])
      .then(([d1, d2]) => {
        setSources(d1.sources || []);
        setQueries(d2.queries || []);
      })
      .catch(() => {});
    loadListings({});
  }, []);

  async function loadListings(overrides) {
    setLoading(true);
    setError(null);
    const params = { ...filter, ...overrides };
    const qs = {};
    if (params.search) qs.search = params.search;
    if (params.source) qs.source = params.source;
    if (params.query_id) qs.query_id = params.query_id;
    if (params.active !== '' && params.active !== null && params.active !== undefined) qs.active = params.active;
    if (params.new) qs.new = 'true';
    qs.limit = 200;
    try {
      const data = await api.listRemyListings(qs);
      setListings(data.listings || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  async function openListing(l) {
    setSelected(l);
    setSelectedDetail(null);
    try {
      const data = await api.getRemyListing(l.id);
      setSelectedDetail(data.listing);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRefresh() {
    if (!selected) return;
    setSelectedDetail(null);
    try {
      const data = await api.getRemyListing(selected.id, true);
      setSelectedDetail(data.listing);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleImport(l) {
    setImportingId(l.id);
    setActionMsg(null);
    try {
      const data = await api.importRemyListing(l.id);
      setListings((prev) => prev.map((x) => (x.id === l.id ? { ...x, imported_position_id: data.position.id } : x)));
      setActionMsg(`Imported as position "${data.position.job_title || 'untitled'}"`);
    } catch (err) {
      setActionMsg(`Import failed: ${err.message}`);
    }
    setImportingId(null);
  }

  const detail = selectedDetail || selected;

  return (
    <div>
      <div className="page-header">
        <h1>Remy — Listings Database</h1>
        <p>Everything Remy has scraped, searchable and importable.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-info">{actionMsg}</div>}

      <div className="card mb-3" style={{ padding: '1rem' }}>
        <div className="inline-row" style={{ flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search title, company, description..."
            value={filter.search}
            onChange={(e) => setFilter({ ...filter, search: e.target.value })}
            onKeyDown={(e) => { if (e.key === 'Enter') loadListings({}); }}
            style={{
              padding: '0.375rem 0.75rem',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              fontSize: '0.8125rem',
              width: '260px',
              outline: 'none',
            }}
          />
          <select
            value={filter.source}
            onChange={(e) => { setFilter({ ...filter, source: e.target.value }); loadListings({ source: e.target.value }); }}
            style={{ padding: '0.375rem 0.75rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', fontSize: '0.8125rem' }}
          >
            <option value="">All sources</option>
            {sources.filter((s) => s.implemented).map((s) => (
              <option key={s.name} value={s.name}>{s.display_name || s.name}</option>
            ))}
          </select>
          <select
            value={filter.query_id}
            onChange={(e) => { setFilter({ ...filter, query_id: e.target.value }); loadListings({ query_id: e.target.value }); }}
            style={{ padding: '0.375rem 0.75rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', fontSize: '0.8125rem' }}
          >
            <option value="">All profiles</option>
            {queries.map((q) => (
              <option key={q.id} value={q.id}>{q.name || 'unnamed'}</option>
            ))}
          </select>
          <select
            value={filter.active}
            onChange={(e) => { setFilter({ ...filter, active: e.target.value }); loadListings({ active: e.target.value }); }}
            style={{ padding: '0.375rem 0.75rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', fontSize: '0.8125rem' }}
          >
            <option value="">Any status</option>
            <option value="true">Active</option>
            <option value="false">Expired</option>
          </select>
          <label className="inline-row gap-1 text-sm" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={filter.new}
              onChange={(e) => { setFilter({ ...filter, new: e.target.checked }); loadListings({ new: e.target.checked }); }}
              style={{ width: 'auto' }}
            />
            Unseen only
          </label>
          <button className="btn btn-secondary btn-sm" onClick={() => { setFilter({ search: '', source: '', query_id: '', active: '', new: false }); loadListings({ search: '', source: '', query_id: '', active: '', new: false }); }}>
            Reset
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner text="Loading listings..." />
      ) : listings.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No listings yet</h3>
            <p>Create a search profile and schedule a scrape, or scrape now from the Queries page.</p>
          </div>
        </div>
      ) : (
        <div className="grid-2" style={{ alignItems: 'start' }}>
          <div className="card" style={{ padding: '0.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
            {listings.map((l) => (
              <div
                key={l.id}
                onClick={() => openListing(l)}
                style={{
                  padding: '0.625rem 0.75rem',
                  borderRadius: 'var(--radius)',
                  cursor: 'pointer',
                  background: selected && selected.id === l.id ? 'var(--color-bg)' : 'transparent',
                }}
              >
                <div className="inline-row gap-1" style={{ flexWrap: 'wrap' }}>
                  <strong className="text-sm">{l.title}</strong>
                  {l.imported_position_id && <span className="badge badge-exported text-sm">imported</span>}
                  {l.is_active === false && <span className="badge badge-new text-sm" style={{ background: '#fee2e2', color: '#991b1b' }}>expired</span>}
                </div>
                <p className="text-sm text-secondary">
                  {l.company}{l.location ? ` — ${l.location}` : ''} · {l.source}
                </p>
              </div>
            ))}
          </div>

          <div className="card">
            {!detail ? (
              <div className="empty-state" style={{ padding: '2rem 1rem' }}>
                <p>Select a listing to view details.</p>
              </div>
            ) : (
              <div>
                <div className="flex-between mb-2">
                  <h3 style={{ fontSize: '1.05rem' }}>{detail.title}</h3>
                  <div className="inline-row gap-1">
                    {detail.imported_position_id ? (
                      <Link to={`/positions/${detail.imported_position_id}`} className="btn btn-primary btn-sm">
                        Open Position
                      </Link>
                    ) : (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleImport(detail)}
                        disabled={importingId === detail.id}
                      >
                        {importingId === detail.id ? 'Importing...' : 'Import to Position'}
                      </button>
                    )}
                    <button className="btn btn-secondary btn-sm" onClick={handleRefresh}>Refresh</button>
                  </div>
                </div>
                <p className="text-sm text-secondary mb-2">
                  {detail.company} — {detail.location || 'n/a'}{detail.salary ? ` · ${detail.salary}` : ''}
                  {' · '}{detail.source}
                </p>
                {detail.url && (
                  <p className="mb-2">
                    <a href={detail.url} target="_blank" rel="noreferrer" className="text-sm">View original listing</a>
                  </p>
                )}
                <div className="adapted-preview" style={{ maxHeight: '50vh', overflowY: 'auto' }}>
                  <ReactMarkdown>{detail.description_md || '*No description fetched yet. Use Refresh to fetch the full listing.*'}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
