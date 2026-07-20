import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function HomePage() {
  const [cv, setCv] = useState(null);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getCv(),
      api.listPositions(),
    ]).then(([cvData, posData]) => {
      setCv(cvData.cv);
      setPositions(posData.positions || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return null;

  const hasCv = cv !== null;
  const personalInfo = cv?.personal_info || {};
  const fullName = [personalInfo.first_name, personalInfo.last_name].filter(Boolean).join(' ') || 'No name set';
  const skillCount = (cv?.skills || []).reduce((sum, s) => sum + (s.technologies || []).length, 0);
  const experienceCount = (cv?.career || []).length;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Dashboard</h1>
          <p>Welcome to Open Resume.</p>
        </div>
        {!hasCv && (
          <Link to="/cv" className="btn btn-primary">Create Base CV</Link>
        )}
      </div>

      <div className="grid-2 mb-3">
        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Base CV</h3>
          {hasCv ? (
            <div>
              <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{fullName}</p>
              <p className="text-sm text-secondary">{personalInfo.email || 'No email'}</p>
              <div className="inline-row mt-2 gap-1">
                <span className="badge badge-new text-sm">{skillCount} skills</span>
                <span className="badge badge-tailored text-sm">{experienceCount} positions</span>
              </div>
              <Link to="/cv" className="btn btn-secondary btn-sm mt-2" style={{ display: 'inline-block' }}>
                Edit CV
              </Link>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '1.5rem 0', textAlign: 'left' }}>
              <p>No base CV yet.</p>
              <Link to="/cv" className="btn btn-primary btn-sm">Create Base CV</Link>
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Positions</h3>
          {positions.length > 0 ? (
            <div>
              <p style={{ fontSize: '1.5rem', fontWeight: 700 }}>{positions.length}</p>
              <p className="text-sm text-secondary">Active positions</p>
              <div className="inline-row mt-1 gap-1">
                {[...new Set(positions.map(p => p.status))].map(s => (
                  <span key={s} className={`badge badge-${s === 'exported' ? 'exported' : s === 'tailored' ? 'tailored' : s === 'tailoring' ? 'tailoring' : 'new'}`}>
                    {positions.filter(p => p.status === s).length} {s}
                  </span>
                ))}
              </div>
              <Link to="/positions" className="btn btn-secondary btn-sm mt-2" style={{ display: 'inline-block' }}>
                View All
              </Link>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '1.5rem 0', textAlign: 'left' }}>
              <p>No positions yet.</p>
              <Link to="/positions" className="btn btn-primary btn-sm">Add Position</Link>
            </div>
          )}
        </div>
      </div>

      {positions.length > 0 && (
        <div>
          <div className="flex-between mb-2">
            <h3 style={{ fontSize: '1rem' }}>Recent Positions</h3>
            <Link to="/positions" className="btn btn-secondary btn-sm">View All</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {positions.slice(0, 5).map(p => (
              <Link
                key={p.id}
                to={`/positions/${p.id}`}
                className="card"
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', textDecoration: 'none', color: 'inherit' }}
              >
                <div>
                  <span style={{ fontWeight: 600 }}>{p.job_title || 'Untitled'}</span>
                  <span className="text-sm text-secondary" style={{ marginLeft: '0.5rem' }}>at {p.company_name || 'Unknown'}</span>
                </div>
                <span className={`badge badge-${p.status === 'exported' ? 'exported' : p.status === 'tailored' ? 'tailored' : p.status === 'tailoring' ? 'tailoring' : 'new'}`}>
                  {p.status || 'new'}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
