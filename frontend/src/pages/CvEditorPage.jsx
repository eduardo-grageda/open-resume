import { useState, useEffect, useCallback } from 'react';
import MdEditor from '../components/MdEditor';
import api from '../api';

const DEFAULT_TEMPLATE = `# Your Name

**Email:** your.email@example.com | **Phone:** +1234567890 | **Location:** City, Country
**LinkedIn:** linkedin.com/in/yourprofile | **GitHub:** github.com/yourusername

## Professional Summary

Brief summary of your professional background and key strengths.

## Skills

- **Category:** Technology 1, Technology 2
- **Category:** Technology 3, Technology 4

## Tools & Technologies

- **Category:** Tool 1, Tool 2

## Experience

### Job Title — Company Name
*Start Date - End Date | Location*

- Accomplishment or responsibility
- Another accomplishment

## Education

### Degree in Field
*Institution — Year*

## Projects

### Project Name
*Year*

Description of the project.

- **Technologies:** Tech 1, Tech 2

## Languages

- **Spoken:** English (Native), Spanish (Fluent)
- **Programming:** Python, JavaScript, TypeScript

## Certifications

- Certification Name — Issuer (Year)
`;

function cvToMarkdown(cv) {
  const pi = cv.personal_info || {};
  const contactParts = [];
  if (pi.email) contactParts.push(`**Email:** ${pi.email}`);
  if (pi.phone) contactParts.push(`**Phone:** ${pi.phone}`);
  if (pi.location) contactParts.push(`**Location:** ${pi.location}`);
  const links = [];
  if (pi.linkedin) links.push(`**LinkedIn:** ${pi.linkedin}`);
  if (pi.github) links.push(`**GitHub:** ${pi.github}`);
  if (pi.website) links.push(`**Website:** ${pi.website}`);

  let md = `# ${pi.first_name || ''} ${pi.last_name || ''}\n\n`;
  if (contactParts.length) md += contactParts.join(' | ') + '\n';
  if (links.length) md += links.join(' | ') + '\n';
  md += '\n';

  if (cv.professional_summary) {
    md += `## Professional Summary\n\n${cv.professional_summary}\n\n`;
  }

  if ((cv.skills || []).length) {
    md += '## Skills\n\n';
    for (const s of cv.skills) {
      md += `- **${s.category}:** ${(s.technologies || []).join(', ')}\n`;
    }
    md += '\n';
  }

  if ((cv.tools || []).length) {
    md += '## Tools & Technologies\n\n';
    for (const t of cv.tools) {
      md += `- **${t.category}:** ${(t.items || []).join(', ')}\n`;
    }
    md += '\n';
  }

  if ((cv.career || []).length) {
    md += '## Experience\n\n';
    for (const c of cv.career) {
      md += `### ${c.title} — ${c.company}\n`;
      md += `*${c.start_date} - ${c.end_date}${c.location ? ` | ${c.location}` : ''}*\n\n`;
      if (c.description) md += c.description + '\n\n';
      for (const acc of (c.accomplishments || [])) {
        md += `- ${acc}\n`;
      }
      md += '\n';
    }
  }

  if ((cv.formation || []).length) {
    md += '## Education\n\n';
    for (const e of cv.formation) {
      md += `### ${e.degree} in ${e.field}\n`;
      md += `*${e.institution} — ${e.end_year || e.start_year}*\n\n`;
      if (e.notes) md += e.notes + '\n\n';
    }
  }

  if ((cv.projects || []).length) {
    md += '## Projects\n\n';
    for (const p of cv.projects) {
      md += `### ${p.name}\n`;
      if (p.year) md += `*${p.year}*\n\n`;
      if (p.description) md += p.description + '\n\n';
      if ((p.technologies || []).length) md += `- **Technologies:** ${p.technologies.join(', ')}\n\n`;
    }
  }

  if (cv.languages) {
    md += '## Languages\n\n';
    const spoken = (cv.languages.spoken || []).map(l => `${l.language} (${l.level})`).join(', ');
    if (spoken) md += `- **Spoken:** ${spoken}\n`;
    if ((cv.languages.programming || []).length) md += `- **Programming:** ${cv.languages.programming.join(', ')}\n`;
    md += '\n';
  }

  if ((cv.certifications || []).length) {
    md += '## Certifications\n\n';
    for (const c of cv.certifications) {
      md += `- ${c.name} — ${c.issuer} (${c.year})\n`;
    }
    md += '\n';
  }

  return md;
}

export default function CvEditorPage() {
  const [cv, setCv] = useState(null);
  const [markdown, setMarkdown] = useState('');
  const [mode, setMode] = useState('markdown');
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCv();
  }, []);

  async function loadCv() {
    try {
      const data = await api.getCv();
      if (data.exists) {
        setCv(data.cv);
        setMarkdown(cvToMarkdown(data.cv));
        setMode('markdown');
      } else {
        setCv(null);
        setMarkdown(DEFAULT_TEMPLATE);
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
    setLoading(false);
  }

  function toggleMode() {
    if (mode === 'markdown' && cv) {
      setMode('structured');
    } else {
      setMarkdown(cvToMarkdown(cv));
      setMode('markdown');
    }
  }

  function updateStructuredField(path, value) {
    const updated = JSON.parse(JSON.stringify(cv));
    const keys = path.split('.');
    let obj = updated;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {};
      obj = obj[keys[i]];
    }
    obj[keys[keys.length - 1]] = value;
    setCv(updated);
    setMarkdown(cvToMarkdown(updated));
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      let cvData;
      if (mode === 'markdown') {
        cvData = {
          personal_info: cv?.personal_info || {},
          professional_summary: markdown,
          career: [],
          formation: [],
          skills: [],
          tools: [],
          accomplishments: [],
          hobbies: [],
          languages: { programming: [], spoken: [] },
          projects: [],
          certifications: [],
        };
        if (cv) {
          cvData.personal_info = cv.personal_info;
          cvData.career = cv.career;
          cvData.formation = cv.formation;
          cvData.skills = cv.skills;
          cvData.tools = cv.tools;
          cvData.accomplishments = cv.accomplishments;
          cvData.hobbies = cv.hobbies;
          cvData.languages = cv.languages;
          cvData.projects = cv.projects;
          cvData.certifications = cv.certifications;
        }
        setMessage({ type: 'info', text: 'Structured editing coming in Phase 3. Save edits below or toggle to structured mode.' });
        return;
      } else {
        cvData = cv;
      }
      await api.updateCv(cvData);
      setCv(cvData);
      setMessage({ type: 'success', text: 'CV saved.' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
    setSaving(false);
  }

  if (loading) return null;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Base CV</h1>
          <p>{cv ? 'Edit your comprehensive base CV.' : 'Start by filling in the template below.'}</p>
        </div>
        <div className="inline-row gap-1">
          {cv && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={toggleMode}>
              {mode === 'markdown' ? 'Structured Edit' : 'Markdown Edit'}
            </button>
          )}
          <button type="button" className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save CV'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}

      {mode === 'markdown' && (
        <MdEditor value={markdown} onChange={setMarkdown} />
      )}

      {mode === 'structured' && cv && (
        <div className="card">
          <div className="tabs">
            <button className="tab active">Personal Info</button>
            <button className="tab">Summary</button>
            <button className="tab">Career</button>
            <button className="tab">Education</button>
            <button className="tab">Skills</button>
            <button className="tab">Projects</button>
            <button className="tab">Languages</button>
          </div>
          <p className="text-secondary text-sm">Structured editing will be available in a future update.</p>
        </div>
      )}
    </div>
  );
}
