"""Phase 9 Claim-Level Verification Accuracy and Taxonomy Evaluation.

Tests:
- Verification status across canonical agreement fields.
- 4-tier taxonomy enforcement (EXPLICIT, DERIVED, NO_SUPPORTING_PASSAGE).
- Deterministic refusal for absent fields (does not propagate unsupported values).
"""

import os
import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.engine.clause_segmenter import segment_clauses
from backend.models.document import DocumentTree
from backend.models.verification import ClaimTag, VerificationStatus
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.extraction.provenance_resolver import resolve_provenance
from backend.verification.verification_gate import VerificationGate
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator


@pytest.fixture(scope="session")
def golden_doc_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_golden_tree",
        filename="golden_agreement.pdf",
        sha256_hash="dummy_hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


@pytest.fixture(scope="session")
def missing_fields_tree():
    path = "tests/fixtures/missing_fields_agreement.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_missing_tree",
        filename="missing_fields_agreement.pdf",
        sha256_hash="dummy_hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


@pytest.mark.asyncio
async def test_claim_level_verification_accuracy(golden_doc_tree):
    """Verify that all explicitly present fields carry physical quotes and ClaimTag.EXPLICIT."""
    candidates = _mock_extract_candidates(golden_doc_tree)
    structured_agreement = resolve_provenance(candidates, golden_doc_tree)
    gate = VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())
    result = await gate.verify_agreement(structured_agreement, golden_doc_tree)

    claims_by_field = {c.field_name: c for c in result.claims}

    # Core explicit terms
    rent = claims_by_field["monthly_rent"]
    assert rent.status == VerificationStatus.VERIFIED
    assert rent.claim_tag == ClaimTag.EXPLICIT
    assert rent.source is not None
    assert rent.source.page == 1
    assert "Rs. 35,000" in rent.source.quote
    assert rent.source.bbox is not None

    deposit = claims_by_field["security_deposit"]
    assert deposit.status == VerificationStatus.VERIFIED
    assert deposit.claim_tag == ClaimTag.EXPLICIT
    assert "1,00,000" in deposit.source.quote

    tenure = claims_by_field["tenure_months"]
    assert tenure.status == VerificationStatus.VERIFIED
    assert "11" in tenure.source.quote

    landlord = claims_by_field["landlord_name"]
    assert landlord.status == VerificationStatus.VERIFIED
    assert "Rajesh Kumar" in landlord.source.quote


@pytest.mark.asyncio
async def test_claim_level_absent_fields_unsupported_refusal(missing_fields_tree):
    """Amendment 1: Evaluates that absent fields do not propagate unsupported values through verification boundary."""
    candidates = _mock_extract_candidates(missing_fields_tree)
    structured_agreement = resolve_provenance(candidates, missing_fields_tree)
    gate = VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())
    result = await gate.verify_agreement(structured_agreement, missing_fields_tree)

    claims_by_field = {c.field_name: c for c in result.claims}

    # Fields completely absent from missing_fields_agreement
    absent_fields = ["security_deposit", "deposit_refund_days", "lock_in_months", "maintenance_responsibility", "late_payment_penalty"]
    for field in absent_fields:
        claim = claims_by_field.get(field)
        assert claim is not None, f"Expected claim for {field}"
        assert claim.status == VerificationStatus.NOT_FOUND
        assert claim.claim_tag == ClaimTag.NOT_FOUND
        # Zero unsupported factual values propagated
        assert claim.source is None or claim.source.quote is None
