import React, { useState } from 'react';

export default function IntakeArea({ onParseFile, onLoadGolden, loading, error }) {
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
      style={{
        borderBottom: '1px solid var(--divider-line)',
        backgroundColor: 'var(--surface-bg)',
        padding: '24px 28px',
        transition: 'background-color 0.25s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '20px',
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
              marginBottom: '4px',
            }}
          >
            Document Intake Desk
          </span>
          <h2
            className="font-serif"
            style={{
              fontSize: '18px',
              fontWeight: 500,
              color: 'var(--ink-primary)',
              lineHeight: 1.2,
            }}
          >
            Submit an Indian Residential Rent or Leave-and-Licence Agreement
          </h2>
          <p
            style={{
              fontSize: '12px',
              color: 'var(--ink-secondary)',
              marginTop: '4px',
            }}
          >
            Preserves physical line geometry, clause boundaries, and multi-page continuity.
          </p>
        </div>

        {/* Dropzone & Quick-Load Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Physical Drop Target */}
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 18px',
              backgroundColor: isDragOver ? 'var(--accent-soft)' : 'var(--sheet-bg)',
              border: `1px ${isDragOver ? 'dashed var(--accent-legal)' : 'solid var(--divider-line)'}`,
              borderRadius: '2px',
              cursor: 'pointer',
              boxShadow: 'var(--panel-shadow)',
              transition: 'all 0.18s ease',
            }}
          >
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileInput}
              style={{ display: 'none' }}
              disabled={loading}
            />
            <span
              style={{
                fontSize: '13px',
                color: isDragOver ? 'var(--accent-legal)' : 'var(--ink-primary)',
                fontWeight: 500,
              }}
            >
              {loading ? 'Ingesting PDF...' : 'Drop PDF or Choose File'}
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
              PDF · Max 15 MB
            </span>
          </label>

          {/* Quick-Load Golden Fixture Button */}
          <button
            onClick={onLoadGolden}
            disabled={loading}
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
            }}
          >
            <span>Load Golden Agreement (Bangalore 11-mo)</span>
            <span style={{ color: 'var(--accent-legal)', fontSize: '11px' }}>→</span>
          </button>
        </div>
      </div>

      {error && (
        <div
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
