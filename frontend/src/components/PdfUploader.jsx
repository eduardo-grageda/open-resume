import { useState, useCallback } from 'react';
import api from '../api';

export default function PdfUploader({ onParsed }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState('');
  const [error, setError] = useState(null);

  const handleFile = useCallback(async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File too large (max 10MB).');
      return;
    }

    setError(null);
    setFilename(file.name);
    setUploading(true);

    try {
      const data = await api.ingestPdf(file);
      if (data.ok && data.parsed_cv) {
        onParsed(data.parsed_cv, data.raw_text);
      } else {
        setError('Failed to parse the PDF. Try again.');
      }
    } catch (err) {
      setError(err.message || 'Upload failed.');
    }
    setUploading(false);
  }, [onParsed]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div>
      <div
        className={`upload-zone ${dragOver ? 'upload-zone-active' : ''} ${uploading ? 'upload-zone-disabled' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && document.getElementById('pdf-file-input')?.click()}
      >
        {uploading ? (
          <div>
            <div className="spinner" style={{ margin: '0 auto 0.5rem' }} />
            <p className="text-sm text-secondary">Parsing {filename}...</p>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>&#128196;</p>
            <p style={{ fontWeight: 500, marginBottom: '0.25rem' }}>
              {filename ? `Selected: ${filename}` : 'Drop your CV PDF here'}
            </p>
            <p className="text-sm text-secondary">or click to browse (max 10MB)</p>
          </div>
        )}
      </div>
      <input
        id="pdf-file-input"
        type="file"
        accept=".pdf"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
      {error && <div className="alert alert-error mt-1">{error}</div>}
    </div>
  );
}