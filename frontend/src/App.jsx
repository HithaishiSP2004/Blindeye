import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import IntakeArea from './components/IntakeArea';
import DocumentSurface from './components/DocumentSurface';
import EvidencePanel from './components/EvidencePanel';
import { extractDocument, verifyDocument, detectContradictions } from './api/client';

export default function App() {
  const [theme, setTheme] = useState('light');
  const [currentFile, setCurrentFile] = useState(null);
  const [documentData, setDocumentData] = useState(null);
  const [structuredAgreement, setStructuredAgreement] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [contradictionData, setContradictionData] = useState(null);
  const [selectedContradictionSource, setSelectedContradictionSource] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeClauseId, setActiveClauseId] = useState(null);
  const [hoveredClauseId, setHoveredClauseId] = useState(null);
  const [activeFactField, setActiveFactField] = useState(null);
  const [hoveredFactField, setHoveredFactField] = useState(null);

  // Synchronize data-theme on root HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Load Golden Agreement fixture by default on initial mount for immediate demonstration
  useEffect(() => {
    handleLoadGoldenAgreement();
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const handleParseFile = async (file) => {
    setLoading(true);
    setError(null);
    setCurrentFile(file);
    try {
      // Execute extraction (DocumentTree), Verification Gate (Phase 4), and Contradiction Engine (Phase 6) in parallel
      const [extractResult, verifyResult, contradictionResult] = await Promise.all([
        extractDocument(file),
        verifyDocument(file),
        detectContradictions(file).catch((cErr) => {
          console.warn('Contradiction analysis note:', cErr);
          return null;
        }),
      ]);

      setDocumentData(extractResult.document_tree);
      setStructuredAgreement(extractResult.structured_agreement);
      setVerificationResult(verifyResult);
      setContradictionData(contradictionResult);
      setSelectedContradictionSource(null);

      setActiveClauseId(null);
      setHoveredClauseId(null);
      setActiveFactField(null);
      setHoveredFactField(null);
    } catch (err) {
      setError(err.message || 'Failed to verify legal agreement.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectContradictionSource = (source) => {
    if (!source) {
      setSelectedContradictionSource(null);
      return;
    }
    setSelectedContradictionSource(source);
    if (source.clause_id) {
      setActiveClauseId(source.clause_id);
    }
    setActiveFactField(null);
    if (source.page_number) {
      const pageEl = document.getElementById(`pdf-page-${source.page_number}`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };


  const handleLoadGoldenAgreement = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/golden_agreement.pdf');
      if (!res.ok) {
        throw new Error('Golden fixture PDF not found in static assets.');
      }
      const blob = await res.blob();
      const file = new File([blob], 'golden_agreement.pdf', { type: 'application/pdf' });
      await handleParseFile(file);
    } catch (err) {
      setError(err.message || 'Failed to load golden agreement.');
      setLoading(false);
    }
  };

  const handleSelectFact = (fieldKey, item) => {
    if (activeFactField === fieldKey) {
      setActiveFactField(null);
      setActiveClauseId(null);
    } else {
      setActiveFactField(fieldKey);
      const clauseId =
        item?.source?.clause_id ||
        item?.source_clause_id ||
        (item?.supporting_clause_ids && item.supporting_clause_ids[0]);
      if (clauseId) {
        setActiveClauseId(clauseId);
      }
    }
  };

  const handleHoverFact = (fieldKey) => {
    setHoveredFactField(fieldKey);
    if (!fieldKey) {
      setHoveredClauseId(null);
      return;
    }

    const fact = structuredAgreement?.[fieldKey];
    const claim = verificationResult?.claims?.find((c) => c.field_name === fieldKey);
    const clauseId =
      claim?.source?.clause_id ||
      fact?.source_clause_id ||
      (claim?.supporting_clause_ids && claim.supporting_clause_ids[0]);

    if (clauseId) {
      setHoveredClauseId(clauseId);
    } else {
      setHoveredClauseId(null);
    }
  };

  const handleSelectClause = (clauseId) => {
    setActiveClauseId(activeClauseId === clauseId ? null : clauseId);

    // If a fact or claim corresponds to this clause, highlight it
    if (clauseId) {
      // Check in claims first
      if (verificationResult?.claims) {
        const matchingClaim = verificationResult.claims.find(
          (c) =>
            c.source?.clause_id === clauseId ||
            (c.supporting_clause_ids && c.supporting_clause_ids.includes(clauseId))
        );
        if (matchingClaim) {
          setActiveFactField(matchingClaim.field_name);
          return;
        }
      }

      // Check in structured agreement
      if (structuredAgreement) {
        const matchingField = Object.entries(structuredAgreement).find(
          ([k, v]) => v && v.source_clause_id === clauseId
        );
        if (matchingField) {
          setActiveFactField(matchingField[0]);
        }
      }
    }
  };

  const handleNavigateToCitation = (citation) => {
    if (!citation) return;
    if (citation.clause_id) {
      setActiveClauseId(citation.clause_id);
    }
    setActiveFactField(null);
    if (citation.page) {
      const pageEl = document.getElementById(`pdf-page-${citation.page}`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: 'var(--canvas-bg)',
      }}
    >
      {/* Editorial Header */}
      <Header
        theme={theme}
        onToggleTheme={toggleTheme}
        documentInfo={
          documentData
            ? { filename: documentData.filename, page_count: documentData.page_count }
            : null
        }
      />

      {/* Document Intake Desk */}
      <IntakeArea
        onParseFile={handleParseFile}
        onLoadGolden={handleLoadGoldenAgreement}
        loading={loading}
        error={error}
      />

      {/* Main Editorial Workspace: 58% Document Surface / 42% Evidence Panel */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          minHeight: 'calc(100vh - 170px)',
          flexDirection: 'row',
        }}
      >
        {/* Left Column: Physical Document Canvas (The Hero) */}
        <div
          style={{
            flex: '0 0 58%',
            maxWidth: '58%',
            borderRight: '1px solid var(--divider-line)',
            overflowY: 'auto',
            backgroundColor: 'var(--canvas-bg)',
          }}
        >
          <DocumentSurface
            documentData={documentData}
            structuredAgreement={structuredAgreement}
            verificationResult={verificationResult}
            activeClauseId={activeClauseId}
            hoveredClauseId={hoveredClauseId}
            activeFactField={activeFactField}
            hoveredFactField={hoveredFactField}
            onHoverClause={setHoveredClauseId}
            onSelectClause={handleSelectClause}
            onSelectFact={handleSelectFact}
            selectedContradictionSource={selectedContradictionSource}
          />
        </div>

        {/* Right Column: Structured Evidence & Provenance Hierarchy */}
        <div
          style={{
            flex: '0 0 42%',
            maxWidth: '42%',
            backgroundColor: 'var(--surface-bg)',
            overflowY: 'auto',
          }}
        >
          <EvidencePanel
            documentData={documentData}
            structuredAgreement={structuredAgreement}
            verificationResult={verificationResult}
            activeClauseId={activeClauseId}
            hoveredClauseId={hoveredClauseId}
            activeFactField={activeFactField}
            hoveredFactField={hoveredFactField}
            onHoverClause={setHoveredClauseId}
            onSelectClause={handleSelectClause}
            onSelectFact={handleSelectFact}
            onHoverFact={handleHoverFact}
            rawFile={currentFile}
            onNavigateToCitation={handleNavigateToCitation}
            contradictionData={contradictionData}
            selectedContradictionSource={selectedContradictionSource}
            onSelectContradictionSource={handleSelectContradictionSource}
          />
        </div>
      </div>

    </div>
  );
}
