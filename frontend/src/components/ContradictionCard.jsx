import React from 'react';

export default function ContradictionCard({ finding, onSelectSource, selectedSource }) {
  if (!finding) return null;

  const isConflict = finding.status === 'CONFIRMED_CONFLICT';
  const isInsufficient = finding.status === 'INSUFFICIENT_CONTEXT';
  const isNoConflict = finding.status === 'NO_CONFLICT';

  const badgeText = isConflict
    ? 'Textual Divergence'
    : isInsufficient
    ? 'Context Incomplete'
    : 'Consistent Terms';

  const badgeSymbol = isConflict ? '≠' : isInsufficient ? '?' : '=';

  const subjectLabel = (finding.subject || 'OTHER')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const isSourceASelected = selectedSource && selectedSource.clause_id === finding.source_a.clause_id;
  const isSourceBSelected = selectedSource && selectedSource.clause_id === finding.source_b.clause_id;

  return (
    <div
      style={{
        padding: '14px',
        borderRadius: '4px',
        border: '1px solid var(--divider-line)',
        backgroundColor: 'var(--canvas-bg)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        transition: 'all 140ms ease',
      }}
    >
      {/* Card Header: Subject, Actor, Status Pill */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            className="font-serif"
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--ink-primary)',
            }}
          >
            {subjectLabel}
          </span>
          {finding.actor && finding.actor !== 'UNKNOWN' && (
            <span
              className="font-mono"
              style={{
                fontSize: '9.5px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                padding: '1px 6px',
                borderRadius: '2px',
                backgroundColor: 'var(--surface-bg)',
                color: 'var(--ink-secondary)',
                border: '1px solid var(--divider-line)',
              }}
            >
              Actor: {finding.actor.toLowerCase()}
            </span>
          )}
        </div>

        <span
          className="font-mono"
          style={{
            fontSize: '10px',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '10px',
            backgroundColor: isConflict
              ? 'var(--accent-soft)'
              : 'var(--surface-bg)',
            color: isConflict ? 'var(--accent-legal)' : 'var(--ink-secondary)',
            border: isConflict
              ? '1px solid var(--accent-border)'
              : '1px solid var(--divider-line)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <span>{badgeSymbol}</span>
          <span>{badgeText}</span>
        </span>
      </div>

      {/* Visual Relationship Grid (Source A vs Source B) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '10px',
          padding: '10px',
          borderRadius: '4px',
          backgroundColor: 'var(--surface-bg)',
          border: '1px solid var(--divider-line)',
        }}
      >
        {/* Source Statement A */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '10px 12px',
            borderRadius: '3px',
            backgroundColor: 'var(--sheet-bg)',
            border: isSourceASelected
              ? '1.5px solid var(--accent-legal)'
              : '1px solid var(--sheet-border)',
            boxShadow: isSourceASelected ? '0 0 8px var(--accent-glow)' : 'none',
            transition: 'all 120ms ease',
          }}
        >
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '10px',
                color: 'var(--ink-tertiary)',
                marginBottom: '4px',
              }}
            >
              <span className="font-mono" style={{ fontWeight: 600 }}>
                {finding.source_a.clause_number ? `Clause ${finding.source_a.clause_number}` : 'Passage A'}
              </span>
              <span className="font-mono">Page {finding.source_a.page_number}</span>
            </div>
            <div
              className="font-mono"
              style={{
                fontSize: '12.5px',
                fontWeight: 700,
                color: 'var(--ink-primary)',
                marginBottom: '6px',
              }}
            >
              {finding.value_a}
            </div>
            <p
              className="font-serif"
              style={{
                fontSize: '11px',
                fontStyle: 'italic',
                lineHeight: 1.45,
                color: 'var(--ink-secondary)',
                margin: 0,
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              "{finding.source_a.exact_quote}"
            </p>
          </div>

          <button
            type="button"
            onClick={() => onSelectSource(finding.source_a)}
            style={{
              marginTop: '10px',
              fontSize: '10.5px',
              fontWeight: 600,
              color: 'var(--accent-legal)',
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              alignSelf: 'flex-start',
            }}
          >
            <span>⌖ View source A</span>
            <span>&rarr;</span>
          </button>
        </div>

        {/* Source Statement B */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '10px 12px',
            borderRadius: '3px',
            backgroundColor: 'var(--sheet-bg)',
            border: isSourceBSelected
              ? '1.5px solid var(--accent-legal)'
              : '1px solid var(--sheet-border)',
            boxShadow: isSourceBSelected ? '0 0 8px var(--accent-glow)' : 'none',
            transition: 'all 120ms ease',
          }}
        >
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '10px',
                color: 'var(--ink-tertiary)',
                marginBottom: '4px',
              }}
            >
              <span className="font-mono" style={{ fontWeight: 600 }}>
                {finding.source_b.clause_number ? `Clause ${finding.source_b.clause_number}` : 'Passage B'}
              </span>
              <span className="font-mono">Page {finding.source_b.page_number}</span>
            </div>
            <div
              className="font-mono"
              style={{
                fontSize: '12.5px',
                fontWeight: 700,
                color: 'var(--ink-primary)',
                marginBottom: '6px',
              }}
            >
              {finding.value_b}
            </div>
            <p
              className="font-serif"
              style={{
                fontSize: '11px',
                fontStyle: 'italic',
                lineHeight: 1.45,
                color: 'var(--ink-secondary)',
                margin: 0,
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              "{finding.source_b.exact_quote}"
            </p>
          </div>

          <button
            type="button"
            onClick={() => onSelectSource(finding.source_b)}
            style={{
              marginTop: '10px',
              fontSize: '10.5px',
              fontWeight: 600,
              color: 'var(--accent-legal)',
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              alignSelf: 'flex-start',
            }}
          >
            <span>⌖ View source B</span>
            <span>&rarr;</span>
          </button>
        </div>
      </div>

      {/* Central Relationship Connector (Restrained, Editorial Distinction) */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 10px',
          borderRadius: '3px',
          backgroundColor: 'var(--surface-bg)',
          border: '1px solid var(--divider-line)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            className="font-mono"
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '1px 5px',
              borderRadius: '2px',
              backgroundColor: 'var(--canvas-bg)',
              color: 'var(--ink-primary)',
              border: '1px solid var(--divider-line)',
            }}
          >
            {badgeSymbol}
          </span>
          <span
            style={{
              fontSize: '11px',
              color: 'var(--ink-secondary)',
            }}
          >
            {isConflict
              ? `Source Relationship: Incompatible values across matching scope (${finding.value_a} vs ${finding.value_b})`
              : isInsufficient
              ? 'Operational Context Incomplete: Actor or scope not deterministically established'
              : 'Harmonious Provisions: Consistent values across scopes'}
          </span>
        </div>
        <span
          className="font-mono"
          style={{
            fontSize: '9.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--ink-tertiary)',
          }}
        >
          Bilateral
        </span>
      </div>

      {/* Factual Non-Adjudicating Explanation */}
      <p
        style={{
          fontSize: '11.5px',
          lineHeight: 1.5,
          color: 'var(--ink-secondary)',
          margin: 0,
        }}
      >
        {finding.explanation}
      </p>
    </div>
  );
}
