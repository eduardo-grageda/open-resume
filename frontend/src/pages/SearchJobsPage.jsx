import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import JobSearchFilters from '../components/JobSearchFilters';

export default function SearchJobsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({
    query: '',
    location: '',
    remote: false,
    job_type: '',
    experience_level: '',
    date_posted: '',
  });
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch() {
    if (!filters.query.trim()) {
      setError('Please enter search keywords.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchJobs(filters);
      setResults(data.results || []);
      setHasSearched(true);
    } catch (err) {
      setError(err.message);
      setResults([]);
    }
    setLoading(false);
  }

  async function handleImport(result) {
    setImporting(result.url);
    setError(null);
    try {
      let jobDescriptionMd = '';
      const jdData = await api.extractJd(result.url);
      jobDescriptionMd = jdData.job_description_md || '';

      const position = {
        company_name: result.company || 'Unknown',
        job_title: result.title || 'Untitled',
        job_description_md: jobDescriptionMd,
        job_source_url: result.url || '',
        job_source_type: 'web_search',
      };

      const data = await api.createPosition(position);
      navigate(`/positions/${data.position.id}`);
    } catch (err) {
      setError(`Failed to import: ${err.message}`);
    }
    setImporting(null);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Search Jobs</h1>
        <p>Search open positions across the web using your configured search provider.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <JobSearchFilters
        filters={filters}
        onChange={setFilters}
        onSearch={handleSearch}
        loading={loading}
      />

      {loading && (
        <div className="card">
          <div className="empty-state">
            <h3>Searching...</h3>
            <p>Fetching results from {filters.query ? `"${filters.query}"` : 'search provider'}.</p>
          </div>
        </div>
      )}

      {!loading && hasSearched && results.length === 0 && (
        <div className="card">
          <div className="empty-state">
            <h3>No results found</h3>
            <p>Try adjusting your search keywords or filters.</p>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div>
          <p className="text-sm text-secondary mb-2">
            {results.length} result{results.length !== 1 ? 's' : ''} found
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {results.map((result, idx) => (
              <div key={idx} className="card">
                <div className="flex-between" style={{ alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                      {result.url ? (
                        <a href={result.url} target="_blank" rel="noopener noreferrer">
                          {result.title || 'Untitled'}
                        </a>
                      ) : (
                        result.title || 'Untitled'
                      )}
                    </h3>
                    <div className="text-sm text-secondary mb-1">
                      {result.company && <span style={{ fontWeight: 500 }}>{result.company}</span>}
                      {result.company && result.location && ' — '}
                      {result.location && <span>{result.location}</span>}
                    </div>
                    {result.description_snippet && (
                      <p className="text-sm" style={{ lineHeight: 1.5, marginBottom: '0.5rem' }}>
                        {result.description_snippet.length > 300
                          ? result.description_snippet.substring(0, 300) + '...'
                          : result.description_snippet}
                      </p>
                    )}
                    <div className="inline-row gap-1" style={{ flexWrap: 'wrap' }}>
                      {result.source && (
                        <span className="badge badge-new">{result.source}</span>
                      )}
                      {result.posted_date && (
                        <span className="text-sm text-secondary">{result.posted_date}</span>
                      )}
                    </div>
                  </div>
                  <div style={{ marginLeft: '1rem', flexShrink: 0 }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleImport(result)}
                      disabled={importing === result.url || !result.url}
                      title={!result.url ? 'No URL available to import' : 'Import as position'}
                    >
                      {importing === result.url ? 'Importing...' : 'Import'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasSearched && !loading && (
        <div className="card">
          <div className="empty-state">
            <h3>Search for open positions</h3>
            <p>Enter keywords above and click Search to find jobs across the web.</p>
          </div>
        </div>
      )}
    </div>
  );
}