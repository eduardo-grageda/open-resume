import { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const EMPTY_QUERY = {
  name: '',
  keywords: '',
  sources: '',
  remote_only: false,
  experience_level: 'any',
  exclude_keywords: '',
  cities: [{ name: '', country: 'MX', lat: 0, lng: 0, radius_km: 25 }],
};

function toForm(query) {
  return {
    ...EMPTY_QUERY,
    ...query,
    keywords: (query.keywords || []).join(', '),
    exclude_keywords: (query.exclude_keywords || []).join(', '),
    sources: (query.sources || []).join(', '),
    cities: (query.cities && query.cities.length ? query.cities : [{ ...EMPTY_QUERY.cities[0] }]).map((c) => ({
      name: c.name, country: c.country || 'MX', lat: c.lat, lng: c.lng, radius_km: c.radius_km,
    })),
  };
}

function fromForm(form) {
  return {
    name: form.name.trim(),
    keywords: form.keywords.split(',').map((s) => s.trim()).filter(Boolean),
    exclude_keywords: form.exclude_keywords.split(',').map((s) => s.trim()).filter(Boolean),
    sources: form.sources.split(',').map((s) => s.trim()).filter(Boolean),
    remote_only: form.remote_only,
    experience_level: form.experience_level,
    cities: form.cities.filter((c) => c.name.trim()),
  };
}

function CityForm({ city, index, onChange, onRemove, canRemove }) {
  const set = (field, value) => onChange(index, { ...city, [field]: value });

  return (
    <div className="card mb-2" style={{ padding: '1rem' }}>
      <div className="flex-between mb-2">
        <h4 style={{ fontSize: '0.875rem' }}>City {index + 1}</h4>
        {canRemove && (
          <button className="btn btn-danger btn-sm" onClick={onRemove}>Remove</button>
        )}
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>City name *</label>
          <input
            value={city.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="e.g. Guadalajara"
          />
        </div>
        <div className="form-group">
          <label>Country</label>
          <input
            value={city.country}
            onChange={(e) => set('country', e.target.value.toUpperCase())}
            placeholder="MX"
            maxLength={2}
          />
        </div>
        <div className="form-group">
          <label>Latitude</label>
          <input
            type="number"
            step="0.0001"
            value={city.lat}
            onChange={(e) => set('lat', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div className="form-group">
          <label>Longitude</label>
          <input
            type="number"
            step="0.0001"
            value={city.lng}
            onChange={(e) => set('lng', parseFloat(e.target.value) || 0)}
          />
        </div>
      </div>
      <div className="form-group no-margin">
        <label>Search radius: {city.radius_km} km</label>
        <input
          type="range"
          min="1"
          max="200"
          step="1"
          value={city.radius_km}
          onChange={(e) => set('radius_km', parseInt(e.target.value, 10))}
          style={{ width: '100%' }}
        />
        <div className="inline-row" style={{ justifyContent: 'space-between' }}>
          <span className="form-help">1 km</span>
          <span className="form-help">200 km</span>
        </div>
      </div>
    </div>
  );
}

export default function RemyQueriesPage() {
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(toForm({}));
  const [saving, setSaving] = useState(false);
  const [scraping, setScraping] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    loadQueries();
  }, []);

  async function loadQueries() {
    try {
      const data = await api.listRemyQueries();
      setQueries(data.queries || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  function startCreate() {
    setEditingId(null);
    setForm(toForm({}));
    setShowForm(true);
    setError(null);
  }

  function startEdit(q) {
    setEditingId(q.id);
    setForm(toForm(q));
    setShowForm(true);
    setError(null);
  }

  function setCity(index, updated) {
    setForm((prev) => ({ ...prev, cities: prev.cities.map((c, i) => (i === index ? updated : c)) }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const body = fromForm(form);
    if (!body.cities.length) {
      setError('Add at least one city.');
      setSaving(false);
      return;
    }
    try {
      let data;
      if (editingId) {
        data = await api.updateRemyQuery(editingId, body);
        setQueries((prev) => prev.map((q) => (q.id === editingId ? data.query : q)));
      } else {
        data = await api.createRemyQuery(body);
        setQueries((prev) => [...prev, data.query]);
      }
      setShowForm(false);
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  async function handleDelete(q) {
    if (!confirm(`Delete search profile "${q.name || 'unnamed'}"?`)) return;
    try {
      await api.deleteRemyQuery(q.id);
      setQueries((prev) => prev.filter((x) => x.id !== q.id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleScrape(q) {
    setScraping(q.id);
    setActionMsg(null);
    try {
      const data = await api.scrapeRemyQuery(q.id);
      const counts = (data.stats || []).map((s) => `${s.source}: +${s.new}`).join(', ');
      setActionMsg(`Scrape finished (${data.run.status}). ${counts}`);
    } catch (err) {
      setActionMsg(`Scrape failed: ${err.message}`);
    }
    setScraping(null);
  }

  if (loading) return <LoadingSpinner text="Loading search profiles..." />;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Remy — Search Profiles</h1>
          <p>Define what Remy watches: keywords, cities, and sources.</p>
        </div>
        <button className="btn btn-primary" onClick={() => (showForm ? setShowForm(false) : startCreate())}>
          {showForm ? 'Cancel' : 'New Profile'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-info">{actionMsg}</div>}

      {showForm && (
        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>{editingId ? 'Edit Profile' : 'New Search Profile'}</h3>
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label>Profile name *</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Backend engineer — Mexico" />
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Keywords (comma separated)</label>
                <input value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} placeholder="python, fastapi, backend" />
              </div>
              <div className="form-group">
                <label>Exclude keywords (comma separated)</label>
                <input value={form.exclude_keywords} onChange={(e) => setForm({ ...form, exclude_keywords: e.target.value })} placeholder="senior, lead" />
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Sources (comma separated, leave empty for all enabled)</label>
                <input value={form.sources} onChange={(e) => setForm({ ...form, sources: e.target.value })} placeholder="occ, linkedin, aggregator" />
              </div>
              <div className="form-group">
                <label>Experience level</label>
                <select value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })}>
                  <option value="any">Any</option>
                  <option value="entry">Entry</option>
                  <option value="mid">Mid</option>
                  <option value="senior">Senior</option>
                </select>
              </div>
            </div>
            <div className="form-group inline-row gap-1">
              <input
                type="checkbox"
                id="remote-only"
                checked={form.remote_only}
                onChange={(e) => setForm({ ...form, remote_only: e.target.checked })}
                style={{ width: 'auto' }}
              />
              <label htmlFor="remote-only" style={{ marginBottom: 0, cursor: 'pointer' }}>Remote only</label>
            </div>

            <h4 style={{ fontSize: '0.875rem', marginBottom: '0.75rem' }}>Cities</h4>
            {form.cities.map((city, i) => (
              <CityForm
                key={i}
                city={city}
                index={i}
                onChange={setCity}
                onRemove={() => setForm((prev) => ({ ...prev, cities: prev.cities.filter((_, j) => j !== i) }))}
                canRemove={form.cities.length > 1}
              />
            ))}
            <button
              type="button"
              className="btn btn-secondary btn-sm mb-3"
              onClick={() => setForm((prev) => ({ ...prev, cities: [...prev.cities, { name: '', country: 'MX', lat: 0, lng: 0, radius_km: 25 }] }))}
            >
              + Add City
            </button>

            <div>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : editingId ? 'Save Changes' : 'Create Profile'}
              </button>
            </div>
          </form>
        </div>
      )}

      {queries.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No search profiles yet</h3>
            <p>Create one to start collecting job listings automatically.</p>
            {!showForm && <button className="btn btn-primary" onClick={startCreate}>New Profile</button>}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {queries.map((q) => (
            <div key={q.id} className="card">
              <div className="flex-between mb-2">
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
                    {q.name || 'Unnamed profile'}
                    {q.enabled === false && <span className="badge badge-new" style={{ marginLeft: '0.5rem' }}>disabled</span>}
                  </h3>
                  <p className="text-sm text-secondary">
                    {q.keywords.join(', ') || 'no keywords'} — {q.cities.map((c) => `${c.name} (${c.radius_km} km)`).join(', ')}
                  </p>
                </div>
                <div className="inline-row gap-1">
                  <button className="btn btn-secondary btn-sm" onClick={() => handleScrape(q)} disabled={scraping === q.id}>
                    {scraping === q.id ? 'Scraping...' : 'Scrape now'}
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => startEdit(q)}>Edit</button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(q)}>Delete</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
