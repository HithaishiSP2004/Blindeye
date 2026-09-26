import React, { useState } from 'react';
import FactRow from './FactRow';
import QuestionDesk from './QuestionDesk';

const FACT_GROUPS = [
  {
    title: 'Essential Financial & Tenure',
    fields: ['monthly_rent', 'security_deposit', 'tenure_months', 'commencement_date'],
  },
  {
    title: 'Parties & Agreement Identity',
    fields: ['agreement_type', 'execution_date', 'landlord_name', 'tenant_name', 'property_address'],
  },
  {
    title: 'Operational Terms & Notice',
    fields: ['deposit_refund_days', 'notice_period_days', 'maintenance_responsibility', 'lock_in_months'],
  },
  {
    title: 'Contingencies & Covenants',
    fields: ['late_payment_penalty', 'permitted_use', 'renewal_terms'],
  },
];

export default function EvidencePanel({
  documentData,
  structuredAgreement,
  verificationResult,
  activeClauseId,
  hoveredClauseId,
  activeFactField,
  hoveredFactField,
  onHoverClause,
  onSelectClause,
  onSelectFact,
  onHoverFact,
  rawFile,
  onNavigateToCitation,
}) {
  const [activeTab, setActiveTab] = useState('facts'); // 'facts', 'clauses', or 'qa'
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL', 'VERIFIED', 'NOT_FOUND', 'UNSUPPORTED', 'AMBIGUOUS'


  // Automatic Smooth Navigation in Evidence Panel when Fact is Selected (Section 9: Bidirectional Source ➔ Fact)
  React.useEffect(() => {
    if (activeFactField && activeTab === 'facts') {
      const el = document.getElementById(`fact-row-${activeFactField}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeFactField, activeTab]);

  if (!documentData) {
    return (
      <div
        style={{
          padding: '40px 24px',
          color: 'var(--ink-tertiary)',
          fontSize: '13px',
          textAlign: 'center',
        }}
      >
        <p className="font-serif" style={{ fontStyle: 'italic', color: 'var(--ink-secondary)' }}>
          Evidence index will appear once an agreement is parsed.
        </p>
      </div>
    );
  }

  const substantiveClauses = documentData.clauses.filter((c) => !c.is_header_footer);

  // Map atomic claims by field_name for instant lookup
  const claimsByField = {};
  if (verificationResult?.claims) {
    verificationResult.claims.forEach((claim) => {
      if (claim.field_name) {
        claimsByField[claim.field_name] = claim;
      }
    });
  }

  // Summary counts: prioritize Phase 4 VerificationSummary, fall back to structuredAgreement.summary
  const vSummary = verificationResult?.summary;
  const saSummary = structuredAgreement?.summary;

  const totalReviewed = vSummary ? vSummary.total : saSummary ? saSummary.fields_total : 16;
  const verifiedCount = vSummary ? vSummary.verified : saSummary ? saSummary.fields_found : 0;
  const notFoundCount = vSummary ? vSummary.not_found : saSummary ? saSummary.fields_not_found : 0;
  const ambiguousCount = vSummary ? vSummary.ambiguous : saSummary ? saSummary.fields_ambiguous : 0;
  const unresolvedCount = vSummary ? vSummary.unresolved : 0;
  const unsupportedCount = vSummary ? vSummary.unsupported : 0;

  // Filter helper
  const matchesFilter = (fieldKey) => {
    if (statusFilter === 'ALL') return true;
    const claim = claimsByField[fieldKey];
    const fact = structuredAgreement?.[fieldKey];
    const status = (claim?.status || fact?.status || 'NOT_FOUND').toUpperCase();

    if (statusFilter === 'VERIFIED') return status === 'VERIFIED' || status === 'FOUND';
    if (statusFilter === 'NOT_FOUND') return status === 'NOT_FOUND';
    if (statusFilter === 'UNSUPPORTED') return status === 'UNSUPPORTED';
    if (statusFilter === 'AMBIGUOUS') return status === 'AMBIGUOUS' || status === 'UNRESOLVED';
    return true;
  };

  return (
    <div
      style={{
        padding: '24px 28px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        height: '100%',
        overflowY: 'auto',
      }}
    >
      {/* Top Editorial Navigation Strip */}
      <div
        style={{
          borderBottom: '1px solid var(--divider-line)',
          paddingBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveTab('facts')}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                padding: '6px 14px',
                borderRadius: '3px',
                border: activeTab === 'facts' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
                backgroundColor: activeTab === 'facts' ? 'var(--accent-legal)' : 'var(--surface-bg)',
                color: activeTab === 'facts' ? '#FFFFFF' : 'var(--ink-secondary)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              Factual Claims ({verifiedCount}/{totalReviewed})
            </button>
            <button
              id="tab-clauses"
              onClick={() => setActiveTab('clauses')}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                padding: '6px 14px',
                borderRadius: '3px',
                border: activeTab === 'clauses' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
                backgroundColor: activeTab === 'clauses' ? 'var(--accent-legal)' : 'var(--surface-bg)',
                color: activeTab === 'clauses' ? '#FFFFFF' : 'var(--ink-secondary)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              Clause Index ({substantiveClauses.length})
            </button>
            <button
              id="tab-qa"
              onClick={() => setActiveTab('qa')}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                padding: '6px 14px',
                borderRadius: '3px',
                border: activeTab === 'qa' ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
                backgroundColor: activeTab === 'qa' ? 'var(--accent-legal)' : 'var(--surface-bg)',
                color: activeTab === 'qa' ? '#FFFFFF' : 'var(--ink-secondary)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              Ask Agreement
            </button>
          </div>


          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: 'var(--status-available)',
              backgroundColor: 'var(--status-available-bg)',
              padding: '2px 8px',
              borderRadius: '2px',
              letterSpacing: '0.04em',
            }}
          >
            ✓ {verificationResult?.document_status || documentData.parsing_status}
          </span>
        </div>

        {/* Factual Metrics Strip (Correction 10: strictly factual claim counters, zero vague AI confidence) */}
        {activeTab === 'facts' && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '8px',
              padding: '12px 14px',
              backgroundColor: 'var(--canvas-bg)',
              borderRadius: '3px',
              border: '1px solid var(--divider-line)',
              marginBottom: '12px',
            }}
          >
            <div>
              <span style={{ fontSize: '9px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-tertiary)', display: 'block' }}>
                Reviewed
              </span>
              <span className="font-mono" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--ink-primary)' }}>
                {totalReviewed}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '9px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-tertiary)', display: 'block' }}>
                Verified
              </span>
              <span className="font-mono" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-legal)' }}>
                ● {verifiedCount}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '9px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-tertiary)', display: 'block' }}>
                Not Found
              </span>
              <span className="font-mono" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-secondary)' }}>
                — {notFoundCount}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '9px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-tertiary)', display: 'block' }}>
                Ambiguous
              </span>
              <span className="font-mono" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--accent-gold)' }}>
                ◇ {ambiguousCount + unresolvedCount}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '9px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-tertiary)', display: 'block' }}>
                Unsupported
              </span>
              <span className="font-mono" style={{ fontSize: '14px', fontWeight: 700, color: unsupportedCount > 0 ? '#C53030' : 'var(--ink-tertiary)' }}>
                ✗ {unsupportedCount}
              </span>
            </div>
          </div>
        )}

        {/* Filter Chips Bar */}
        {activeTab === 'facts' && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: `All (${totalReviewed})` },
              { id: 'VERIFIED', label: `Verified (${verifiedCount})` },
              { id: 'NOT_FOUND', label: `Not Found (${notFoundCount})` },
              { id: 'UNSUPPORTED', label: `Unsupported (${unsupportedCount})` },
              { id: 'AMBIGUOUS', label: `Ambiguous / Unresolved (${ambiguousCount + unresolvedCount})` },
            ].map((chip) => (
              <button
                key={chip.id}
                onClick={() => setStatusFilter(chip.id)}
                style={{
                  fontSize: '9.5px',
                  fontWeight: 600,
                  letterSpacing: '0.04em',
                  padding: '3px 8px',
                  borderRadius: '2px',
                  border: statusFilter === chip.id ? '1px solid var(--accent-legal)' : '1px solid var(--divider-line)',
                  backgroundColor: statusFilter === chip.id ? 'var(--accent-legal-bg)' : 'transparent',
                  color: statusFilter === chip.id ? 'var(--accent-legal)' : 'var(--ink-tertiary)',
                  cursor: 'pointer',
                  transition: 'all 120ms ease',
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* VIEW 1: STRUCTURED FACTS LIST */}
      {activeTab === 'facts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {FACT_GROUPS.map((group) => {
            const visibleFields = group.fields.filter(matchesFilter);
            if (visibleFields.length === 0) return null;

            return (
              <div key={group.title} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    color: 'var(--ink-tertiary)',
                    borderBottom: '1px solid var(--divider-line)',
                    paddingBottom: '4px',
                  }}
                >
                  {group.title}
                </span>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {visibleFields.map((fieldKey) => {
                    const fact = structuredAgreement?.[fieldKey];
                    const claim = claimsByField[fieldKey];
                    const isActive = activeFactField === fieldKey;
                    const isHovered = hoveredFactField === fieldKey;

                    return (
                      <FactRow
                        key={fieldKey}
                        fieldKey={fieldKey}
                        fact={fact}
                        claim={claim}
                        isActive={isActive}
                        isHovered={isHovered}
                        onSelectFact={onSelectFact}
                        onHoverFact={onHoverFact}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* Integrated Research Desk below Facts (Correction 22) */}
          <div style={{ marginTop: '20px' }}>

            <QuestionDesk
              rawFile={rawFile}
              documentData={documentData}
              onNavigateToCitation={onNavigateToCitation}
            />
          </div>
        </div>
      )}

      {/* VIEW 2: CLAUSE EVIDENCE INDEX */}
      {activeTab === 'clauses' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {substantiveClauses.map((clause) => {
            const isActive = activeClauseId === clause.clause_id;
            const isHovered = hoveredClauseId === clause.clause_id;
            const isHierarchical = clause.hierarchy_level > 1;

            return (
              <div
                key={clause.clause_id}
                onClick={() => onSelectClause(isActive ? null : clause.clause_id)}
                onMouseEnter={() => onHoverClause(clause.clause_id)}
                onMouseLeave={() => onHoverClause(null)}
                style={{
                  padding: '14px 16px',
                  marginLeft: isHierarchical ? '16px' : '0',
                  borderRadius: '3px',
                  border: isActive
                    ? '1px solid var(--accent-legal)'
                    : isHovered
                    ? '1px solid var(--ink-secondary)'
                    : '1px solid var(--divider-line)',
                  backgroundColor: isActive
                    ? 'var(--accent-legal-bg)'
                    : isHovered
                    ? 'var(--canvas-bg)'
                    : 'var(--surface-bg)',
                  boxShadow: isActive ? '0 1px 4px rgba(184, 134, 11, 0.15)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 140ms ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span
                      className="font-mono"
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isActive ? 'var(--accent-legal)' : 'var(--ink-primary)',
                      }}
                    >
                      Clause {clause.clause_number}
                    </span>
                    {clause.title && (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: 'var(--ink-secondary)',
                          letterSpacing: '0.02em',
                        }}
                      >
                        {clause.title}
                      </span>
                    )}
                  </div>
                  <span
                    className="font-mono"
                    style={{ fontSize: '10px', color: 'var(--ink-tertiary)' }}
                  >
                    P. {clause.pages.join(', ')}
                  </span>
                </div>

                <p
                  className="font-serif"
                  style={{
                    fontSize: '12px',
                    lineHeight: 1.5,
                    color: 'var(--ink-secondary)',
                    margin: 0,
                    display: '-webkit-box',
                    WebkitLineClamp: isActive ? 'none' : 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {clause.text}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* VIEW 3: DEDICATED Q&A RESEARCH DESK (Correction 21 & 22) */}
      {activeTab === 'qa' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <QuestionDesk
            rawFile={rawFile}
            documentData={documentData}
            onNavigateToCitation={onNavigateToCitation}
          />
        </div>
      )}
    </div>
  );
}

