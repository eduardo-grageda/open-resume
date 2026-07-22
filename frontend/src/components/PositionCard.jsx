import { Link } from 'react-router-dom';

export default function PositionCard({ position }) {
  const statusClass = `badge badge-${
    position.status === 'exported' ? 'exported'
    : position.status === 'tailored' ? 'tailored'
    : position.status === 'tailoring' ? 'tailoring'
    : 'new'
  }`;

  return (
    <Link
      to={`/positions/${position.id}`}
      className="card"
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1rem',
        textDecoration: 'none',
        color: 'inherit',
      }}
    >
      <div>
        <span style={{ fontWeight: 600 }}>
          {position.job_title || 'Untitled'}
        </span>
        <span className="text-sm text-secondary" style={{ marginLeft: '0.5rem' }}>
          at {position.company_name || 'Unknown'}
        </span>
      </div>
      <span className={statusClass}>{position.status || 'new'}</span>
    </Link>
  );
}