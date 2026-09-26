import pytest
from pydantic import ValidationError
from backend.models.document import BoundingBox, Clause, DocumentTree
from backend.models.extraction import ProvenancedValue, StructuredAgreement
from backend.models.verification import AtomicClaim, ClaimTag, VerificationResult


def test_bounding_box_valid():
    """Verify BoundingBox enforces valid page and coordinate values."""
    bbox = BoundingBox(page=1, x0=10.0, y0=20.0, x1=200.0, y1=250.0)
    assert bbox.page == 1
    assert bbox.x0 == 10.0
    assert bbox.y1 == 250.0


def test_bounding_box_invalid_page():
    """Verify BoundingBox rejects non-positive page numbers."""
    with pytest.raises(ValidationError):
        BoundingBox(page=0, x0=10.0, y0=20.0, x1=200.0, y1=250.0)


def test_clause_model():
    """Verify Clause model encapsulates text, page, and bounding boxes correctly."""
    bbox = BoundingBox(page=2, x0=50.0, y0=100.0, x1=500.0, y1=140.0)
    clause = Clause(
        clause_id="clause_p2_c4",
        clause_number="4",
        title="SECURITY DEPOSIT",
        text="The Licensee has deposited a sum of Rs. 1,00,000 as refundable deposit.",
        page_number=2,
        bounding_boxes=[bbox],
    )
    assert clause.clause_id == "clause_p2_c4"
    assert len(clause.bounding_boxes) == 1
    assert clause.bounding_boxes[0].page == 2


def test_document_tree_serialization():
    """Verify DocumentTree model serializes and deserializes accurately."""
    doc = DocumentTree(
        document_id="doc_test_123",
        filename="lease_agreement.pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        page_count=3,
        clauses=[],
    )
    dumped = doc.model_dump()
    assert dumped["document_id"] == "doc_test_123"
    assert dumped["page_count"] == 3

    rebuilt = DocumentTree.model_validate(dumped)
    assert rebuilt.filename == "lease_agreement.pdf"


def test_claim_tag_enum():
    """Verify persistent A-E evidence taxonomy strings."""
    assert ClaimTag.EXPLICIT.value == "A / EXPLICIT IN DOCUMENT"
    assert ClaimTag.DERIVED.value == "B / DERIVED FROM CLAUSES"
    assert ClaimTag.GENERAL_LEGAL.value == "C / GENERAL LEGAL INFORMATION"
    assert ClaimTag.NOT_FOUND.value == "D / NO SUPPORTING PASSAGE"
    assert ClaimTag.CONFLICTING.value == "E / CONFLICTING EVIDENCE"


def test_atomic_claim_and_verification_result():
    """Verify atomic claims assemble into a VerificationResult."""
    claim = AtomicClaim(
        claim_id="claim_1",
        claim_text="The security deposit is Rs. 1,00,000.",
        tag=ClaimTag.EXPLICIT,
        supporting_clause_ids=["clause_p2_c4"],
        exact_quotes=["deposited a sum of Rs. 1,00,000"],
        confidence_score=0.98,
    )
    result = VerificationResult(
        is_verified=True,
        overall_tag=ClaimTag.EXPLICIT,
        claims=[claim],
    )
    assert result.is_verified is True
    assert len(result.claims) == 1
    assert result.claims[0].tag == ClaimTag.EXPLICIT


def test_structured_agreement_provenance():
    """Verify structured agreement fields carry explicit provenance."""
    rent = ProvenancedValue(
        value="₹35,000",
        is_present=True,
        source_clause_id="clause_p1_c2",
        source_clause_number="Clause 2",
        page=1,
        exact_quote="monthly rent of Rs. 35,000/-",
    )
    agreement = StructuredAgreement(
        document_id="doc_test_123",
        monthly_rent=rent,
    )
    assert agreement.monthly_rent.is_present is True
    assert agreement.monthly_rent.value == "₹35,000"
    assert agreement.monthly_rent.page == 1
    # Verify unpopulated field has default empty ProvenancedValue
    assert agreement.security_deposit.value is None
    assert agreement.security_deposit.is_present is False
