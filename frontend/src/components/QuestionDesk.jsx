import React, { useState } from 'react';
import VerifiedAnswer from './VerifiedAnswer';
import { askDocument } from '../api/client';

const SUGGESTED_QUERIES = [
  { label: 'Monthly Rent', query: 'What is the monthly rent?' },
  { label: 'Security Deposit', query: 'How much is the security deposit?' },
  { label: 'Notice Period', query: 'What is the notice period?' },
  { label: 'Minor Repairs', query: 'Who is responsible for minor leakages?' },
  { label: 'Lock-in Period', query: 'Is there a lock-in period?' },
  { label: 'Property Address', query: 'What is the property address?' },
];

const BOUNDARY_QUERIES = [
  { label: 'Is notice enforceable?', query: 'Is the termination clause legally enforceable?' },
  { label: 'External Law', query: 'What does the law say about this agreement?' },
];

export default function QuestionDesk({
  rawFile,
  documentData,
  onNavigateToCitation,
}) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [history, setHistory] = useState([]);

  const handleAsk = async (queryText) => {
    const q = (queryText || question).trim();
    if (!q) return;

    if (!rawFile) {
      setError('Please upload or load a PDF agreement first.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await askDocument(rawFile, q, history);
      setCurrentResponse(resp);

      // Append lightweight context for coreference resolution (context only, never evidence)
      setHistory((prev) => [
        ...prev.slice(-4), // keep last 4 turns
        { role: 'user', text: q },
        { role: 'assistant', text: resp.answer },
      ]);
    } catch (err) {
      setError(err.message || 'Failed to answer agreement inquiry.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleAsk(question);
  };

  const handleSelectSuggested = (item) => {
    setQuestion(item.query);
    handleAsk(item.query);
  };

  return (
    <div
      id="question-desk"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '18px 20px',
        backgroundColor: 'var(--sheet-bg)',
        border: '1px solid var(--divider-line)',
        borderRadius: '4px',
        boxShadow: 'var(--panel-shadow)',
      }}
    >
      {/* Desk Title Strip */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3
            className="font-serif"
            style={{
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--ink-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            Research Desk: Ask Agreement
          </h3>
          <p
            style={{
              fontSize: '11px',
              color: 'var(--ink-tertiary)',
              marginTop: '2px',
            }}
          >
            Factual inquiry verified strictly against physical clauses.
          </p>
        </div>

        {currentResponse && (
          <button
            onClick={() => {
              setCurrentResponse(null);
              setQuestion('');
            }}
            style={{
              fontSize: '11px',
              color: 'var(--ink-tertiary)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Query Input Bar */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
        <input
          id="qa-question-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask e.g. 'What is the monthly rent?' or 'What does Clause 3 say?'"
          disabled={loading || !rawFile}
          style={{
            flex: 1,
            padding: '9px 14px',
            fontSize: '13px',
            fontFamily: 'var(--font-sans)',
            backgroundColor: 'var(--canvas-bg)',
            color: 'var(--ink-primary)',
            border: '1px solid var(--divider-line)',
            borderRadius: '3px',
            outline: 'none',
            transition: 'border-color 150ms ease',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'var(--accent-legal)')}
          onBlur={(e) => (e.target.style.borderColor = 'var(--divider-line)')}
        />
        <button
          id="qa-submit-btn"
          type="submit"
          disabled={loading || !question.trim() || !rawFile}
          style={{
            padding: '9px 18px',
            fontSize: '12px',
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            backgroundColor: loading || !question.trim() || !rawFile ? 'var(--divider-line)' : 'var(--accent-legal)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '3px',
            cursor: loading || !question.trim() || !rawFile ? 'not-allowed' : 'pointer',
            transition: 'all 150ms ease',
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Verifying...' : 'Ask Agreement'}
        </button>
      </form>

      {/* Suggested Query Chips (Correction 23) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--ink-tertiary)',
              marginRight: '2px',
            }}
          >
            Suggested:
          </span>
          {SUGGESTED_QUERIES.map((item, idx) => (
            <button
              key={`sugg-${idx}`}
              id={`chip-sugg-${idx}`}
              type="button"
              onClick={() => handleSelectSuggested(item)}
              disabled={loading || !rawFile}
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                borderRadius: '3px',
                border: '1px solid var(--divider-line)',
                backgroundColor: 'var(--surface-bg)',
                color: 'var(--ink-secondary)',
                cursor: loading || !rawFile ? 'not-allowed' : 'pointer',
                transition: 'all 120ms ease',
              }}
              onMouseEnter={(e) => {
                if (!loading && rawFile) e.target.style.borderColor = 'var(--accent-legal)';
              }}
              onMouseLeave={(e) => {
                e.target.style.borderColor = 'var(--divider-line)';
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Subtle Boundary Test Queries (Correction 23) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--ink-tertiary)',
              marginRight: '2px',
            }}
          >
            Boundary Test:
          </span>
          {BOUNDARY_QUERIES.map((item, idx) => (
            <button
              key={`bound-${idx}`}
              id={`chip-boundary-${idx}`}
              type="button"
              onClick={() => handleSelectSuggested(item)}
              disabled={loading || !rawFile}
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                borderRadius: '3px',
                border: '1px dashed var(--ink-tertiary)',
                backgroundColor: 'transparent',
                color: 'var(--ink-tertiary)',
                cursor: loading || !rawFile ? 'not-allowed' : 'pointer',
                transition: 'all 120ms ease',
              }}
              title="Demonstrates policy refusal without legal advice"
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            fontSize: '12px',
            color: 'var(--status-alert)',
            backgroundColor: 'var(--status-alert-bg)',
            padding: '8px 12px',
            borderRadius: '3px',
            border: '1px solid var(--status-alert)',
          }}
        >
          {error}
        </div>
      )}

      {/* Verified Answer Presentation */}
      {currentResponse && (
        <VerifiedAnswer
          response={currentResponse}
          onViewSource={(cit) => onNavigateToCitation && onNavigateToCitation(cit)}
        />
      )}
    </div>
  );
}
