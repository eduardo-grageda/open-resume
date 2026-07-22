export default function LoadingSpinner({ text = 'Loading...' }) {
  return (
    <div className="empty-state" style={{ padding: '3rem 1rem' }}>
      <div className="spinner" />
      <p style={{ marginTop: '0.75rem', color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
        {text}
      </p>
    </div>
  );
}