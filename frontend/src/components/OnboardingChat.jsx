import { useState, useEffect, useRef } from 'react';

export default function OnboardingChat({ messages, onSend, disabled }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="onboarding-chat">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            <div className="chat-role">{msg.role === 'assistant' ? 'AI' : 'You'}</div>
            <div className="chat-content">{msg.content}</div>
          </div>
        ))}
        {disabled && (
          <div className="chat-bubble assistant">
            <div className="chat-role">AI</div>
            <div className="chat-content typing-indicator">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your answer..."
          disabled={disabled}
          autoFocus
        />
        <button type="submit" className="btn btn-primary" disabled={disabled || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}