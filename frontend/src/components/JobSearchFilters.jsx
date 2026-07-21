export default function JobSearchFilters({ filters, onChange, onSearch, loading }) {
  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    onChange({ ...filters, [name]: type === 'checkbox' ? checked : value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSearch();
  }

  return (
    <form onSubmit={handleSubmit} className="card mb-3">
      <div className="grid-2">
        <div className="form-group">
          <label htmlFor="query">Keywords</label>
          <input
            id="query"
            name="query"
            type="text"
            value={filters.query || ''}
            onChange={handleChange}
            placeholder="e.g. Senior Python Developer"
          />
        </div>
        <div className="form-group">
          <label htmlFor="location">Location</label>
          <input
            id="location"
            name="location"
            type="text"
            value={filters.location || ''}
            onChange={handleChange}
            placeholder="e.g. New York, Remote"
          />
        </div>
      </div>

      <div className="grid-2">
        <div className="form-group">
          <label htmlFor="experience_level">Experience Level</label>
          <select
            id="experience_level"
            name="experience_level"
            value={filters.experience_level || ''}
            onChange={handleChange}
          >
            <option value="">Any</option>
            <option value="entry">Entry Level</option>
            <option value="mid">Mid Level</option>
            <option value="senior">Senior</option>
            <option value="lead">Lead</option>
            <option value="executive">Executive</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="job_type">Job Type</label>
          <select
            id="job_type"
            name="job_type"
            value={filters.job_type || ''}
            onChange={handleChange}
          >
            <option value="">Any</option>
            <option value="full-time">Full-time</option>
            <option value="part-time">Part-time</option>
            <option value="contract">Contract</option>
            <option value="freelance">Freelance</option>
            <option value="internship">Internship</option>
          </select>
        </div>
      </div>

      <div className="grid-2">
        <div className="form-group">
          <label htmlFor="date_posted">Date Posted</label>
          <select
            id="date_posted"
            name="date_posted"
            value={filters.date_posted || ''}
            onChange={handleChange}
          >
            <option value="">Any time</option>
            <option value="today">Today</option>
            <option value="3days">Last 3 days</option>
            <option value="week">Last week</option>
            <option value="month">Last month</option>
          </select>
        </div>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              name="remote"
              checked={filters.remote || false}
              onChange={handleChange}
              style={{ width: 'auto', marginRight: '0.5rem' }}
            />
            Remote only
          </label>
        </div>
      </div>

      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? 'Searching...' : 'Search Jobs'}
      </button>
    </form>
  );
}