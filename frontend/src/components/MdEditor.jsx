import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

export default function MdEditor({ value, onChange, readOnly = false }) {
  const [showPreview, setShowPreview] = useState(true);

  const insertMarkdown = useCallback((prefix, suffix = '') => {
    if (readOnly) return;
    const textarea = document.getElementById('md-editor-textarea');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.substring(start, end);
    const before = value.substring(0, start);
    const after = value.substring(end);
    const newText = before + prefix + selected + suffix + after;
    onChange(newText);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + prefix.length,
        start + prefix.length + selected.length
      );
    }, 0);
  }, [value, onChange, readOnly]);

  const toolbarButtons = [
    { label: 'B', action: () => insertMarkdown('**', '**'), title: 'Bold' },
    { label: 'I', action: () => insertMarkdown('*', '*'), title: 'Italic' },
    { label: 'H1', action: () => insertMarkdown('# '), title: 'Heading 1' },
    { label: 'H2', action: () => insertMarkdown('## '), title: 'Heading 2' },
    { label: 'H3', action: () => insertMarkdown('### '), title: 'Heading 3' },
    { label: 'Link', action: () => insertMarkdown('[', '](url)'), title: 'Link' },
    { label: 'List', action: () => insertMarkdown('- '), title: 'Bullet list' },
    { label: 'Num', action: () => insertMarkdown('1. '), title: 'Numbered list' },
    { label: 'Code', action: () => insertMarkdown('```\n', '\n```'), title: 'Code block' },
    { label: '`', action: () => insertMarkdown('`', '`'), title: 'Inline code' },
  ];

  return (
    <div>
      {!readOnly && (
        <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {toolbarButtons.map(btn => (
            <button
              key={btn.title}
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={btn.action}
              title={btn.title}
            >
              {btn.label}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button
            type="button"
            className={`btn btn-sm ${showPreview ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? 'Hide Preview' : 'Show Preview'}
          </button>
        </div>
      )}
      <div style={{ display: showPreview ? 'grid' : 'block', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <textarea
          id="md-editor-textarea"
          value={value}
          onChange={e => onChange(e.target.value)}
          readOnly={readOnly}
          style={{
            width: '100%',
            minHeight: '400px',
            padding: '0.75rem',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            fontFamily: 'monospace',
            fontSize: '0.8125rem',
            lineHeight: 1.7,
            resize: 'vertical',
            background: readOnly ? 'var(--color-bg)' : 'var(--color-surface)',
            color: 'var(--color-text)',
            outline: 'none',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--color-primary)'}
          onBlur={e => e.target.style.borderColor = 'var(--color-border)'}
        />
        {showPreview && (
          <div
            style={{
              minHeight: '400px',
              padding: '0.75rem',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              background: 'var(--color-surface)',
              overflow: 'auto',
              fontSize: '0.875rem',
              lineHeight: 1.7,
            }}
          >
            {value.trim() ? (
              <ReactMarkdown>{value}</ReactMarkdown>
            ) : (
              <span className="text-secondary" style={{ fontSize: '0.8125rem' }}>Preview will appear here...</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
