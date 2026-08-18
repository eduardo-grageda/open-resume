import { NavLink } from 'react-router-dom';

export default function Layout({ children }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Open Resume
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Dashboard
          </NavLink>
          <NavLink to="/cv" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Base CV
          </NavLink>
          <NavLink to="/onboard" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Onboarding
          </NavLink>
          <NavLink to="/star" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Interview Prep
          </NavLink>
          <NavLink to="/positions" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Positions
          </NavLink>
          <NavLink to="/search" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Search Jobs
          </NavLink>
          <div style={{ padding: '0.5rem 0.75rem 0.25rem', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', borderTop: '1px solid var(--color-border)', marginTop: '0.25rem' }}>
            Remy Agent
          </div>
          <NavLink to="/remy" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Remy Dashboard
          </NavLink>
          <NavLink to="/remy/queries" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Queries
          </NavLink>
          <NavLink to="/remy/tasks" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Tasks
          </NavLink>
          <NavLink to="/remy/listings" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Listings
          </NavLink>
          <NavLink to="/remy/reports" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Reports
          </NavLink>
          <NavLink to="/remy/memory" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Memory
          </NavLink>
        </nav>
        <div style={{ padding: '0 0.75rem' }}>
          <NavLink to="/settings" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Settings
          </NavLink>
        </div>
      </aside>
      <main className="main">
        {children}
      </main>
    </div>
  );
}
