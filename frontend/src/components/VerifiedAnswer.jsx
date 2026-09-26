import React from 'react';

export default function VerifiedAnswer({ response, onViewSource }) {
  if (!response) return null;

  const { question, status, answer, evidence, retrieval, refusal_reason } = response;

  const getStatusBadgeStyle = () => {
    switch (status) {
      case 'ANSWERED':
        return {
          backgroundColor: 'var(--status-available-bg)',
          color: 'var(--status-available)',
          border: '1px solid var(--status-available)',
        };
      case 'NOT_FOUND':
        return {
          backgroundColor: 'rgba(138, 133, 125, 0.12)',
          color: 'var(--ink-secondary)',
          border: '1px solid var(--ink-tertiary)',
        };
      case 'AMBIGUOUS':
      case 'UNRESOLVED':
        return {
          backgroundColor: 'var(--status-warning-bg)',
          color: 'var(--status-warning)',
          border: '1px solid var(--status-warning)',
        };
      case 'REFUSED':
      default:
        return {
          backgroundColor: 'var(--status-alert-bg)',
          color: 'var(--status-alert)',
          border: '1px solid var(--status-alert)',
        };
    }
  };

  return (
    <div
      id="verified-answer-card"
      style={{
        border: '1px solid var(--divider-line)',
        borderRadius: '4px',
        backgroundColor: 'var(--sheet-bg)',
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: 'var(--panel-shadow)',
        transition: 'all 180ms ease',
      }}
    >
      {/* Query Header Strip */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--ink-tertiary)',
            }}
          >
            Question
          </span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              padding: '2px 8px',
              borderRadius: '2px',
              ...getStatusBadgeStyle(),
            }}
          >
            {status}
          </span>
        </div>

        {retrieval && (
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--ink-tertiary)',
            }}
          >
            {retrieval.method}
          </span>
        )}
      </div>

      {/* The Question Text */}
      <div
        style={{
          fontSize: '13px',
          fontWeight: 600,
          color: 'var(--ink-primary)',
          lineHeight: 1.4,
        }}
      >
        {question}
      </div>

      {/* Answer Body */}
      <div
        className="font-serif"
        style={{
          fontSize: '15px',
          lineHeight: 1.6,
          color: 'var(--ink-primary)',
          backgroundColor: 'var(--surface-bg)',
          padding: '12px 14px',
          borderRadius: '3px',
          borderLeft: status === 'ANSWERED' ? '3px solid var(--accent-legal)' : '3px solid var(--ink-tertiary)',
        }}
      >
        {answer}
      </div>

      {/* Verbatim Physical Document Evidence Citations */}
      {status === 'ANSWERED' && evidence && evidence.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--ink-secondary)',
            }}
          >
            Physical Evidence Citation ({evidence.length} {evidence.length > 1 ? 'locations' : 'location'})
          </span>

          {evidence.map((cit, idx) => (
            <div
              key={`citation-${idx}`}
              style={{
                backgroundColor: 'var(--canvas-bg)',
                border: '1px solid var(--divider-line)',
                borderRadius: '3px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: 'var(--accent-legal)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {cit.clause_number ? `Clause ${cit.clause_number}` : 'Document Excerpt'} · Page {cit.page}
                </span>

                <button
                  id={`btn-view-source-${idx}`}
                  onClick={() => onViewSource && onViewSource(cit)}
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: 'var(--accent-legal)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '2px 6px',
                    borderRadius: '2px',
                  }}
                  title="Navigate directly to source clause on PDF surface"
                >
                  View source →
                </button>
              </div>

              <blockquote
                className="font-serif"
                style={{
                  fontSize: '13px',
                  fontStyle: 'italic',
                  color: 'var(--ink-secondary)',
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                "{cit.quote}"
              </blockquote>
            </div>
          ))}
        </div>
      )}

      {/* Honest Boundary / Refusal Explanation */}
      {status === 'REFUSED' && refusal_reason && (
        <div
          style={{
            fontSize: '11px',
            color: 'var(--status-alert)',
            backgroundColor: 'var(--status-alert-bg)',
            padding: '8px 10px',
            borderRadius: '3px',
            lineHeight: 1.4,
          }}
        >
          {refusal_reason}
        </div>
      )}
    </div>
  );
}
