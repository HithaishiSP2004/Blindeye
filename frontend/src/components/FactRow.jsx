import React, { useState } from 'react';

const FIELD_LABELS = {
  agreement_type: 'Agreement Type',
  execution_date: 'Execution Date',
  landlord_name: 'Licensor / Landlord',
  tenant_name: 'Licensee / Tenant',
  property_address: 'Property Address',
  tenure_months: 'Agreement Tenure',
  commencement_date: 'Commencement Date',
  lock_in_months: 'Lock-in Period',
  monthly_rent: 'Monthly Rent',
  security_deposit: 'Security Deposit',
  deposit_refund_days: 'Deposit Refund Period',
  notice_period_days: 'Notice Period',
  maintenance_responsibility: 'Maintenance Responsibility',
  late_payment_penalty: 'Late Payment Penalty',
  permitted_use: 'Permitted Use',
  renewal_terms: 'Renewal Terms',
};

export default function FactRow({
  fieldKey,
  fact,
  claim,
  isActive,
  isHovered,
  onSelectFact,
  onHoverFact,
}) {
  const [showAudit, setShowAudit] = useState(false);

  // If neither fact nor claim is provided, render nothing
  if (!fact && !claim) return null;

  const label = FIELD_LABELS[fieldKey] || fieldKey.replace(/_/g, ' ');

  // Prefer claim status from Phase 4 Verification Gate if present, otherwise fall back to fact status
  const rawStatus = claim ? claim.status : fact ? fact.status : 'NOT_FOUND';
  const status = typeof rawStatus === 'string' ? rawStatus.toUpperCase() : 'NOT_FOUND';

  // Value resolution
  const displayValue = (claim && claim.value) || (fact && fact.value) || null;

  // Source & Coordinate resolution
  const source = claim?.source || null;
  const page = source?.page || fact?.page || null;
  const bbox = source?.bbox || fact?.bbox || null;
  const exactQuote = source?.exact_quote || fact?.exact_quote || null;
  const clauseNumber = source?.clause_number || fact?.source_clause_number || null;

  // Audit metadata from Phase 4 Verification Gate
  const verification = claim?.verification || null;

  // Double-coded indicator symbols, colors, and badge styling
  let statusBadge = null;
  let borderColor = 'var(--divider-line)';
  let bgTint = 'var(--surface-bg)';

  switch (status) {
    case 'VERIFIED':
      borderColor = 'var(--accent-legal)';
      bgTint = 'var(--accent-legal-bg)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--accent-legal)',
            backgroundColor: 'var(--accent-legal-bg)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid var(--accent-legal-border)',
          }}
        >
          <span style={{ fontSize: '8px' }}>●</span> VERIFIED
        </span>
      );
      break;

    case 'UNSUPPORTED':
      borderColor = '#C53030';
      bgTint = 'rgba(197, 48, 48, 0.05)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: '#C53030',
            backgroundColor: 'rgba(197, 48, 48, 0.08)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid rgba(197, 48, 48, 0.3)',
          }}
        >
          <span>✗</span> UNSUPPORTED
        </span>
      );
      break;

    case 'AMBIGUOUS':
      borderColor = 'var(--accent-gold)';
      bgTint = 'var(--accent-gold-bg)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--accent-gold)',
            backgroundColor: 'var(--accent-gold-bg)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid var(--accent-gold-border)',
          }}
        >
          <span>◇</span> AMBIGUOUS
        </span>
      );
      break;

    case 'UNRESOLVED':
      borderColor = 'var(--status-sparse)';
      bgTint = 'var(--status-sparse-bg)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 600,
            color: 'var(--status-sparse)',
            backgroundColor: 'var(--status-sparse-bg)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid rgba(184, 134, 11, 0.2)',
          }}
        >
          <span>?</span> UNRESOLVED
        </span>
      );
      break;

    case 'CONTRADICTORY':
      borderColor = '#9B2C2C';
      bgTint = 'rgba(155, 44, 44, 0.08)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 700,
            color: '#9B2C2C',
            backgroundColor: 'rgba(155, 44, 44, 0.1)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid rgba(155, 44, 44, 0.4)',
          }}
        >
          <span>⚡</span> CONTRADICTORY
        </span>
      );
      break;

    case 'REFUSED':
      borderColor = '#742A2A';
      bgTint = 'rgba(116, 42, 42, 0.08)';
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 700,
            color: '#742A2A',
            backgroundColor: 'rgba(116, 42, 42, 0.1)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid rgba(116, 42, 42, 0.4)',
          }}
        >
          <span>⊘</span> REFUSED
        </span>
      );
      break;

    case 'NOT_FOUND':
    default:
      statusBadge = (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9.5px',
            fontWeight: 500,
            color: 'var(--ink-tertiary)',
            backgroundColor: 'var(--canvas-bg)',
            padding: '2px 7px',
            borderRadius: '2px',
            border: '1px solid var(--divider-line)',
          }}
        >
          <span>—</span> NOT FOUND
        </span>
      );
      break;
  }

  const isHighlighted = isActive || isHovered;

  return (
    <div
      id={`fact-row-${fieldKey}`}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      aria-label={`View evidence for ${label}: ${displayValue || 'Not established in document'}`}
      onClick={() => onSelectFact(fieldKey, fact || claim)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelectFact(fieldKey, fact || claim);
        }
      }}
      onMouseEnter={() => onHoverFact(fieldKey)}
      onMouseLeave={() => onHoverFact(null)}
      style={{
        padding: '12px 14px',
        borderRadius: '3px',
        border: isHighlighted
          ? '1px solid var(--accent-legal)'
          : `1px solid ${borderColor === 'var(--divider-line)' ? 'var(--divider-line)' : borderColor}`,
        backgroundColor: isActive
          ? 'var(--accent-legal-bg)'
          : isHovered
          ? 'var(--canvas-bg)'
          : bgTint,
        boxShadow: isHighlighted ? '0 1px 4px rgba(184, 134, 11, 0.12)' : 'none',
        cursor: 'pointer',
        transition: 'all 140ms ease',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}
    >
      {/* Top Header: Field Label + State Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: isHighlighted ? 'var(--accent-legal)' : 'var(--ink-secondary)',
          }}
        >
          {label}
        </span>
        {statusBadge}
      </div>

      {/* Primary Value */}
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <span
          className="font-serif"
          style={{
            fontSize: '13.5px',
            fontWeight: displayValue ? 600 : 400,
            color: displayValue ? 'var(--ink-primary)' : 'var(--ink-tertiary)',
            fontStyle: displayValue ? 'normal' : 'italic',
          }}
        >
          {displayValue || 'Not established in document'}
        </span>

        {/* Physical coordinate link indicator */}
        {page && bbox ? (
          <span
            className="font-mono"
            style={{
              fontSize: '10px',
              color: 'var(--accent-legal)',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
            }}
          >
            <span>⌖</span> P. 0{page}
          </span>
        ) : (
          <span
            className="font-mono"
            style={{
              fontSize: '9px',
              color: 'var(--ink-tertiary)',
              letterSpacing: '0.02em',
            }}
          >
            {status === 'NOT_FOUND' ? 'No source' : 'Source coords unavailable'}
          </span>
        )}
      </div>

      {/* Verbatim Document Evidence Quote (when VERIFIED or FOUND) */}
      {(status === 'VERIFIED' || status === 'FOUND') && exactQuote && (
        <div
          style={{
            marginTop: '4px',
            padding: '6px 10px',
            backgroundColor: 'var(--canvas-bg)',
            borderLeft: '2px solid var(--accent-legal)',
            borderRadius: '0 2px 2px 0',
          }}
        >
          <p
            className="font-serif"
            style={{
              fontSize: '11px',
              lineHeight: 1.45,
              color: 'var(--ink-secondary)',
              fontStyle: 'italic',
              margin: 0,
            }}
          >
            "{exactQuote}"
          </p>
          {clauseNumber && (
            <span
              style={{
                display: 'block',
                marginTop: '4px',
                fontSize: '9px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--ink-tertiary)',
              }}
            >
              Source: Clause {clauseNumber}
            </span>
          )}
        </div>
      )}

      {/* Ambiguity Candidates Details */}
      {status === 'AMBIGUOUS' && fact?.ambiguity_candidates && fact.ambiguity_candidates.length > 0 && (
        <div
          style={{
            marginTop: '4px',
            padding: '6px 10px',
            backgroundColor: 'var(--accent-gold-bg)',
            borderLeft: '2px solid var(--accent-gold)',
            borderRadius: '0 2px 2px 0',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: 'var(--accent-gold)',
              display: 'block',
              marginBottom: '3px',
            }}
          >
            {fact.ambiguity_candidates.length} candidate clauses matched:
          </span>
          {fact.ambiguity_candidates.map((cand, idx) => (
            <div key={idx} style={{ fontSize: '10px', color: 'var(--ink-secondary)', marginBottom: '2px' }}>
              • Clause {cand.clause_number} (P. {cand.page}): "{cand.quote}"
            </div>
          ))}
        </div>
      )}

      {/* Verification Audit Trail Toggle (Phase 4 Observability) */}
      {verification && (
        <div style={{ marginTop: '4px', borderTop: '1px dashed var(--divider-line)', paddingTop: '4px' }}>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowAudit((prev) => !prev);
            }}
            aria-expanded={showAudit}
            aria-label={`Toggle verification audit trail for ${label}`}
            style={{
              width: '100%',
              fontSize: '9px',
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--ink-tertiary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '2px 0',
              background: 'none',
              border: 'none',
            }}
          >
            <span>
              Audit Trail: {verification.resolution_method || 'DETERMINISTIC_CHECK'}
            </span>
            <span style={{ fontSize: '10px' }}>{showAudit ? '▲' : '▼'}</span>
          </button>

          {showAudit && (
            <div
              style={{
                marginTop: '4px',
                padding: '6px 8px',
                backgroundColor: 'var(--canvas-bg)',
                borderRadius: '2px',
                fontSize: '9.5px',
                fontFamily: 'monospace',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                color: 'var(--ink-secondary)',
              }}
            >
              <div>Method: <strong>{verification.resolution_method || 'DETERMINISTIC'}</strong></div>
              <div>Deterministic: <strong>{verification.deterministic_result || 'None'}</strong></div>
              <div>Semantic: <strong>{verification.semantic_result || 'SKIPPED'}</strong></div>
              <div>Contradiction: <strong>{verification.contradiction_result}</strong></div>
              {verification.reason_code && <div>Reason Code: <strong>{verification.reason_code}</strong></div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
