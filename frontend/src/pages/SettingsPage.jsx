import { useState, useEffect } from 'react';
import api from '../api';

export default function SettingsPage({ onConfigSaved }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [message, setMessage] = useState(null);

  const [form, setForm] = useState({
    openrouter_api_key: '',
    openrouter_base_url: 'https://openrouter.ai/api/v1',
    openrouter_model: 'openai/gpt-4o',
    storage_backend: 'json',
    mongo_uri: 'mongodb://localhost:27017',
    search_provider: 'serpapi',
    search_api_key: '',
  });

  useEffect(() => {
    api.getSettings()
      .then(d => {
        if (d.config) {
          setForm(prev => ({ ...prev, ...d.config }));
        }
        setLoading(false);
      })
      .catch(err => {
        setMessage({ type: 'error', text: err.message });
        setLoading(false);
      });
  }, []);

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.updateSettings(form);
      setMessage({ type: 'success', text: 'Settings saved.' });
      if (onConfigSaved) onConfigSaved();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
    setSaving(false);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.testLlm();
      setTestResult({ ok: r.ok, model: r.model });
    } catch (err) {
      setTestResult({ ok: false, model: err.message });
    }
    setTesting(false);
  }

  if (loading) return null;

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Configure your AI provider and storage backend.</p>
      </div>

      {message && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}

      <form onSubmit={handleSave}>
        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>AI Provider</h3>
          <div className="form-group">
            <label htmlFor="openrouter_base_url">Base URL</label>
            <input
              id="openrouter_base_url"
              name="openrouter_base_url"
              value={form.openrouter_base_url}
              onChange={handleChange}
              placeholder="https://openrouter.ai/api/v1"
            />
            <p className="form-help">OpenRouter, OpenAI, or any OpenAI-compatible endpoint.</p>
          </div>
          <div className="form-group">
            <label htmlFor="openrouter_api_key">API Key</label>
            <input
              id="openrouter_api_key"
              name="openrouter_api_key"
              type="password"
              value={form.openrouter_api_key}
              onChange={handleChange}
              placeholder="sk-..."
            />
          </div>
          <div className="form-group">
            <label htmlFor="openrouter_model">Model</label>
            <input
              id="openrouter_model"
              name="openrouter_model"
              value={form.openrouter_model}
              onChange={handleChange}
              placeholder="openai/gpt-4o"
            />
          </div>
          <div className="inline-row">
            <button type="button" className="btn btn-secondary" onClick={handleTest} disabled={testing || !form.openrouter_api_key}>
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            {testResult && (
              <span className={`text-sm ${testResult.ok ? 'badge badge-tailored' : 'badge badge-tailoring'}`}>
                {testResult.ok ? `Connected (${testResult.model})` : `Failed: ${testResult.model}`}
              </span>
            )}
          </div>
        </div>

        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Storage</h3>
          <div className="form-group">
            <label htmlFor="storage_backend">Storage Backend</label>
            <select
              id="storage_backend"
              name="storage_backend"
              value={form.storage_backend}
              onChange={handleChange}
            >
              <option value="json">JSON (files)</option>
              <option value="mongodb">MongoDB</option>
            </select>
          </div>
          {form.storage_backend === 'mongodb' && (
            <div className="form-group">
              <label htmlFor="mongo_uri">MongoDB URI</label>
              <input
                id="mongo_uri"
                name="mongo_uri"
                value={form.mongo_uri}
                onChange={handleChange}
                placeholder="mongodb://localhost:27017"
              />
            </div>
          )}
        </div>

        <div className="card mb-3">
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Search</h3>
          <div className="form-group">
            <label htmlFor="search_provider">Search Provider</label>
            <select
              id="search_provider"
              name="search_provider"
              value={form.search_provider}
              onChange={handleChange}
            >
              <option value="serpapi">SerpAPI</option>
              <option value="brave">Brave Search</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="search_api_key">Search API Key</label>
            <input
              id="search_api_key"
              name="search_api_key"
              type="password"
              value={form.search_api_key}
              onChange={handleChange}
              placeholder="API key..."
            />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}
