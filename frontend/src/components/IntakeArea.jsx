import React, { useState } from 'react';

export default function IntakeArea({ onParseFile, onLoadGolden, onLoadConflicting, onLoadAdversarial, loading, loadingStage, error }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        onParseFile(file);
      }
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      onParseFile(e.target.files[0]);
    }
  };

  return (
    <div
      className="intake-desk-container"
      style={{
        borderBottom: '1px solid var(--divider-line)',
        backgroundColor: 'var(--surface-bg)',
        padding: '22px 28px',
        transition: 'background-color 0.25s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        {/* Intake Title & Instructions */}
        <div>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: 'var(--accent-legal)',
              display: 'block',
              marginBottom: '3px',
            }}
          >
            BLIND EYE · RESIDENTIAL AGREEMENT INTELLIGENCE
          </span>
          <h2
            className="font-serif"
            style={{
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--ink-primary)',
              lineHeight: 1.25,
              margin: 0,
            }}
          >
            Bring the agreement. We will show you exactly what it says.
          </h2>
          <p
            style={{
              fontSize: '11.5px',
              color: 'var(--ink-secondary)',
              marginTop: '4px',
              margin: '4px 0 0 0',
            }}
          >
            PDF only · Physical line geometry, clause boundaries, and multi-page evidence preservation.
          </p>
        </div>

        {/* Dropzone & Quick-Load Buttons */}
        <div
          className="intake-buttons-group"
          style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}
        >
          {/* Physical Drop Target & Accessible File Upload */}
          <label
            role="button"
            tabIndex={0}
            aria-label="Upload PDF Agreement, maximum 15 megabytes"
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                document.getElementById('hidden-pdf-upload')?.click();
              }
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 18px',
              backgroundColor: isDragOver ? 'var(--accent-soft)' : 'var(--sheet-bg)',
              border: `1px ${isDragOver ? 'dashed var(--accent-legal)' : 'solid var(--accent-legal)'}`,
              borderRadius: '3px',
              cursor: 'pointer',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
              transition: 'all 0.18s ease',
            }}
          >
            <input
              id="hidden-pdf-upload"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileInput}
              style={{ display: 'none' }}
              disabled={loading}
              aria-label="Upload Agreement PDF File"
            />
            <span
              style={{
                fontSize: '13px',
                color: 'var(--accent-legal)',
                fontWeight: 600,
              }}
            >
              {loading ? 'Ingesting Agreement...' : 'Upload Agreement (PDF)'}
            </span>
            <span
              style={{
                fontSize: '10px',
                letterSpacing: '0.04em',
                color: 'var(--ink-tertiary)',
                borderLeft: '1px solid var(--divider-line)',
                paddingLeft: '8px',
              }}
            >
              Max 15 MB
            </span>
          </label>

          {/* Stepped Observable Loading Stage with accessible status region */}
          {loadingStage && (
            <div
              role="status"
              aria-live="polite"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: '3px',
                backgroundColor: 'var(--sheet-bg)',
                border: '1px solid var(--accent-border)',
                boxShadow: 'var(--panel-shadow)',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--accent-legal)',
                }}
              />
              <span
                className="font-mono"
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  color: 'var(--accent-legal)',
                  textTransform: 'uppercase',
                }}
              >
                {loadingStage}
              </span>
            </div>
          )}

          {/* Quick-Load Golden Fixture Button */}
          <button
            onClick={onLoadGolden}
            disabled={loading}
            aria-label="Load Golden Agreement: Bangalore 11-month residential lease fixture"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              backgroundColor: 'var(--sheet-bg)',
              border: '1px solid var(--divider-line)',
              borderRadius: '2px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--ink-primary)',
              boxShadow: 'var(--panel-shadow)',
              opacity: loading ? 0.6 : 1,
              cursor: 'pointer',
            }}
          >
            <span>Load Golden Agreement (Bangalore 11-mo)</span>
            <span style={{ color: 'var(--accent-legal)', fontSize: '11px' }}>→</span>
          </button>

          {/* Quick-Load Divergent Agreement Button */}
          {onLoadConflicting && (
            <button
              onClick={onLoadConflicting}
              disabled={loading}
              aria-label="Load Divergent Covenants: conflicting contractual terms fixture"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                backgroundColor: 'var(--sheet-bg)',
                border: '1px solid var(--divider-line)',
                borderRadius: '2px',
                fontSize: '12px',
                fontWeight: 500,
                color: 'var(--ink-primary)',
                boxShadow: 'var(--panel-shadow)',
                opacity: loading ? 0.6 : 1,
                cursor: 'pointer',
              }}
            >
              <span>Load Divergent Covenants (Conflicting Terms)</span>
              <span style={{ color: 'var(--accent-legal)', fontSize: '11px' }}>≠</span>
            </button>
          )}

          {/* Quick-Load Adversarial Injection Agreement Button */}
          {onLoadAdversarial && (
            <button
              onClick={onLoadAdversarial}
              disabled={loading}
              aria-label="Load Adversarial Injection Fixture: prompt injection evaluation fixture"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                backgroundColor: 'var(--sheet-bg)',
                border: '1px solid rgba(225, 29, 72, 0.3)',
                borderRadius: '2px',
                fontSize: '12px',
                fontWeight: 500,
                color: 'var(--ink-primary)',
                boxShadow: 'var(--panel-shadow)',
                opacity: loading ? 0.6 : 1,
                cursor: 'pointer',
              }}
            >
              <span>Load Adversarial Injection Fixture</span>
              <span style={{ color: '#e11d48', fontSize: '11px', fontWeight: 700 }}>🛡️</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            marginTop: '16px',
            padding: '10px 14px',
            borderRadius: '2px',
            backgroundColor: 'var(--status-alert-bg)',
            borderLeft: '3px solid var(--status-alert)',
            fontSize: '12px',
            color: 'var(--status-alert)',
          }}
        >
          <strong>Ingestion Rejected:</strong> {error}
        </div>
      )}
    </div>
  );
}
