import React from 'react';

export default function Header({ theme, onToggleTheme, documentInfo }) {
  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 28px',
        borderBottom: '1px solid var(--divider-line)',
        backgroundColor: 'var(--canvas-bg)',
        transition: 'border-color 0.25s ease',
      }}
    >
      {/* Product Identity */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '14px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
          <span
            className="font-serif"
            style={{
              fontSize: '18px',
              fontWeight: 600,
              letterSpacing: '0.04em',
              color: 'var(--ink-primary)',
            }}
          >
            EVIDENCE FIRST
          </span>
        </div>
        <span
          style={{
            fontSize: '10px',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--ink-tertiary)',
            fontWeight: 500,
            borderLeft: '1px solid var(--divider-line)',
            paddingLeft: '12px',
          }}
        >
          Residential Agreement Intelligence
        </span>
      </div>

      {/* Right Controls: Document Status + Theme Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {documentInfo && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '11px',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              color: 'var(--ink-secondary)',
              background: 'var(--surface-bg)',
              padding: '4px 10px',
              borderRadius: '2px',
              border: '1px solid var(--divider-line)',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--status-available)',
                display: 'inline-block',
              }}
            />
            <span>
              {documentInfo.filename} · {documentInfo.page_count} Pages
            </span>
          </div>
        )}

        {/* Theme Switcher Button */}
        <button
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--ink-secondary)',
            padding: '5px 12px',
            borderRadius: '2px',
            border: '1px solid var(--divider-line)',
            backgroundColor: 'var(--surface-bg)',
          }}
        >
          <span>{theme === 'light' ? '● Dark Room' : '○ Light Paper'}</span>
        </button>
      </div>
    </header>
  );
}
