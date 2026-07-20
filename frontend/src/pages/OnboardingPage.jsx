import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import OnboardingChat from '../components/OnboardingChat';

const SECTION_LABELS = {
  personal_info: 'Personal & Contact Info',
  professional_summary: 'Professional Summary',
  career: 'Work Experience',
  formation: 'Education',
  skills: 'Skills',
  tools: 'Tools & Technologies',
  accomplishments: 'Accomplishments',
  projects: 'Projects',
  certifications: 'Certifications',
  programming_languages: 'Programming Languages',
  spoken_languages: 'Spoken Languages',
  hobbies: 'Hobbies & Interests',
};

const ALL_SECTIONS = Object.keys(SECTION_LABELS);

function ProgressBar({ currentSection, completedSections }) {
  const total = ALL_SECTIONS.length;
  const completed = completedSections.length;
  const pct = Math.round((completed / total) * 100);

  return (
    <div className="onboard-progress">
      <div className="flex-between mb-2">
        <span className="text-sm text-secondary">
          Section: {SECTION_LABELS[currentSection] || currentSection}
        </span>
        <span className="text-sm text-secondary">{completed}/{total} sections</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ReviewGrid({ extractedData, onFieldChange, onConfirm, onBack }) {
  const [edits, setEdits] = useState(() => JSON.parse(JSON.stringify(extractedData)));

  const updateField = (section, field, value) => {
    const next = JSON.parse(JSON.stringify(edits));
    if (field) {
      if (!next[section]) next[section] = (typeof next[section] === 'object' && !Array.isArray(next[section])) ? {} : (value === '' || Array.isArray(value) ? value : (next[section] || ''))
      if (typeof next[section] === 'object' && !Array.isArray(next[section])) {
        next[section][field] = value;
      } else {
        next[section] = value;
      }
    } else {
      next[section] = value;
    }
    setEdits(next);
  };

  const updateArrayItem = (section, index, field, value) => {
    const next = JSON.parse(JSON.stringify(edits));
    if (!next[section]) next[section] = [];
    if (!next[section][index]) next[section][index] = {};
    next[section][index][field] = value;
    setEdits(next);
  };

  const addArrayItem = (section, template) => {
    const next = JSON.parse(JSON.stringify(edits));
    if (!next[section]) next[section] = [];
    next[section].push(JSON.parse(JSON.stringify(template)));
    setEdits(next);
  };

  const removeArrayItem = (section, index) => {
    const next = JSON.parse(JSON.stringify(edits));
    next[section].splice(index, 1);
    setEdits(next);
  };

  const renderField = (label, value, onChange, multiline) => {
    if (multiline) {
      return (
        <div className="form-group" key={label}>
          <label>{label}</label>
          <textarea value={value || ''} onChange={(e) => onChange(e.target.value)} rows={3} />
        </div>
      );
    }
    return (
      <div className="form-group" key={label}>
        <label>{label}</label>
        <input value={value || ''} onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  };

  const renderPersonalInfo = () => {
    const pi = edits.personal_info || {};
    const fields = [
      ['First Name', 'first_name'],
      ['Last Name', 'last_name'],
      ['Email', 'email'],
      ['Phone', 'phone'],
      ['Location', 'location'],
      ['Address', 'address'],
      ['Website', 'website'],
      ['LinkedIn', 'linkedin'],
      ['GitHub', 'github'],
      ['Twitter', 'twitter'],
    ];
    return fields.map(([label, key]) =>
      renderField(label, pi[key], (val) => updateField('personal_info', key, val))
    );
  };

  const renderArraySection = (section, fields, emptyTemplate) => {
    const items = edits[section] || [];
    return (
      <div>
        {items.map((item, i) => (
          <div key={i} className="card mb-2" style={{ position: 'relative' }}>
            <button
              className="btn btn-danger btn-sm"
              style={{ position: 'absolute', top: '0.5rem', right: '0.5rem' }}
              onClick={() => removeArrayItem(section, i)}
            >
              Remove
            </button>
            {fields.map(([label, key, multiline]) =>
              renderField(label, item[key], (val) => updateArrayItem(section, i, key, val), multiline)
            )}
          </div>
        ))}
        <button className="btn btn-secondary btn-sm" onClick={() => addArrayItem(section, emptyTemplate)}>
          + Add Entry
        </button>
      </div>
    );
  };

  return (
    <div className="review-grid">
      <div className="flex-between mb-3">
        <h2>Review Your CV</h2>
        <div className="inline-row gap-1">
          <button className="btn btn-secondary" onClick={onBack}>Back to Chat</button>
          <button className="btn btn-primary" onClick={() => onConfirm(edits)}>Save CV</button>
        </div>
      </div>

      {ALL_SECTIONS.map((section) => {
        const data = edits[section];
        const label = SECTION_LABELS[section];
        if (!data) return null;
        const isEmpty = typeof data === 'string' ? !data.trim() :
                         Array.isArray(data) ? data.length === 0 :
                         typeof data === 'object' ? Object.values(data).every(v => !v || (Array.isArray(v) && v.length === 0)) :
                         false;
        if (isEmpty) return null;

        return (
          <details key={section} className="review-section" open>
            <summary className="review-section-title">{label}</summary>
            <div className="review-section-body">
              {section === 'personal_info' && renderPersonalInfo()}
              {section === 'professional_summary' && renderField('Professional Summary', data, (val) => updateField(section, null, val), true)}
              {section === 'career' && renderArraySection(section,
                [['Company', 'company'], ['Title', 'title'], ['Start Date', 'start_date'], ['End Date', 'end_date'], ['Location', 'location'], ['Description', 'description', true]],
                { company: '', title: '', start_date: '', end_date: '', location: '', description: '', accomplishments: [], technologies: [] }
              )}
              {section === 'formation' && renderArraySection(section,
                [['Degree', 'degree'], ['Institution', 'institution'], ['Field', 'field'], ['Start Year', 'start_year'], ['End Year', 'end_year'], ['Notes', 'notes']],
                { degree: '', institution: '', field: '', start_year: '', end_year: '', notes: '' }
              )}
              {section === 'skills' && renderArraySection(section,
                [['Category', 'category'], ['Technologies (comma-separated)', 'technologies']],
                { category: '', technologies: [] }
              )}
              {section === 'tools' && renderArraySection(section,
                [['Category', 'category'], ['Items (comma-separated)', 'items']],
                { category: '', items: [] }
              )}
              {section === 'accomplishments' && renderArraySection(section,
                [['Title', 'title'], ['Description', 'description', true], ['Year', 'year']],
                { title: '', description: '', year: '' }
              )}
              {section === 'projects' && renderArraySection(section,
                [['Name', 'name'], ['URL', 'url'], ['Year', 'year'], ['Description', 'description', true]],
                { name: '', url: '', year: '', description: '', technologies: [] }
              )}
              {section === 'certifications' && renderArraySection(section,
                [['Name', 'name'], ['Issuer', 'issuer'], ['Year', 'year'], ['URL', 'url']],
                { name: '', issuer: '', year: '', url: '' }
              )}
              {(section === 'programming_languages' || section === 'spoken_languages' || section === 'hobbies') && (
                <div>
                  {section === 'programming_languages' && renderField('Programming Languages (comma-separated)', (edits.languages?.programming || []).join(', '), (val) => {
                    const next = JSON.parse(JSON.stringify(edits));
                    if (!next.languages) next.languages = { programming: [], spoken: [] };
                    next.languages.programming = val.split(',').map(s => s.trim()).filter(Boolean);
                    setEdits(next);
                  })}
                  {section === 'spoken_languages' && renderField('Spoken Languages (comma-separated: lang:level)', (edits.languages?.spoken || []).map(s => `${s.language}:${s.level}`).join(', '), (val) => {
                    const next = JSON.parse(JSON.stringify(edits));
                    if (!next.languages) next.languages = { programming: [], spoken: [] };
                    next.languages.spoken = val.split(',').map(s => s.trim()).filter(Boolean).map(s => {
                      const [language, level] = s.split(':').map(p => p.trim());
                      return { language: language || '', level: level || '' };
                    });
                    setEdits(next);
                  })}
                  {section === 'hobbies' && renderField('Hobbies (comma-separated)', (data || []).join(', '), (val) => {
                    updateField(section, null, val.split(',').map(s => s.trim()).filter(Boolean));
                  })}
                </div>
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState('start');
  const [sessionId, setSessionId] = useState(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentSection, setCurrentSection] = useState('');
  const [completedSections, setCompletedSections] = useState([]);
  const [extractedData, setExtractedData] = useState({});
  const [done, setDone] = useState(false);

  const handleStart = async (e) => {
    e.preventDefault();
    if (!firstName.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.onboardStart({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        target_role: targetRole.trim() || 'professional',
      });
      setSessionId(data.session_id);
      setMessages([
        { role: 'assistant', content: data.question },
      ]);
      setCurrentSection(data.section);
      setCompletedSections(data.completed_sections || []);
      setExtractedData(data.extracted_data || {});
      setDone(data.done);
      setStep('chat');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = async (answer) => {
    if (!sessionId || loading || done) return;
    setMessages((prev) => [...prev, { role: 'user', content: answer }]);
    setLoading(true);
    setError('');
    try {
      const data = await api.onboardAnswer({
        session_id: sessionId,
        answer,
      });
      setCurrentSection(data.section);
      setCompletedSections(data.completed_sections || []);
      setExtractedData(data.extracted_data || {});
      if (data.done) {
        setDone(true);
        setMessages((prev) => [...prev, { role: 'assistant', content: data.message || 'All sections complete!' }]);
      } else if (data.question) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.question }]);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (confirmedData) => {
    setLoading(true);
    setError('');
    try {
      await api.onboardConfirm({
        session_id: sessionId,
        confirmed_data: confirmedData,
      });
      navigate('/cv');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoToReview = () => setStep('review');

  const handleBackToChat = () => setStep('chat');

  if (step === 'review') {
    return (
      <div>
        <ReviewGrid
          extractedData={extractedData}
          onConfirm={handleConfirm}
          onBack={handleBackToChat}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Onboarding</h1>
        <p>AI-guided CV builder — answer questions to build your base CV.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {step === 'start' && (
        <div className="card" style={{ maxWidth: 480 }}>
          <form onSubmit={handleStart}>
            <div className="form-group">
              <label>First Name *</label>
              <input
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Your first name"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Last Name</label>
              <input
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Your last name"
              />
            </div>
            <div className="form-group">
              <label>Target Role</label>
              <input
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Software Engineer, Data Scientist..."
              />
              <div className="form-help">Optional. Helps tailor the questions.</div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !firstName.trim()}>
              {loading ? 'Starting...' : 'Start Interview'}
            </button>
          </form>
        </div>
      )}

      {step === 'chat' && (
        <div>
          {!done && completedSections.length > 0 && (
            <ProgressBar currentSection={currentSection} completedSections={completedSections} />
          )}

          {done && (
            <div className="alert alert-success mb-3">
              All sections complete! Review your CV below or continue chatting.
              <button className="btn btn-primary btn-sm" style={{ marginLeft: '0.5rem' }} onClick={handleGoToReview}>
                Review &amp; Save
              </button>
            </div>
          )}

          <OnboardingChat
            messages={messages}
            onSend={handleAnswer}
            disabled={loading}
          />
        </div>
      )}
    </div>
  );
}