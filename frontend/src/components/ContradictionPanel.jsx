import React, { useState } from 'react';
import ContradictionCard from './ContradictionCard';

export default function ContradictionPanel({ contradictionData, onSelectSource, selectedSource }) {
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'CONFLICTS' | 'HARMONIOUS'

  if (!contradictionData) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--ink-tertiary)' }}>
        <p className="font-serif" style={{ fontSize: '13px', fontStyle: 'italic' }}>
          Upload or parse an agreement to view comparative evidence relationships.
        </p>
      </div>
    );
  }

  const { findings = [], total_conflicts = 0, evaluation_summary = '' } = contradictionData;

  const conflictsOnly = findings.filter((f) => f.status === 'CONFIRMED_CONFLICT');
  const harmoniousOnly = findings.filter((f) => f.status === 'NO_CONFLICT');

  const displayedFindings =
    filter === 'CONFLICTS'
      ? conflictsOnly
      : filter === 'HARMONIOUS'
      ? harmoniousOnly
      : findings;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', paddingBottom: '24px' }}>
      {/* Editorial Overview Header */}
      <div
        style={{
          padding: '14px 16px',
          backgroundColor: 'var(--canvas-bg)',
          borderRadius: '4px',
          border: '1px solid var(--divider-line)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
          }}
        >
          <span
            className="font-serif"
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--ink-primary)',
              letterSpacing: '0.01em',
            }}
          >
            Evidence Relationships & Comparative Covenants
          </span>
          <span
            className="font-mono"
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '10px',
              backgroundColor: 'var(--surface-bg)',
              color: 'var(--ink-secondary)',
              border: '1px solid var(--divider-line)',
            }}
          >
            {total_conflicts === 1 ? '1 Divergence' : `${total_conflicts} Divergences`}
          </span>
        </div>
        <p
          style={{
            fontSize: '11.5px',
            lineHeight: 1.5,
            color: 'var(--ink-secondary)',
            margin: 0,
          }}
        >
          {evaluation_summary || 'Comparing paired contractual covenants across matching subjects and scopes.'}
        </p>
      </div>

      {/* Filter Tabs */}
      {findings.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '3px',
              border: filter === 'ALL' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
              backgroundColor: filter === 'ALL' ? 'var(--accent-legal)' : 'var(--surface-bg)',
              color: filter === 'ALL' ? '#FFFFFF' : 'var(--ink-secondary)',
              cursor: 'pointer',
              transition: 'all 120ms ease',
            }}
          >
            All Relationships ({findings.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('CONFLICTS')}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '3px',
              border: filter === 'CONFLICTS' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
              backgroundColor: filter === 'CONFLICTS' ? 'var(--accent-legal)' : 'var(--surface-bg)',
              color: filter === 'CONFLICTS' ? '#FFFFFF' : 'var(--ink-secondary)',
              cursor: 'pointer',
              transition: 'all 120ms ease',
            }}
          >
            Divergent ({conflictsOnly.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('HARMONIOUS')}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '3px',
              border: filter === 'HARMONIOUS' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
              backgroundColor: filter === 'HARMONIOUS' ? 'var(--accent-legal)' : 'var(--surface-bg)',
              color: filter === 'HARMONIOUS' ? '#FFFFFF' : 'var(--ink-secondary)',
              cursor: 'pointer',
              transition: 'all 120ms ease',
            }}
          >
            Consistent ({harmoniousOnly.length})
          </button>
        </div>
      )}

      {/* Findings List */}
      {displayedFindings.length === 0 ? (
        <div
          style={{
            padding: '28px 16px',
            textAlign: 'center',
            borderRadius: '4px',
            border: '1px dashed var(--divider-line)',
            backgroundColor: 'var(--canvas-bg)',
          }}
        >
          <p
            className="font-serif"
            style={{
              fontSize: '13px',
              color: 'var(--ink-secondary)',
              fontStyle: 'italic',
              margin: '0 0 6px 0',
            }}
          >
            No conflicting statements detected.
          </p>
          <p style={{ fontSize: '11px', color: 'var(--ink-tertiary)', margin: 0 }}>
            All extracted contractual provisions maintain consistent values and actor attributions.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {displayedFindings.map((finding) => (
            <ContradictionCard
              key={finding.finding_id}
              finding={finding}
              onSelectSource={onSelectSource}
              selectedSource={selectedSource}
            />
          ))}
        </div>
      )}
    </div>
  );
}
