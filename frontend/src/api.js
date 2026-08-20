const BACKEND_URL = window.__BACKEND_URL__ ||
  (window.__BACKEND_PORT__ ? `http://127.0.0.1:${window.__BACKEND_PORT__}` : '');

const BASE = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

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
    return fetch(`${BASE}/cv/ingest-pdf`, { method: 'POST', body: form }).then(r => {
      if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Upload failed'); });
      return r.json();
    });
  },
  ingestPdfConfirm: (cv) => request('POST', '/cv/ingest-pdf/confirm', cv),

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

  // Search
  searchJobs: (body) => request('POST', '/search/jobs', body),
  getSearchSources: () => request('GET', '/search/sources'),
  extractJd: (body) => request('POST', '/search/extract-jd', body),
  ingestUrl: (body) => request('POST', '/positions/ingest-url', body),

  // STAR Interview Prep
  starStart: (body) => request('POST', '/star/start', body),
  starAnswer: (body) => request('POST', '/star/answer', body),
  starConfirm: (body) => request('POST', '/star/confirm', body),
  listStarStories: () => request('GET', '/star/stories'),
  getStarStory: (id) => request('GET', `/star/stories/${id}`),
  updateStarStory: (id, body) => request('PUT', `/star/stories/${id}`, body),
  deleteStarStory: (id) => request('DELETE', `/star/stories/${id}`),
  generateStarPitch: (id) => request('POST', `/star/generate-pitch/${id}`),

  // Remy — sources
  getRemySources: () => request('GET', '/remy/sources'),

  // Remy — queries
  listRemyQueries: () => request('GET', '/remy/queries'),
  createRemyQuery: (body) => request('POST', '/remy/queries', body),
  getRemyQuery: (id) => request('GET', `/remy/queries/${id}`),
  updateRemyQuery: (id, body) => request('PUT', `/remy/queries/${id}`, body),
  deleteRemyQuery: (id) => request('DELETE', `/remy/queries/${id}`),
  scrapeRemyQuery: (id) => request('POST', `/remy/queries/${id}/scrape`),

  // Remy — tasks
  listRemyTasks: () => request('GET', '/remy/tasks'),
  createRemyTask: (body) => request('POST', '/remy/tasks', body),
  getRemyTask: (id) => request('GET', `/remy/tasks/${id}`),
  updateRemyTask: (id, body) => request('PUT', `/remy/tasks/${id}`, body),
  deleteRemyTask: (id) => request('DELETE', `/remy/tasks/${id}`),
  runRemyTask: (id) => request('POST', `/remy/tasks/${id}/run`),

  // Remy — runs
  listRemyRuns: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request('GET', `/remy/runs${qs ? `?${qs}` : ''}`);
  },

  // Remy — listings
  listRemyListings: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request('GET', `/remy/listings${qs ? `?${qs}` : ''}`);
  },
  getRemyListing: (id, refresh = false) => request('GET', `/remy/listings/${id}${refresh ? '?refresh=true' : ''}`),
  importRemyListing: (id) => request('POST', `/remy/listings/${id}/import`),

  // Remy — analysis & recommendations
  analyzeRemy: (queryId) => request('POST', `/remy/analyze/${queryId}`),
  recommendRemy: (queryId) => request('POST', `/remy/recommend/${queryId}`),
  listRemyReports: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request('GET', `/remy/reports${qs ? `?${qs}` : ''}`);
  },
  getRemyReport: (id) => request('GET', `/remy/reports/${id}`),

  // Remy — memory
  getRemyMemory: () => request('GET', '/remy/memory'),
  clearRemyMemory: () => request('DELETE', '/remy/memory'),

  // Remy — chat
  listRemyThreads: () => request('GET', '/remy/chat/threads'),
  getRemyThread: (id) => request('GET', `/remy/chat/${id}`),
  deleteRemyThread: (id) => request('DELETE', `/remy/chat/${id}`),
  streamRemyChat: (message, threadId, onEvent) => {
    return new Promise((resolve, reject) => {
      const controller = new AbortController();
      const promise = fetch(`${BASE}/remy/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, thread_id: threadId || null }),
        signal: controller.signal,
      });

      let fullText = '';
      let thread = threadId;

      (async () => {
        try {
          const res = await promise;
          if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            reject(new Error(data.detail || `HTTP ${res.status}`));
            return;
          }
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop();
            for (const part of parts) {
              const line = part.trim();
              if (!line.startsWith('data: ')) continue;
              let event;
              try {
                event = JSON.parse(line.slice(6));
              } catch {
                continue;
              }
              if (event.type === 'meta') thread = event.thread_id;
              if (event.type === 'delta') {
                fullText += event.content;
                onEvent({ type: 'delta', content: event.content, thread_id: thread });
              } else if (event.type === 'done') {
                onEvent({ type: 'done', thread_id: thread });
              } else if (event.type === 'error') {
                onEvent({ type: 'error', detail: event.detail, thread_id: thread });
              }
            }
          }
          if (buffer.trim().startsWith('data: ')) {
            try {
              const event = JSON.parse(buffer.trim().slice(6));
              if (event.type === 'delta') fullText += event.content;
              onEvent(event);
            } catch { /* ignore trailing partial */ }
          }
          resolve({ thread_id: thread, text: fullText });
        } catch (err) {
          if (err.name === 'AbortError') reject(err);
          else reject(err);
        }
      })();

      promise.cancel = () => controller.abort();
    });
  },
};

export default api;
