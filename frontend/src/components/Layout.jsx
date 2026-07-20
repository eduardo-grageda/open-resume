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
          <NavLink to="/positions" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            Positions
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
