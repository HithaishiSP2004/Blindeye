"""Pydantic data models for Advocate Preparation Pack & Evidentiary Agreement Review Dossier.

Strictly non-evaluative:
- Zero legal enforceability claims.
- Zero statutory context or general legal advice.
- Strict 4-tier evidence taxonomy.
- Dual physical provenance back to DocumentTree.
- Deterministic compilation without unsupported factual values.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.document import BoundingBox


class EvidenceClassification(str, Enum):
    """Strictly factual 4-tier evidentiary classification.

    No GENERAL_LEGAL_INFO or statutory opinions.
    """

    EXPLICIT_IN_DOCUMENT = "EXPLICIT_IN_DOCUMENT"
    DERIVED_FROM_CLAUSES = "DERIVED_FROM_CLAUSES"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    NO_SUPPORTING_PASSAGE = "NO_SUPPORTING_PASSAGE"


class ProvenanceFootnote(BaseModel):
    """Indexable physical provenance footnote referencing exact document geometry."""

    index: int = Field(..., ge=1, description="Sequential 1-based footnote identifier")
    clause_id: Optional[str] = Field(default=None, description="Anchored clause ID")
    clause_number: Optional[str] = Field(default=None, description="Human-readable clause number e.g. 'Clause 4'")
    page_number: int = Field(..., ge=1, description="Physical page number (1-based)")
    exact_quote: str = Field(..., description="Verbatim physical text from DocumentTree")
    bounding_boxes: List[BoundingBox] = Field(default_factory=list, description="Physical bounding boxes")


class AdvocatePackItem(BaseModel):
    """Single item in the dossier with explicit evidentiary classification and provenance."""

    field_name: str = Field(..., description="Canonical field title e.g. 'Monthly Rent'")
    value: Optional[str] = Field(default=None, description="Factual extracted or derived value; None if unaddressed")
    classification: EvidenceClassification = Field(..., description="Factual evidence category")
    provenance_indices: List[int] = Field(default_factory=list, description="Indices to footnotes list")
    source_clauses: List[str] = Field(default_factory=list, description="Referenced clause numbers")
    exact_quotes: List[str] = Field(default_factory=list, description="Verbatim quote excerpts")
    notes: Optional[str] = Field(default=None, description="Descriptive evidentiary note if any")


class ExecutiveSummary(BaseModel):
    """Core transaction terms.

    Rule: Every value originates directly from a verified AtomicClaim.
    No inferred party, property, or date info.
    """

    parties_licensor: AdvocatePackItem
    parties_licensee: AdvocatePackItem
    property_address: AdvocatePackItem
    monthly_rent: AdvocatePackItem
    security_deposit: AdvocatePackItem
    tenure_months: AdvocatePackItem
    execution_date: AdvocatePackItem


class FinancialCovenantRow(BaseModel):
    """Row in the Financial Covenants Matrix."""

    term: str = Field(..., description="Specific financial covenant term name")
    amount_or_terms: str = Field(..., description="Extracted monetary amount or payment terms")
    actor_responsible: str = Field(default="Tenant", description="Responsible party / covenant actor")
    classification: EvidenceClassification = Field(default=EvidenceClassification.EXPLICIT_IN_DOCUMENT)
    provenance_indices: List[int] = Field(default_factory=list, description="Indices to footnotes list")
    source_clauses: List[str] = Field(default_factory=list, description="Referenced clause numbers")
    exact_quotes: List[str] = Field(default_factory=list, description="Verbatim quote excerpts")


class DiscrepancyItem(BaseModel):
    """Item in the Textual Divergence Schedule (Phase 6 Contradictions).

    Adheres strictly to bilateral evidence rules:
    - Never declares which clause is legally valid or controlling.
    - Presents side-by-side textual divergence with dual physical provenance.
    """

    subject: str = Field(..., description="Subject matter of divergence e.g. 'NOTICE_PERIOD'")
    actor: str = Field(..., description="Actor bound by the covenants e.g. 'TENANT'")
    divergence_summary: str = Field(..., description="Neutral factual description of divergence")
    classification: EvidenceClassification = Field(default=EvidenceClassification.CONFLICTING_EVIDENCE)
    source_a_clause: Optional[str] = Field(default=None, description="Clause reference for Source A")
    source_a_page: int = Field(..., ge=1, description="Page number for Source A")
    source_a_quote: str = Field(..., description="Verbatim quote for Source A")
    source_a_provenance_index: Optional[int] = Field(default=None, description="Footnote index for Source A")
    source_b_clause: Optional[str] = Field(default=None, description="Clause reference for Source B")
    source_b_page: int = Field(..., ge=1, description="Page number for Source B")
    source_b_quote: str = Field(..., description="Verbatim quote for Source B")
    source_b_provenance_index: Optional[int] = Field(default=None, description="Footnote index for Source B")
    neutral_comparison_statement: str = Field(..., description="Strictly non-evaluative comparison text")


class CoverageGapItem(BaseModel):
    """Item in Document Coverage & Clarification Gaps.

    Represents a specific checked field where no supporting passage was found.
    Rule: Never states the agreement is legally deficient or missing a required protection.
    """

    field_name: str = Field(..., description="Checked field name e.g. 'Deposit Refund Timeline'")
    classification: EvidenceClassification = Field(default=EvidenceClassification.NO_SUPPORTING_PASSAGE)
    status_display: str = Field(default="UNADDRESSED", description="Standard UI status pill")
    coverage_note: str = Field(
        default="No supporting provision found for this field.",
        description="Standard factual non-adjudicating notification",
    )
    checked_scope: str = Field(..., description="Description of the searched covenant boundary")


class AdvocatePack(BaseModel):
    """Complete Evidentiary Agreement Review Dossier.

    Deterministic compilation of verified workspace state.
    Zero generative hallucination; zero external legal advice.
    """

    document_name: str = Field(..., description="Filename or title of reviewed document")
    total_pages: int = Field(..., ge=1, description="Total physical pages in document")
    compilation_timestamp: str = Field(..., description="ISO 8601 compilation timestamp")
    executive_summary: ExecutiveSummary = Field(..., description="Core transaction terms backed by verified claims")
    financial_covenants: List[FinancialCovenantRow] = Field(
        default_factory=list, description="Matrix of all financial obligations"
    )
    textual_divergence_schedule: List[DiscrepancyItem] = Field(
        default_factory=list, description="Schedule of identified textual contradictions"
    )
    coverage_gaps: List[CoverageGapItem] = Field(
        default_factory=list, description="Checked covenant terms without supporting passages"
    )
    footnotes: List[ProvenanceFootnote] = Field(
        default_factory=list, description="Physical footnote citations with geometry"
    )
    legal_disclaimer: str = Field(
        default="Evidentiary Agreement Review Dossier compiled strictly from physical document text. This document does not constitute legal advice, statutory validation, or advocate representation.",
        description="Mandatory evidentiary disclaimer",
    )
    builder_version: str = Field(default="1.0.0", description="Advocate pack builder version")
