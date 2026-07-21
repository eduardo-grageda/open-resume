import { Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import SettingsPage from './pages/SettingsPage';
import CvEditorPage from './pages/CvEditorPage';
import OnboardingPage from './pages/OnboardingPage';
import PositionsPage from './pages/PositionsPage';
import PositionPage from './pages/PositionPage';
import SearchJobsPage from './pages/SearchJobsPage';
import api from './api';

export default function App() {
  const [hasConfig, setHasConfig] = useState(null);

  useEffect(() => {
    api.getSettings()
      .then(d => setHasConfig(d.has_config))
      .catch(() => setHasConfig(false));
  }, []);

  if (hasConfig === null) {
    return (
      <div className="layout">
        <main className="main" style={{ marginLeft: 0 }}>
          <div className="empty-state">
            <h3>Loading...</h3>
          </div>
        </main>
      </div>
    );
  }

  if (!hasConfig) {
    return (
      <div className="layout">
        <main className="main" style={{ marginLeft: 0 }}>
          <Routes>
            <Route path="/settings" element={<SettingsPage onConfigSaved={() => setHasConfig(true)} />} />
            <Route path="*" element={<Navigate to="/settings" replace />} />
          </Routes>
        </main>
      </div>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/cv" element={<CvEditorPage />} />
        <Route path="/onboard" element={<OnboardingPage />} />
        <Route path="/positions" element={<PositionsPage />} />
        <Route path="/positions/:id" element={<PositionPage />} />
        <Route path="/search" element={<SearchJobsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
