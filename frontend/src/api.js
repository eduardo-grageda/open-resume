const BASE = '/api';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(`${BASE}${path}`, opts);
  const data = await res.json();

  if (!res.ok) {
    const detail = data.detail || data.message || `${res.status} ${res.statusText}`;
    throw new Error(detail);
  }

  return data;
}

export const api = {
  // Health
  health: () => request('GET', '/health'),

  // Settings
  getSettings: () => request('GET', '/settings'),
  updateSettings: (body) => request('PUT', '/settings', body),
  testLlm: () => request('POST', '/settings/test-llm'),

  // CV
  getCv: () => request('GET', '/cv'),
  updateCv: (cv) => request('PUT', '/cv', cv),
  ingestPdf: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE}/cv/ingest-pdf`, { method: 'POST', body: form }).then(r => r.json());
  },

  // Onboarding
  onboardStart: (body) => request('POST', '/cv/onboard/start', body),
  onboardAnswer: (body) => request('POST', '/cv/onboard/answer', body),
  onboardConfirm: (body) => request('POST', '/cv/onboard/confirm', body),
  onboardProgress: (sessionId) => request('GET', `/cv/onboard/progress/${sessionId}`),

  // Positions
  listPositions: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request('GET', `/positions${qs ? `?${qs}` : ''}`);
  },
  getPosition: (id) => request('GET', `/positions/${id}`),
  createPosition: (body) => request('POST', '/positions', body),
  updatePosition: (id, body) => request('PUT', `/positions/${id}`, body),
  deletePosition: (id) => request('DELETE', `/positions/${id}`),
  adaptPosition: (id) => request('POST', `/positions/${id}/adapt`),
  exportMarkdownUrl: (id) => `${BASE}/positions/${id}/export/md`,
  exportPdfUrl: (id) => `${BASE}/positions/${id}/export/pdf`,
};

export default api;
