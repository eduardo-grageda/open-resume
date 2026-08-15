import { useState, useEffect, useCallback } from 'react';
import api from '../api';
import OnboardingChat from '../components/OnboardingChat';

const STAR_STEPS = ['situation', 'task', 'action', 'result'];
const STAR_LABELS = { situation: 'Situation', task: 'Task', action: 'Action', result: 'Result' };

function StarProgress({ phase, starStep, storyIndex, totalStories }) {
  const stepIdx = STAR_STEPS.indexOf(starStep);
  const currentLabel = STAR_LABELS[starStep] || '';

  return (
    <div className="onboard-progress">
      <div className="flex-between mb-2">
        <span className="text-sm text-secondary">
          Phase: {phase === 'intro' ? 'Introduction' :
                   phase === 'select_achievements' ? 'Selecting Achievements' :
                   phase === 'star_questions' ? `STAR — ${currentLabel || 'Questioning'}` :
                   phase === 'review' ? 'Review' : phase}
        </span>
        {totalStories > 0 && (
          <span className="text-sm text-secondary">Story {storyIndex + 1} of {totalStories}</span>
        )}
      </div>
      {starStep && (
        <div className="progress-bar" style={{ marginBottom: '0.5rem' }}>
          <div className="progress-fill" style={{ width: `${((STAR_STEPS.indexOf(starStep) + 1) / 4) * 100}%` }} />
        </div>
      )}
      {starStep && (
        <div className="star-steps-indicator">
          {STAR_STEPS.map((step) => (
            <span key={step} className={`star-step-dot ${STAR_STEPS.indexOf(step) <= STAR_STEPS.indexOf(starStep) ? 'active' : ''}`}>
              {STAR_LABELS[step][0]}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function StoryEditor({ story, onUpdate, onSave, onDelete, onGeneratePitch }) {
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState({ ...story });

  const handleChange = (field, value) => {
    setEdited((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    setEditing(false);
    onUpdate(edited);
  };

  return (
    <div className="card mb-3">
      <div className="flex-between mb-2">
        <h3 className="no-margin">{edited.title || 'Untitled Story'}</h3>
        <div className="inline-row gap-1">
          <button className="btn btn-danger btn-sm" onClick={() => onDelete(story.id)}>Delete</button>
        </div>
      </div>

      {edited.source_company && (
        <p className="text-sm text-secondary mb-2">
          {edited.source_title} at {edited.source_company}
        </p>
      )}

      {editing ? (
        <div>
          <div className="form-group">
            <label>Title</label>
            <input value={edited.title || ''} onChange={(e) => handleChange('title', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Source Company</label>
            <input value={edited.source_company || ''} onChange={(e) => handleChange('source_company', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Source Title</label>
            <input value={edited.source_title || ''} onChange={(e) => handleChange('source_title', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Situation</label>
            <textarea value={edited.situation || ''} onChange={(e) => handleChange('situation', e.target.value)} rows={3} />
          </div>
          <div className="form-group">
            <label>Task</label>
            <textarea value={edited.task || ''} onChange={(e) => handleChange('task', e.target.value)} rows={3} />
          </div>
          <div className="form-group">
            <label>Action</label>
            <textarea value={edited.action || ''} onChange={(e) => handleChange('action', e.target.value)} rows={4} />
          </div>
          <div className="form-group">
            <label>Result</label>
            <textarea value={edited.result || ''} onChange={(e) => handleChange('result', e.target.value)} rows={3} />
          </div>
          <div className="form-group">
            <label>Interview Pitch</label>
            <textarea value={edited.interview_pitch || ''} onChange={(e) => handleChange('interview_pitch', e.target.value)} rows={4} />
          </div>
          <div className="inline-row gap-1">
            <button className="btn btn-primary btn-sm" onClick={handleSave}>Save</button>
            <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(false); setEdited({ ...story }); }}>Cancel</button>
          </div>
        </div>
      ) : (
        <div>
          {edited.situation && (
            <div className="mb-2">
              <strong className="text-primary">Situation</strong>
              <p className="text-sm">{edited.situation}</p>
            </div>
          )}
          {edited.task && (
            <div className="mb-2">
              <strong className="text-primary">Task</strong>
              <p className="text-sm">{edited.task}</p>
            </div>
          )}
          {edited.action && (
            <div className="mb-2">
              <strong className="text-primary">Action</strong>
              <p className="text-sm">{edited.action}</p>
            </div>
          )}
          {edited.result && (
            <div className="mb-2">
              <strong className="text-primary">Result</strong>
              <p className="text-sm">{edited.result}</p>
            </div>
          )}
          {edited.interview_pitch && (
            <div className="interview-pitch-box">
              <strong>Interview Pitch</strong>
              <p className="text-sm">{edited.interview_pitch}</p>
            </div>
          )}
          <div className="inline-row gap-1 mt-2">
            <button className="btn btn-secondary btn-sm" onClick={() => setEditing(true)}>Edit</button>
            {edited.situation && edited.task && edited.action && edited.result && !edited.interview_pitch && (
              <button className="btn btn-primary btn-sm" onClick={() => onGeneratePitch(story.id)}>Generate Pitch</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StoriesReview({ stories, onUpdate, onDelete, onGeneratePitch, onBack, onConfirm, loading }) {
  return (
    <div>
      <div className="flex-between mb-3">
        <h2>Your STAR Stories</h2>
        <div className="inline-row gap-1">
          <button className="btn btn-secondary" onClick={onBack} disabled={loading}>Back to Chat</button>
          <button className="btn btn-primary" onClick={onConfirm} disabled={loading}>
            {loading ? 'Saving...' : 'Save & Finish'}
          </button>
        </div>
      </div>

      {stories.length === 0 && (
        <div className="empty-state">
          <h3>No stories yet</h3>
          <p>Go back to the chat to build your STAR stories.</p>
        </div>
      )}

      {stories.map((story) => (
        <StoryEditor
          key={story.id || story.title}
          story={story}
          onUpdate={onUpdate}
          onSave={onUpdate}
          onDelete={onDelete}
          onGeneratePitch={onGeneratePitch}
        />
      ))}
    </div>
  );
}

export default function StarPage() {
  const [step, setStep] = useState('start');
  const [sessionId, setSessionId] = useState(null);
  const [targetRole, setTargetRole] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [phase, setPhase] = useState('');
  const [starStep, setStarStep] = useState('');
  const [stories, setStories] = useState([]);
  const [done, setDone] = useState(false);
  const [hasCv, setHasCv] = useState(null);

  useEffect(() => {
    api.getCv().then((d) => setHasCv(!!d.exists || !!d.personal_info)).catch(() => setHasCv(false));
  }, []);

  const handleStart = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await api.starStart({ target_role: targetRole.trim() });
      setSessionId(data.session_id);
      const msgs = [];
      if (data.retries > 0) {
        msgs.push({ role: 'system', content: `(Retried ${data.retries} time(s))` });
      }
      msgs.push({ role: 'assistant', content: data.question });
      setMessages(msgs);
      setPhase(data.phase);
      setStarStep(data.star_step);
      setStories(data.stories || []);
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
      const data = await api.starAnswer({ session_id: sessionId, answer });
      setPhase(data.phase);
      setStarStep(data.star_step);
      setStories(data.stories || []);
      if (data.done) {
        setDone(true);
        setMessages((prev) => [
          ...prev,
          ...(data.retries > 0 ? [{ role: 'system', content: `(Retried ${data.retries} time(s))` }] : []),
          { role: 'assistant', content: data.message || 'All STAR stories complete!' },
        ]);
      } else if (data.question) {
        setMessages((prev) => [
          ...prev,
          ...(data.retries > 0 ? [{ role: 'system', content: `(Retried ${data.retries} time(s))` }] : []),
          { role: 'assistant', content: data.question },
        ]);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoToReview = () => setStep('review');
  const handleBackToChat = () => setStep('chat');

  const handleUpdateStory = (updatedStory) => {
    setStories((prev) => prev.map((s) =>
      (s.id && s.id === updatedStory.id) || s.title === updatedStory.title ? updatedStory : s
    ));
  };

  const handleDeleteStory = (storyId) => {
    setStories((prev) => prev.filter((s) => s.id !== storyId));
  };

  const handleGeneratePitch = async (storyId) => {
    setLoading(true);
    try {
      const data = await api.generateStarPitch(storyId);
      setStories((prev) => prev.map((s) => s.id === storyId ? data.story : s));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);
    setError('');
    try {
      await api.starConfirm({ session_id: sessionId, confirmed_stories: stories });
      setStep('saved');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (hasCv === null) {
    return (
      <div>
        <div className="page-header"><h1>Interview Prep</h1></div>
        <div className="empty-state"><h3>Loading...</h3></div>
      </div>
    );
  }

  if (hasCv === false) {
    return (
      <div>
        <div className="page-header">
          <h1>Interview Prep</h1>
          <p>Build STAR stories for behavioral interviews using your CV.</p>
        </div>
        <div className="empty-state">
          <h3>No CV Found</h3>
          <p>You need a base CV first. Go to <strong>Base CV</strong> or <strong>Onboarding</strong> to create one.</p>
        </div>
      </div>
    );
  }

  if (step === 'saved') {
    return (
      <div>
        <div className="page-header">
          <h1>Interview Prep</h1>
          <p>Build STAR stories for behavioral interviews using your CV.</p>
        </div>
        <div className="alert alert-success mb-3">
          Your STAR stories have been saved. You can start a new session or review your saved stories below.
        </div>
        <SavedStories onStartNew={() => { setStep('start'); setDone(false); setStories([]); setMessages([]); }} />
      </div>
    );
  }

  if (step === 'review') {
    return (
      <div>
        <StoriesReview
          stories={stories}
          onUpdate={handleUpdateStory}
          onDelete={handleDeleteStory}
          onGeneratePitch={handleGeneratePitch}
          onBack={handleBackToChat}
          onConfirm={handleConfirm}
          loading={loading}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Interview Prep</h1>
        <p>Build STAR stories for behavioral interviews using your CV.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {step === 'start' && (
        <div className="card" style={{ maxWidth: 480 }}>
          <form onSubmit={handleStart}>
            <p className="text-secondary mb-3">
              The AI will review your CV, identify your most impactful achievements, and guide you through building
              structured STAR (Situation, Task, Action, Result) stories for behavioral interviews.
            </p>
            <div className="form-group">
              <label>Target Role (optional)</label>
              <input
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Senior Software Engineer, Engineering Manager..."
              />
              <div className="form-help">Helps the AI prioritize relevant achievements.</div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Analyzing CV...' : 'Start STAR Prep'}
            </button>
          </form>
        </div>
      )}

      {step === 'chat' && (
        <div>
          {!done && phase && (
            <StarProgress
              phase={phase}
              starStep={starStep}
              storyIndex={stories.length > 0 ? stories.length - 1 : 0}
              totalStories={stories.length}
            />
          )}

          {done && (
            <div className="alert alert-success mb-3">
              Your STAR stories are ready. Review and edit them before saving.
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

function SavedStories({ onStartNew }) {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listStarStories();
      setStories(data.stories || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadStories(); }, [loadStories]);

  const handleDelete = async (id) => {
    try {
      await api.deleteStarStory(id);
      setStories((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleUpdate = async (updated) => {
    try {
      await api.updateStarStory(updated.id, updated);
      setStories((prev) => prev.map((s) => s.id === updated.id ? updated : s));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleGeneratePitch = async (id) => {
    try {
      const data = await api.generateStarPitch(id);
      setStories((prev) => prev.map((s) => s.id === id ? data.story : s));
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <div className="empty-state"><h3>Loading saved stories...</h3></div>;

  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="flex-between mb-3">
        <h3>Saved Stories ({stories.length})</h3>
        <button className="btn btn-primary" onClick={onStartNew}>New STAR Session</button>
      </div>

      {stories.length === 0 && (
        <div className="empty-state">
          <h3>No saved stories yet</h3>
          <p>Start a new STAR session to build your interview stories.</p>
        </div>
      )}

      {stories.map((story) => (
        <StoryEditor
          key={story.id}
          story={story}
          onUpdate={handleUpdate}
          onSave={handleUpdate}
          onDelete={handleDelete}
          onGeneratePitch={handleGeneratePitch}
        />
      ))}
    </div>
  );
}