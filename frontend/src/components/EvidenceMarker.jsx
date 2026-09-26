import React from 'react';

/**
 * Geometric visual evidence overlay marker positioned strictly via PyMuPDF BoundingBoxes.
 * Adheres strictly to the Page-Local Coordinate Contract:
 * - Coordinates are interpreted relative to the individual PDF page (0 to 100%).
 * - Unselected markers remain quiet/subtle to eliminate visual ambiguity with structural text spans.
 * - Active selected markers receive prominent, restrained amber evidence illumination with an anchored badge.
 */
export default function EvidenceMarker({
  bbox,
  pageWidth,
  pageHeight,
  label,
  value,
  isActive,
  isHovered,
  onClick,
}) {
  if (!bbox || !pageWidth || !pageHeight) return null;

  // Convert PDF points to exact percentage of individual PDF page dimensions
  const leftPct = (bbox.x0 / pageWidth) * 100;
  const topPct = (bbox.y0 / pageHeight) * 100;
  const widthPct = Math.max(1, ((bbox.x1 - bbox.x0) / pageWidth) * 100);
  const heightPct = Math.max(1.2, ((bbox.y1 - bbox.y0) / pageHeight) * 100);

  const isHighlighted = isActive || isHovered;

  // Anchor label badge above marker, or below if marker is near the very top of the page
  const anchorBelow = topPct < 6;

  return (
    <div
      onClick={onClick}
      style={{
        position: 'absolute',
        left: `${leftPct}%`,
        top: `${topPct}%`,
        width: `${widthPct}%`,
        height: `${heightPct}%`,
        // Strict distinction between verified evidence and document structure (Section 12)
        backgroundColor: isActive
          ? 'rgba(184, 134, 11, 0.22)'
          : isHovered
          ? 'rgba(184, 134, 11, 0.12)'
          : 'transparent',
        border: isActive
          ? '1.5px solid var(--accent-legal)'
          : isHovered
          ? '1px solid var(--accent-legal)'
          : 'none',
        borderRadius: '2px',
        pointerEvents: 'auto',
        cursor: 'pointer',
        transition: 'all 140ms ease',
        zIndex: isActive ? 25 : isHovered ? 20 : 5,
        boxShadow: isActive ? '0 0 10px rgba(184, 134, 11, 0.35)' : 'none',
      }}
      title={`${label}: ${value}`}
    >
      {/* Floating editorial pill on hover or selection (Section 13: strictly anchored) */}
      {isHighlighted && (
        <div
          style={{
            position: 'absolute',
            ...(anchorBelow
              ? { top: 'calc(100% + 3px)', left: '0' }
              : { bottom: 'calc(100% + 3px)', left: '0' }),
            backgroundColor: 'var(--accent-legal)',
            color: '#FFFFFF',
            fontSize: '9px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            padding: '2px 7px',
            borderRadius: '2px',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.25)',
            zIndex: 30,
            pointerEvents: 'none',
          }}
        >
          <span style={{ fontSize: '8px' }}>⌖</span>
          <span>{label}</span>
        </div>
      )}
    </div>
  );
}
