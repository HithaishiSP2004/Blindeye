"""Unit tests for Phase 8 Advocate Pack Pydantic models.

Enforces:
- Strict 4-tier evidence taxonomy (NO GENERAL_LEGAL_INFO).
- Zero sha256 hashing overhead.
- Document Coverage & Clarification Gaps non-adjudicating copy.
- Mandatory evidentiary non-advice disclaimer.
"""

import pytest
from backend.models.advocate_pack import (
    AdvocatePack,
    AdvocatePackItem,
    CoverageGapItem,
    DiscrepancyItem,
    EvidenceClassification,
    ExecutiveSummary,
    FinancialCovenantRow,
    ProvenanceFootnote,
)
from backend.models.document import BoundingBox


def test_evidence_classification_taxonomy_strictly_four_values():
    """Amendment 1: Evidence taxonomy strictly contains only 4 classifications."""
    assert len(EvidenceClassification) == 4
    expected_values = {
        "EXPLICIT_IN_DOCUMENT",
        "DERIVED_FROM_CLAUSES",
        "CONFLICTING_EVIDENCE",
        "NO_SUPPORTING_PASSAGE",
    }
    actual_values = {e.value for e in EvidenceClassification}
    assert actual_values == expected_values

    # Explicitly assert GENERAL_LEGAL_INFO is NOT present
    assert "GENERAL_LEGAL_INFO" not in actual_values
    assert not hasattr(EvidenceClassification, "GENERAL_LEGAL_INFO")


def test_advocate_pack_has_no_sha256_field():
    """Amendment 7: Remove sha256 from AdvocatePack model."""
    assert "sha256" not in AdvocatePack.model_fields
    assert "sha256_hash" not in AdvocatePack.model_fields


def test_coverage_gap_item_non_adjudicating_defaults():
    """Amendment 2: Unaddressed items must use non-adjudicating copy."""
    gap = CoverageGapItem(
        field_name="Security Deposit Refund Timeline",
        checked_scope="Searched for refund deadline",
    )
    assert gap.status_display == "UNADDRESSED"
    assert gap.coverage_note == "No supporting provision found for this field."
    assert gap.classification == EvidenceClassification.NO_SUPPORTING_PASSAGE
    # Must NOT mention 'missing legal protection' or 'deficient'
    assert "missing legal protection" not in gap.coverage_note.lower()
    assert "deficient" not in gap.coverage_note.lower()


def test_advocate_pack_minimal_valid_serialization():
    """Validate full pack model serialization and disclaimer."""
    footnote = ProvenanceFootnote(
        index=1,
        clause_id="clause_4",
        clause_number="Clause 4",
        page_number=1,
        exact_quote="The monthly rent shall be Rs. 25,000/-.",
        bounding_boxes=[BoundingBox(page=1, x0=10.0, y0=20.0, x1=80.0, y1=30.0)],
    )

    item_verified = AdvocatePackItem(
        field_name="Monthly Rent",
        value="Rs. 25,000/-",
        classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
        provenance_indices=[1],
        source_clauses=["Clause 4"],
        exact_quotes=["The monthly rent shall be Rs. 25,000/-."],
    )

    item_unaddressed = AdvocatePackItem(
        field_name="Premises Address",
        value=None,
        classification=EvidenceClassification.NO_SUPPORTING_PASSAGE,
        provenance_indices=[],
        source_clauses=[],
        exact_quotes=[],
        notes="No supporting provision found for this field.",
    )

    exec_summary = ExecutiveSummary(
        parties_licensor=item_verified,
        parties_licensee=item_verified,
        property_address=item_unaddressed,
        monthly_rent=item_verified,
        security_deposit=item_verified,
        tenure_months=item_verified,
        execution_date=item_unaddressed,
    )

    pack = AdvocatePack(
        document_name="Sample_Agreement.pdf",
        total_pages=2,
        compilation_timestamp="2026-09-26T12:00:00Z",
        executive_summary=exec_summary,
        financial_covenants=[
            FinancialCovenantRow(
                term="Monthly License Fee",
                amount_or_terms="Rs. 25,000/-",
                actor_responsible="Tenant",
                classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
                provenance_indices=[1],
                source_clauses=["Clause 4"],
                exact_quotes=["The monthly rent shall be Rs. 25,000/-."],
            )
        ],
        textual_divergence_schedule=[],
        coverage_gaps=[
            CoverageGapItem(
                field_name="Lock-in Period",
                checked_scope="Searched for lock-in terms",
            )
        ],
        footnotes=[footnote],
    )

    json_str = pack.model_dump_json()
    assert "Sample_Agreement.pdf" in json_str
    assert "Rs. 25,000/-" in json_str
    assert "Evidentiary Agreement Review Dossier" in pack.legal_disclaimer
    assert "legal advice" in pack.legal_disclaimer.lower()
