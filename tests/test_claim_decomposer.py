import pytest
from backend.models.document import BoundingBox
from backend.models.extraction import ExtractionStatus, ProvenancedValue, StructuredAgreement
from backend.models.verification import ClaimTag, VerificationStatus
from backend.verification.claim_decomposer import decompose_agreement, decompose_field_to_atomic_claim


def test_decompose_single_field():
    """Verify single field decomposes into atomic claim with subject, actor, predicate, and unit."""
    val = ProvenancedValue(
        field_name="monthly_rent",
        status=ExtractionStatus.FOUND,
        value="Rs. 35,000",
        is_present=True,
        claim_tag=ClaimTag.EXPLICIT,
        source_clause_id="clause_p1_c2",
        source_clause_number="2.1",
        page=1,
        exact_quote="Rs. 35,000/- per month",
        bbox=BoundingBox(page=1, x0=50, y0=270, x1=545, y1=305),
    )
    claim = decompose_field_to_atomic_claim("monthly_rent", val, "doc_123")

    assert claim.claim_id == "claim_doc_123_monthly_rent"
    assert claim.field_name == "monthly_rent"
    assert claim.subject == "monthly_rent"
    assert claim.actor == "licensee"
    assert claim.predicate == "shall_pay"
    assert claim.value == "Rs. 35,000"
    assert claim.unit == "INR"
    assert "per month" in claim.qualifiers
    assert claim.source is not None
    assert claim.source.clause_id == "clause_p1_c2"
    assert claim.source.bbox is not None


def test_decompose_agreement_all_16_fields():
    """Verify decompose_agreement creates 16 independent atomic claims."""
    agreement = StructuredAgreement(document_id="doc_full_test")
    claims = decompose_agreement(agreement, "doc_full_test")

    assert len(claims) == 16
    field_names = [c.field_name for c in claims]
    assert "monthly_rent" in field_names
    assert "security_deposit" in field_names
    assert "deposit_refund_days" in field_names
    assert "notice_period_days" in field_names
    assert "lock_in_months" in field_names

    # Check unpopulated fields default safely with claim_tag = None
    rent_claim = next(c for c in claims if c.field_name == "monthly_rent")
    assert rent_claim.status == VerificationStatus.UNRESOLVED
    assert rent_claim.claim_tag is None
