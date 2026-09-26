import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.extraction.provenance_resolver import resolve_provenance
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.models.document import DocumentTree
from backend.models.verification import ClaimTag, VerificationStatus
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator
from backend.verification.verification_gate import VerificationGate
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_doc_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_golden_tree",
        filename="golden_agreement.pdf",
        sha256_hash="dummy_hash",
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


@pytest.mark.asyncio
async def test_golden_agreement_full_verification(golden_doc_tree):
    """End-to-end Phase 4 verification against golden agreement fixture using deterministic mock (Correction 9)."""
    candidates = _mock_extract_candidates(golden_doc_tree)
    structured_agreement = resolve_provenance(candidates, golden_doc_tree)

    gate = VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())
    result = await gate.verify_agreement(structured_agreement, golden_doc_tree)

    summary = result.summary
    assert summary.total == 16
    assert summary.verified == 11
    assert summary.not_found == 5
    assert summary.ambiguous == 0
    assert summary.unresolved == 0
    assert summary.unsupported == 0
    assert summary.refused == 0

    claims_by_field = {c.field_name: c for c in result.claims}

    # 1. Assert Verified Facts carry physical provenance and ClaimTag.EXPLICIT
    verified_fields = [
        "monthly_rent",
        "security_deposit",
        "deposit_refund_days",
        "tenure_months",
        "commencement_date",
        "notice_period_days",
        "landlord_name",
        "tenant_name",
        "agreement_type",
        "execution_date",
        "maintenance_responsibility",
    ]
    for fn in verified_fields:
        claim = claims_by_field[fn]
        assert claim.status == VerificationStatus.VERIFIED
        assert claim.claim_tag == ClaimTag.EXPLICIT
        assert claim.source is not None
        assert claim.source.page in (1, 2)
        assert claim.source.bbox is not None
        assert claim.source.quote is not None
        assert len(claim.source.quote.strip()) > 0

    # 2. Assert Missing Facts carry ClaimTag.NOT_FOUND and zero coordinates
    missing_fields = [
        "lock_in_months",
        "property_address",
        "late_payment_penalty",
        "permitted_use",
        "renewal_terms",
    ]
    for fn in missing_fields:
        claim = claims_by_field[fn]
        assert claim.status == VerificationStatus.NOT_FOUND
        assert claim.claim_tag == ClaimTag.NOT_FOUND
        assert claim.source is None
