import React, { useEffect, useRef } from 'react';
import EvidenceMarker from './EvidenceMarker';

const FIELD_LABELS = {
  agreement_type: 'Agreement Type',
  execution_date: 'Execution Date',
  landlord_name: 'Licensor',
  tenant_name: 'Licensee',
  property_address: 'Property Address',
  tenure_months: 'Tenure',
  commencement_date: 'Commencement',
  lock_in_months: 'Lock-in',
  monthly_rent: 'Monthly Rent',
  security_deposit: 'Security Deposit',
  deposit_refund_days: 'Deposit Refund',
  notice_period_days: 'Notice Period',
  maintenance_responsibility: 'Maintenance',
  late_payment_penalty: 'Penalty',
  permitted_use: 'Permitted Use',
  renewal_terms: 'Renewal Terms',
};

export default function DocumentSurface({
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
  selectedContradictionSource,
}) {
  const containerRef = useRef(null);

  // Automatic Smooth Navigation to Source on Fact Selection (Section 14)
  useEffect(() => {
    if (!activeFactField || !documentData) return;

    // Find the claim or fact
    let targetPage = null;
    if (verificationResult?.claims) {
      const claim = verificationResult.claims.find((c) => c.field_name === activeFactField);
      if (claim?.source?.page) {
        targetPage = claim.source.page;
      } else if (claim?.bounding_boxes?.[0]?.page) {
        targetPage = claim.bounding_boxes[0].page;
      }
    }

    if (!targetPage && structuredAgreement?.[activeFactField]) {
      const fact = structuredAgreement[activeFactField];
      targetPage = fact.page || fact.bbox?.page || null;
    }

    if (targetPage) {
      const pageEl = document.getElementById(`pdf-page-${targetPage}`);
      const scrollContainer = containerRef.current;
      if (pageEl && scrollContainer) {
        const containerRect = scrollContainer.getBoundingClientRect();
        const elRect = pageEl.getBoundingClientRect();
        // Only scroll if page is not comfortably in view
        const isComfortablyVisible =
          elRect.top >= containerRect.top - 50 && elRect.bottom <= containerRect.bottom + 50;
        if (!isComfortablyVisible) {
          pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }
  }, [activeFactField, documentData, verificationResult, structuredAgreement]);

  if (!documentData) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '80px 24px',
          color: 'var(--ink-tertiary)',
          textAlign: 'center',
        }}
      >
        <div
          className="paper-sheet"
          style={{
            width: '260px',
            height: '340px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '24px',
            marginBottom: '24px',
            opacity: 0.65,
          }}
        >
          <div
            style={{
              width: '40px',
              height: '4px',
              backgroundColor: 'var(--divider-line)',
              marginBottom: '16px',
            }}
          />
          <span
            className="font-serif"
            style={{
              fontSize: '15px',
              color: 'var(--ink-secondary)',
              fontStyle: 'italic',
            }}
          >
            Awaiting Legal Agreement
          </span>
          <span style={{ fontSize: '11px', color: 'var(--ink-tertiary)', marginTop: '8px' }}>
            Submit a residential PDF above to inspect physical evidence
          </span>
        </div>
      </div>
    );
  }

  // Map block_id -> Clause for instantaneous lookup
  const blockToClauseMap = {};
  documentData.clauses.forEach((clause) => {
    clause.source_block_ids.forEach((bId) => {
      blockToClauseMap[bId] = clause;
    });
  });

  const hasSelection = Boolean(activeClauseId || hoveredClauseId || activeFactField || hoveredFactField);

  // Extract all verified fact bounding boxes per page from verificationResult (preferred) or structuredAgreement
  const pageFactMarkers = {};

  if (verificationResult?.claims && verificationResult.claims.length > 0) {
    verificationResult.claims.forEach((claim) => {
      const addedKeysForPage = new Set();

      // Collect primary source bbox
      const primaryBbox = claim.source?.bbox;
      if (primaryBbox && primaryBbox.page) {
        const pNum = primaryBbox.page;
        if (!pageFactMarkers[pNum]) pageFactMarkers[pNum] = [];
        pageFactMarkers[pNum].push({
          key: claim.field_name,
          fact: claim,
          bbox: primaryBbox,
        });
        addedKeysForPage.add(`${claim.field_name}_p${pNum}`);
      }

      // Collect any additional bounding boxes (e.g. multi-page maintenance)
      if (claim.bounding_boxes && claim.bounding_boxes.length > 0) {
        claim.bounding_boxes.forEach((bb) => {
          if (bb && bb.page && !addedKeysForPage.has(`${claim.field_name}_p${bb.page}`)) {
            const pNum = bb.page;
            if (!pageFactMarkers[pNum]) pageFactMarkers[pNum] = [];
            pageFactMarkers[pNum].push({
              key: claim.field_name,
              fact: claim,
              bbox: bb,
            });
            addedKeysForPage.add(`${claim.field_name}_p${pNum}`);
          }
        });
      }
    });
  } else if (structuredAgreement) {
    Object.entries(structuredAgreement).forEach(([key, fact]) => {
      if (fact && fact.bbox && fact.bbox.page) {
        const pNum = fact.bbox.page;
        if (!pageFactMarkers[pNum]) pageFactMarkers[pNum] = [];
        pageFactMarkers[pNum].push({
          key,
          fact,
          bbox: fact.bbox,
        });
      }
    });
  }

  return (
    <div
      ref={containerRef}
      className={`document-surface ${hasSelection ? 'has-active-selection' : ''}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '36px',
        padding: '24px 28px',
        alignItems: 'center',
        overflowY: 'auto',
        height: '100%',
      }}
    >
      {documentData.pages.map((page) => {
        const markersForPage = pageFactMarkers[page.page_number] || [];
        const pageWidth = page.width || 595.0;
        const pageHeight = page.height || 842.0;

        return (
          <div
            key={`page_container_${page.page_number}`}
            id={`page-container-${page.page_number}`}
            style={{
              display: 'flex',
              flexDirection: 'column',
              width: '100%',
              maxWidth: '680px',
            }}
          >
            {/* Top Page Header (Positioned outside the coordinate canvas to preserve origin) */}
            <div
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                marginBottom: '8px',
                fontSize: '10px',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: 'var(--ink-tertiary)',
              }}
            >
              <span>Physical Document Surface</span>
              <span className="font-mono">
                Page {page.page_number} of {documentData.page_count}
              </span>
            </div>

            {/* Exact PDF Page Sheet: Physical Coordinate Canvas */}
            <div
              id={`pdf-page-${page.page_number}`}
              className="paper-sheet"
              style={{
                width: '100%',
                aspectRatio: `${pageWidth} / ${pageHeight}`,
                position: 'relative',
                overflow: 'hidden',
                backgroundColor: 'var(--sheet-bg)',
              }}
            >
              {/* Layer 1: Physical Typography Blocks (Placed strictly via PyMuPDF BoundingBoxes) */}
              {page.blocks.map((block) => {
                const matchedClause = blockToClauseMap[block.block_id];
                const isClauseHovered = matchedClause && hoveredClauseId === matchedClause.clause_id;
                const isClauseSelected = matchedClause && activeClauseId === matchedClause.clause_id;

                const leftPct = (block.bbox.x0 / pageWidth) * 100;
                const topPct = (block.bbox.y0 / pageHeight) * 100;
                const widthPct = ((block.bbox.x1 - block.bbox.x0) / pageWidth) * 100;
                const minHeightPct = ((block.bbox.y1 - block.bbox.y0) / pageHeight) * 100;

                const ptSize = block.spans?.[0]?.font_size || 10;
                const isBold = block.spans?.[0]?.font_name?.toLowerCase().includes('bold') || ptSize > 12;

                return (
                  <div
                    key={block.block_id}
                    id={`block-${block.block_id}`}
                    onClick={() => matchedClause && onSelectClause(matchedClause.clause_id)}
                    onMouseEnter={() => matchedClause && onHoverClause(matchedClause.clause_id)}
                    onMouseLeave={() => onHoverClause(null)}
                    className={`clause-block-highlight ${isClauseHovered ? 'is-hovered' : ''} ${
                      isClauseSelected ? 'is-selected' : ''
                    }`}
                    style={{
                      position: 'absolute',
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: `${widthPct}%`,
                      minHeight: `${minHeightPct}%`,
                      pointerEvents: 'auto',
                      cursor: matchedClause ? 'pointer' : 'default',
                      zIndex: 2,
                    }}
                  >
                    {/* Verbatim Document Typography */}
                    <div
                      className="font-serif"
                      style={{
                        fontSize: `calc(${ptSize} * 100cqw / ${pageWidth})`,
                        lineHeight: 1.34,
                        fontWeight: isBold ? 700 : 400,
                        color: 'var(--ink-primary)',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {block.text}
                    </div>
                  </div>
                );
              })}

              {/* Layer 2: Geometric Evidence Overlay Layer (Strictly PyMuPDF BoundingBoxes) */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  pointerEvents: 'none',
                  zIndex: 10,
                }}
              >
                {markersForPage.map(({ key, fact, bbox }, idx) => (
                  <EvidenceMarker
                    key={`marker_${key}_p${page.page_number}_${idx}`}
                    bbox={bbox}
                    pageWidth={pageWidth}
                    pageHeight={pageHeight}
                    label={FIELD_LABELS[key] || key}
                    value={fact.value || ''}
                    isActive={activeFactField === key}
                    isHovered={hoveredFactField === key}
                    onClick={() => onSelectFact(key, fact)}
                  />
                ))}

                {/* Comparative Evidence Source Box (Bilateral Dual Physical Provenance) */}
                {selectedContradictionSource?.bbox && selectedContradictionSource.bbox.page === page.page_number && (
                  <div
                    style={{
                      position: 'absolute',
                      left: `${(selectedContradictionSource.bbox.x0 / pageWidth) * 100}%`,
                      top: `${(selectedContradictionSource.bbox.y0 / pageHeight) * 100}%`,
                      width: `${Math.max(1, ((selectedContradictionSource.bbox.x1 - selectedContradictionSource.bbox.x0) / pageWidth) * 100)}%`,
                      height: `${Math.max(1.2, ((selectedContradictionSource.bbox.y1 - selectedContradictionSource.bbox.y0) / pageHeight) * 100)}%`,
                      border: '1.5px solid var(--accent-legal)',
                      backgroundColor: 'var(--accent-soft)',
                      borderRadius: '2px',
                      pointerEvents: 'none',
                      boxShadow: '0 0 10px var(--accent-glow)',
                      zIndex: 25,
                      transition: 'all 140ms ease',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 'calc(100% + 3px)',
                        left: 0,
                        backgroundColor: 'var(--accent-legal)',
                        color: '#FFFFFF',
                        fontSize: '9px',
                        fontWeight: 600,
                        letterSpacing: '0.04em',
                        padding: '2px 7px',
                        borderRadius: '2px',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.25)',
                        zIndex: 30,
                      }}
                    >
                      <span style={{ fontSize: '9px' }}>⇄</span>
                      <span>Comparative Source: Clause {selectedContradictionSource.clause_number || ''}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
