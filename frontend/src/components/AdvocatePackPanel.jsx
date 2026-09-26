import React from 'react';

/**
 * AdvocatePackPanel
 *
 * Evidentiary Agreement Review Dossier (Advocate Preparation Pack)
 * Strictly non-evaluative:
 * - 4-tier evidence taxonomy ONLY (EXPLICIT_IN_DOCUMENT, DERIVED_FROM_CLAUSES, CONFLICTING_EVIDENCE, NO_SUPPORTING_PASSAGE)
 * - Document Coverage & Clarification Gaps (copy: "No supporting provision found for this field.")
 * - Every value originates from verified claims with physical provenance
 * - Lightweight print export (window.print())
 * - Zero legal enforceability claims or statutory advice
 */

function getClassificationBadge(classification) {
  switch (classification) {
    case 'EXPLICIT_IN_DOCUMENT':
      return (
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: 'rgba(180, 83, 9, 0.12)',
            color: '#b45309',
            border: '1px solid rgba(180, 83, 9, 0.28)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          ● EXPLICIT
        </span>
      );
    case 'DERIVED_FROM_CLAUSES':
      return (
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: 'rgba(59, 130, 246, 0.12)',
            color: '#2563eb',
            border: '1px solid rgba(59, 130, 246, 0.28)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          ◆ DERIVED
        </span>
      );
    case 'CONFLICTING_EVIDENCE':
      return (
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: 'rgba(225, 29, 72, 0.12)',
            color: '#e11d48',
            border: '1px solid rgba(225, 29, 72, 0.28)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          ≠ DIVERGENT
        </span>
      );
    case 'NO_SUPPORTING_PASSAGE':
    default:
      return (
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: 'var(--canvas-bg)',
            color: 'var(--ink-tertiary)',
            border: '1px dashed var(--divider-line)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          ○ UNADDRESSED
        </span>
      );
  }
}

export default function AdvocatePackPanel({
  advocatePack,
  onNavigateToCitation,
}) {
  if (!advocatePack) {
    return (
      <div style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--ink-tertiary)' }}>
        <p className="font-serif" style={{ fontStyle: 'italic', color: 'var(--ink-secondary)' }}>
          Preparing evidentiary dossier from verified workspace evidence...
        </p>
      </div>
    );
  }

  const {
    document_name,
    total_pages,
    compilation_timestamp,
    executive_summary,
    financial_covenants,
    textual_divergence_schedule,
    coverage_gaps,
    footnotes,
    legal_disclaimer,
  } = advocatePack;

  const handlePrint = () => {
    window.print();
  };

  const findFootnote = (idx) => footnotes.find((f) => f.index === idx);

  const handleCitationClick = (footnoteIndex) => {
    const fn = findFootnote(footnoteIndex);
    if (fn && onNavigateToCitation) {
      onNavigateToCitation({
        page: fn.page_number,
        clauseId: fn.clause_id,
        clauseNumber: fn.clause_number,
        quote: fn.exact_quote,
        boundingBoxes: fn.bounding_boxes || [],
      });
    }
  };

  return (
    <div
      className="advocate-dossier-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        paddingBottom: '40px',
      }}
    >
      {/* Dossier Top Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderBottom: '2px solid var(--accent-legal)',
          paddingBottom: '16px',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: 'var(--accent-legal)',
              marginBottom: '4px',
            }}
          >
            BLIND EYE · Evidentiary Agreement Review Dossier
          </div>
          <h2
            className="font-serif"
            style={{
              fontSize: '22px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            Advocate Preparation Pack
          </h2>
          <div
            style={{
              fontSize: '12px',
              color: 'var(--ink-secondary)',
              marginTop: '4px',
              display: 'flex',
              gap: '16px',
            }}
          >
            <span>
              <strong>Document:</strong> {document_name}
            </span>
            <span>
              <strong>Pages:</strong> {total_pages}
            </span>
            <span>
              <strong>Generated:</strong> {new Date(compilation_timestamp).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Print / Archival Export Action */}
        <button
          onClick={handlePrint}
          className="no-print"
          aria-label="Print or export archival evidentiary agreement review dossier"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            fontSize: '12px',
            fontWeight: 600,
            borderRadius: '4px',
            backgroundColor: 'var(--surface-bg)',
            border: '1px solid var(--divider-line)',
            color: 'var(--ink-primary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--canvas-bg)';
            e.currentTarget.style.borderColor = 'var(--accent-legal)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--surface-bg)';
            e.currentTarget.style.borderColor = 'var(--divider-line)';
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 6 2 18 2 18 9"></polyline>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
            <rect x="6" y="14" width="12" height="8"></rect>
          </svg>
          Print / Export Dossier
        </button>
      </div>

      {/* Mandatory Non-Advice Evidentiary Notice */}
      <div
        style={{
          padding: '12px 16px',
          borderRadius: '4px',
          backgroundColor: 'rgba(180, 83, 9, 0.06)',
          borderLeft: '3px solid var(--accent-legal)',
          fontSize: '11px',
          lineHeight: '1.5',
          color: 'var(--ink-secondary)',
        }}
      >
        <span style={{ fontWeight: 600, color: 'var(--accent-legal)' }}>Evidentiary Notice: </span>
        {legal_disclaimer}
      </div>

      {/* SECTION I: EXECUTIVE SUMMARY */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3
            className="font-serif"
            style={{
              fontSize: '15px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            I. Executive Summary (Verified Terms)
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)' }}>
            Physical provenance anchored directly to verified claims
          </span>
        </div>

        <div
          style={{
            borderRadius: '6px',
            border: '1px solid var(--divider-line)',
            backgroundColor: 'var(--surface-bg)',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr
                style={{
                  backgroundColor: 'var(--canvas-bg)',
                  borderBottom: '1px solid var(--divider-line)',
                  color: 'var(--ink-secondary)',
                  textAlign: 'left',
                }}
              >
                <th style={{ padding: '8px 14px', width: '28%' }}>Core Covenant Field</th>
                <th style={{ padding: '8px 14px', width: '38%' }}>Extracted Term / Value</th>
                <th style={{ padding: '8px 14px', width: '16%' }}>Classification</th>
                <th style={{ padding: '8px 14px', width: '18%' }}>Source Provenance</th>
              </tr>
            </thead>
            <tbody>
              {[
                { key: 'licensor', label: 'Licensor / Landlord', item: executive_summary.parties_licensor },
                { key: 'licensee', label: 'Licensee / Tenant', item: executive_summary.parties_licensee },
                { key: 'property', label: 'Premises Address', item: executive_summary.property_address },
                { key: 'rent', label: 'Monthly License Fee', item: executive_summary.monthly_rent },
                { key: 'deposit', label: 'Security Deposit', item: executive_summary.security_deposit },
                { key: 'tenure', label: 'Agreement Tenure', item: executive_summary.tenure_months },
                { key: 'date', label: 'Execution / Commencement', item: executive_summary.execution_date },
              ].map(({ key, label, item }, idx) => (
                <tr
                  key={key}
                  style={{
                    borderBottom: idx < 6 ? '1px solid var(--divider-line)' : 'none',
                    backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(0, 0, 0, 0.015)',
                  }}
                >
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    {label}
                  </td>
                  <td style={{ padding: '10px 14px', color: item.value ? 'var(--ink-primary)' : 'var(--ink-tertiary)' }}>
                    {item.value ? (
                      <span style={{ fontWeight: 500 }}>{item.value}</span>
                    ) : (
                      <span style={{ fontStyle: 'italic', fontSize: '11px' }}>
                        {item.notes || 'No supporting provision found for this field.'}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {getClassificationBadge(item.classification)}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {item.provenance_indices?.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {item.provenance_indices.map((pIdx) => (
                          <button
                            key={pIdx}
                            onClick={() => handleCitationClick(pIdx)}
                            className="no-print"
                            title={`Jump to footnote [${pIdx}]`}
                            style={{
                              padding: '2px 6px',
                              fontSize: '11px',
                              fontWeight: 600,
                              borderRadius: '3px',
                              backgroundColor: 'rgba(180, 83, 9, 0.08)',
                              color: 'var(--accent-legal)',
                              border: '1px solid rgba(180, 83, 9, 0.25)',
                              cursor: 'pointer',
                            }}
                          >
                            [{pIdx}] ↗
                          </button>
                        ))}
                        <span className="print-only" style={{ fontSize: '10px', color: 'var(--ink-secondary)' }}>
                          {item.source_clauses?.join(', ') || `[${item.provenance_indices.join(', ')}]`}
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--ink-tertiary)', fontSize: '11px' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SECTION II: FINANCIAL COVENANTS MATRIX */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3
            className="font-serif"
            style={{
              fontSize: '15px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            II. Financial Covenants Matrix
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)' }}>
            Explicit covenants & derived financial totals
          </span>
        </div>

        <div
          style={{
            borderRadius: '6px',
            border: '1px solid var(--divider-line)',
            backgroundColor: 'var(--surface-bg)',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr
                style={{
                  backgroundColor: 'var(--canvas-bg)',
                  borderBottom: '1px solid var(--divider-line)',
                  color: 'var(--ink-secondary)',
                  textAlign: 'left',
                }}
              >
                <th style={{ padding: '8px 14px', width: '32%' }}>Covenant Term</th>
                <th style={{ padding: '8px 14px', width: '18%' }}>Obligated Party</th>
                <th style={{ padding: '8px 14px', width: '26%' }}>Amount / Rate</th>
                <th style={{ padding: '8px 14px', width: '14%' }}>Classification</th>
                <th style={{ padding: '8px 14px', width: '10%' }}>Citation</th>
              </tr>
            </thead>
            <tbody>
              {financial_covenants.map((row, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: idx < financial_covenants.length - 1 ? '1px solid var(--divider-line)' : 'none',
                    backgroundColor: row.classification === 'DERIVED_FROM_CLAUSES'
                      ? 'rgba(59, 130, 246, 0.03)'
                      : (idx % 2 === 0 ? 'transparent' : 'rgba(0, 0, 0, 0.015)'),
                  }}
                >
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    {row.term}
                    {row.classification === 'DERIVED_FROM_CLAUSES' && (
                      <div style={{ fontSize: '10px', color: 'var(--ink-tertiary)', fontWeight: 400, marginTop: '2px' }}>
                        Combines explicit deposit & rent claims without introducing absent values.
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--ink-secondary)' }}>
                    {row.actor_responsible}
                  </td>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    {row.amount_or_terms}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {getClassificationBadge(row.classification)}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {row.provenance_indices?.length > 0 ? (
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {row.provenance_indices.map((pIdx) => (
                          <button
                            key={pIdx}
                            onClick={() => handleCitationClick(pIdx)}
                            className="no-print"
                            title={`Jump to footnote [${pIdx}]`}
                            style={{
                              padding: '2px 6px',
                              fontSize: '11px',
                              fontWeight: 600,
                              borderRadius: '3px',
                              backgroundColor: 'rgba(180, 83, 9, 0.08)',
                              color: 'var(--accent-legal)',
                              border: '1px solid rgba(180, 83, 9, 0.25)',
                              cursor: 'pointer',
                            }}
                          >
                            [{pIdx}] ↗
                          </button>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: 'var(--ink-tertiary)', fontSize: '11px' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SECTION III: TEXTUAL DIVERGENCE SCHEDULE */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3
            className="font-serif"
            style={{
              fontSize: '15px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            III. Textual Divergence Schedule
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)' }}>
            Side-by-side textual contradictions across covenant clauses
          </span>
        </div>

        {textual_divergence_schedule.length === 0 ? (
          <div
            style={{
              padding: '16px 20px',
              borderRadius: '6px',
              border: '1px solid var(--divider-line)',
              backgroundColor: 'var(--surface-bg)',
              color: 'var(--ink-secondary)',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <span style={{ color: '#16a34a', fontWeight: 700 }}>✓</span>
            Zero textual contradictions identified across analyzed covenants.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {textual_divergence_schedule.map((item, idx) => (
              <div
                key={idx}
                style={{
                  borderRadius: '6px',
                  border: '1px solid rgba(225, 29, 72, 0.3)',
                  backgroundColor: 'var(--surface-bg)',
                  padding: '16px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(225, 29, 72, 0.1)',
                        color: '#e11d48',
                      }}
                    >
                      {item.subject}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--ink-secondary)' }}>
                      Actor: <strong>{item.actor}</strong>
                    </span>
                  </div>
                  {getClassificationBadge(item.classification)}
                </div>

                {/* Neutral Comparison Statement */}
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 500,
                    color: 'var(--ink-primary)',
                    lineHeight: '1.5',
                  }}
                >
                  {item.neutral_comparison_statement}
                </div>

                {/* Bilateral Evidence Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px',
                    marginTop: '4px',
                  }}
                >
                  {/* Source A */}
                  <div
                    style={{
                      padding: '10px 12px',
                      borderRadius: '4px',
                      backgroundColor: 'var(--canvas-bg)',
                      border: '1px solid var(--divider-line)',
                      fontSize: '11px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <strong style={{ color: 'var(--ink-primary)' }}>
                        Source A: {item.source_a_clause || `Page ${item.source_a_page}`}
                      </strong>
                      {item.source_a_provenance_index && (
                        <button
                          onClick={() => handleCitationClick(item.source_a_provenance_index)}
                          className="no-print"
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '1px 6px',
                            borderRadius: '3px',
                            backgroundColor: 'rgba(180, 83, 9, 0.08)',
                            color: 'var(--accent-legal)',
                            border: '1px solid rgba(180, 83, 9, 0.25)',
                            cursor: 'pointer',
                          }}
                        >
                          View Source A ↗
                        </button>
                      )}
                    </div>
                    <div style={{ fontStyle: 'italic', color: 'var(--ink-secondary)', lineHeight: '1.4' }}>
                      "{item.source_a_quote}"
                    </div>
                  </div>

                  {/* Source B */}
                  <div
                    style={{
                      padding: '10px 12px',
                      borderRadius: '4px',
                      backgroundColor: 'var(--canvas-bg)',
                      border: '1px solid var(--divider-line)',
                      fontSize: '11px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <strong style={{ color: 'var(--ink-primary)' }}>
                        Source B: {item.source_b_clause || `Page ${item.source_b_page}`}
                      </strong>
                      {item.source_b_provenance_index && (
                        <button
                          onClick={() => handleCitationClick(item.source_b_provenance_index)}
                          className="no-print"
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '1px 6px',
                            borderRadius: '3px',
                            backgroundColor: 'rgba(180, 83, 9, 0.08)',
                            color: 'var(--accent-legal)',
                            border: '1px solid rgba(180, 83, 9, 0.25)',
                            cursor: 'pointer',
                          }}
                        >
                          View Source B ↗
                        </button>
                      )}
                    </div>
                    <div style={{ fontStyle: 'italic', color: 'var(--ink-secondary)', lineHeight: '1.4' }}>
                      "{item.source_b_quote}"
                    </div>
                  </div>
                </div>

                {/* Non-adjudicating disclaimer */}
                <div style={{ fontSize: '10px', color: 'var(--ink-tertiary)', fontStyle: 'italic' }}>
                  * Identifies physical textual divergence only. Does not adjudicate legal enforceability or determine controlling clause.
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECTION IV: DOCUMENT COVERAGE & CLARIFICATION GAPS */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3
            className="font-serif"
            style={{
              fontSize: '15px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            IV. Document Coverage & Clarification Gaps
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)' }}>
            Requested covenants checked without supporting text
          </span>
        </div>

        <div
          style={{
            borderRadius: '6px',
            border: '1px solid var(--divider-line)',
            backgroundColor: 'var(--surface-bg)',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr
                style={{
                  backgroundColor: 'var(--canvas-bg)',
                  borderBottom: '1px solid var(--divider-line)',
                  color: 'var(--ink-secondary)',
                  textAlign: 'left',
                }}
              >
                <th style={{ padding: '8px 14px', width: '30%' }}>Covenant Checked</th>
                <th style={{ padding: '8px 14px', width: '40%' }}>Search Boundary / Scope</th>
                <th style={{ padding: '8px 14px', width: '14%' }}>Status</th>
                <th style={{ padding: '8px 14px', width: '16%' }}>Evidentiary Finding</th>
              </tr>
            </thead>
            <tbody>
              {coverage_gaps.map((gap, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: idx < coverage_gaps.length - 1 ? '1px solid var(--divider-line)' : 'none',
                    backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(0, 0, 0, 0.015)',
                  }}
                >
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    {gap.field_name}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--ink-secondary)' }}>
                    {gap.checked_scope}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {getClassificationBadge(gap.classification)}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--ink-tertiary)', fontStyle: 'italic', fontSize: '11px' }}>
                    {gap.coverage_note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SECTION V: PROVENANCE FOOTNOTE INDEX */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3
            className="font-serif"
            style={{
              fontSize: '15px',
              fontWeight: 700,
              margin: 0,
              color: 'var(--ink-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            V. Physical Provenance Footnote Index
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)' }}>
            Sequential verbatim citations anchored to physical document coordinates
          </span>
        </div>

        <div
          style={{
            borderRadius: '6px',
            border: '1px solid var(--divider-line)',
            backgroundColor: 'var(--surface-bg)',
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          {footnotes.map((fn) => (
            <div
              key={fn.index}
              style={{
                fontSize: '11px',
                lineHeight: '1.5',
                display: 'flex',
                gap: '8px',
                alignItems: 'baseline',
              }}
            >
              <strong style={{ color: 'var(--accent-legal)', minWidth: '24px' }}>[{fn.index}]</strong>
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 600, color: 'var(--ink-primary)' }}>
                  {fn.clause_number ? `${fn.clause_number} • ` : ''}Page {fn.page_number}:
                </span>{' '}
                <span style={{ fontStyle: 'italic', color: 'var(--ink-secondary)' }}>
                  "{fn.exact_quote}"
                </span>{' '}
                <button
                  onClick={() => handleCitationClick(fn.index)}
                  className="no-print"
                  aria-label={`Locate footnote [${fn.index}] on page ${fn.page_number} in document`}
                  style={{
                    border: 'none',
                    background: 'none',
                    color: 'var(--accent-legal)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '11px',
                    padding: '2px 4px',
                    textDecoration: 'underline',
                  }}
                >
                  locate in document ↗
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
