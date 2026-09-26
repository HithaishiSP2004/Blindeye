import pytest
from backend.models.document import BoundingBox, Clause, DocumentTree, TextSpan
from backend.models.extraction import ExtractionStatus, ProvenancedValue, StructuredAgreement
from backend.models.verification import ClaimTag, VerificationStatus
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator
from backend.verification.verification_gate import VerificationGate


@pytest.fixture
def gate():
    return VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())


@pytest.mark.asyncio
async def test_gate_decision_states_and_claim_tags(gate):
    """CRITICAL (Correction 1): Verify exact mapping of verification states to ClaimTags.

    VERIFIED -> EXPLICIT
    NOT_FOUND -> NOT_FOUND
    UNRESOLVED -> None
    AMBIGUOUS -> None
    UNSUPPORTED -> None
    """
    bbox = BoundingBox(page=1, x0=50, y0=270, x1=545, y1=305)
    span = TextSpan(
        span_id="s1",
        text="Monthly rent of Rs. 35,000/- per month",
        bbox=bbox,
        char_start=0,
        char_end=38,
        clause_char_start=0,
        clause_char_end=38,
    )
    c1 = Clause(
        clause_id="cl_rent",
        clause_number="2.1",
        text="Monthly rent of Rs. 35,000/- per month",
        page_number=1,
        pages=[1],
        bounding_boxes=[bbox],
        spans=[span],
    )
    doc_tree = DocumentTree(
        document_id="doc_gate_test",
        filename="lease.pdf",
        sha256_hash="hash",
        page_count=1,
        clauses=[c1],
    )

    agreement = StructuredAgreement(
        document_id="doc_gate_test",
        # 1. Supported fact
        monthly_rent=ProvenancedValue(
            field_name="monthly_rent",
            status=ExtractionStatus.FOUND,
            value="Rs. 35,000",
            is_present=True,
            claim_tag=ClaimTag.EXPLICIT,
            source_clause_id="cl_rent",
            source_clause_number="2.1",
            page=1,
            exact_quote="Monthly rent of Rs. 35,000/- per month",
            bbox=bbox,
            bounding_boxes=[bbox],
        ),
        # 2. Unsupported fact (numeric conflict)
        security_deposit=ProvenancedValue(
            field_name="security_deposit",
            status=ExtractionStatus.FOUND,
            value="Rs. 5,00,000",  # conflicts with source having no 5,00,000
            is_present=True,
            claim_tag=ClaimTag.EXPLICIT,
            source_clause_id="cl_rent",
            page=1,
            exact_quote="Monthly rent of Rs. 35,000/- per month",
            bbox=bbox,
        ),
        # 3. Not found fact
        lock_in_months=ProvenancedValue(
            field_name="lock_in_months",
            status=ExtractionStatus.NOT_FOUND,
            value=None,
            is_present=False,
            claim_tag=ClaimTag.NOT_FOUND,
        ),
        # 4. Ambiguous fact
        deposit_refund_days=ProvenancedValue(
            field_name="deposit_refund_days",
            status=ExtractionStatus.AMBIGUOUS,
            value="30 days",
            is_present=False,
            claim_tag=None,
        ),
        # 5. Unresolved fact
        renewal_terms=ProvenancedValue(
            field_name="renewal_terms",
            status=ExtractionStatus.UNRESOLVED,
            value="Option to extend 1 year",
            is_present=False,
            claim_tag=None,
        ),
    )

    result = await gate.verify_agreement(agreement, doc_tree)

    claims_map = {c.field_name: c for c in result.claims}

    # 1. Supported claim -> VERIFIED, ClaimTag.EXPLICIT
    rent_claim = claims_map["monthly_rent"]
    assert rent_claim.status == VerificationStatus.VERIFIED
    assert rent_claim.claim_tag == ClaimTag.EXPLICIT

    # 2. Unsupported claim -> UNSUPPORTED, ClaimTag = None (Correction 1)
    dep_claim = claims_map["security_deposit"]
    assert dep_claim.status == VerificationStatus.UNSUPPORTED
    assert dep_claim.claim_tag is None

    # 3. Not found claim -> NOT_FOUND, ClaimTag.NOT_FOUND
    lock_claim = claims_map["lock_in_months"]
    assert lock_claim.status == VerificationStatus.NOT_FOUND
    assert lock_claim.claim_tag == ClaimTag.NOT_FOUND

    # 4. Ambiguous claim -> AMBIGUOUS, ClaimTag = None (Correction 1)
    ref_claim = claims_map["deposit_refund_days"]
    assert ref_claim.status == VerificationStatus.AMBIGUOUS
    assert ref_claim.claim_tag is None

    # 5. Unresolved claim -> UNRESOLVED, ClaimTag = None (Correction 1: NEVER NOT_FOUND!)
    ren_claim = claims_map["renewal_terms"]
    assert ren_claim.status == VerificationStatus.UNRESOLVED
    assert ren_claim.claim_tag is None

    # Derived summary metrics check
    summary = result.summary
    assert summary.total == 16
    assert summary.verified == 1
    assert summary.unsupported == 1
    assert summary.ambiguous == 1
    assert summary.unresolved == 1
    assert summary.not_found == 12
