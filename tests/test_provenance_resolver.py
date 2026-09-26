import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.extraction.provenance_resolver import resolve_provenance
from backend.models.document import BoundingBox, Clause, DocumentTree, TextSpan
from backend.models.extraction import (
    CandidateExtractionResult,
    CandidateFact,
    ExtractionStatus,
    MatchQuality,
    ResolutionMethod,
)
from backend.models.verification import ClaimTag
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


def test_exact_source_match(golden_doc_tree):
    """Test 1: Exact quote match -> EXACT_SOURCE_MATCH, FOUND, EXPLICIT, exact BoundingBox."""
    candidate = CandidateExtractionResult(
        monthly_rent=CandidateFact(
            field_name="monthly_rent",
            candidate_value="Rs. 35,000/- (Rupees Thirty Five Thousand) per month",
            candidate_quote="Rs. 35,000/- (Rupees Thirty Five Thousand) per month",
            candidate_clause_id=None,
            is_present=True,
        )
    )
    result = resolve_provenance(candidate, golden_doc_tree)
    rent = result.monthly_rent

    assert rent.status == ExtractionStatus.FOUND
    assert rent.claim_tag == ClaimTag.EXPLICIT
    assert rent.match_quality == MatchQuality.EXACT_SOURCE_MATCH
    assert rent.resolution_method == ResolutionMethod.EXACT_QUOTE
    assert "Rs. 35,000/- (Rupees Thirty Five Thousand) per month" in rent.exact_quote
    assert rent.page == 1
    assert rent.bbox is not None
    assert rent.bbox.page == 1
    assert len(rent.bounding_boxes) >= 1


def test_normalized_quote_match(golden_doc_tree):
    """Test 2: Normalized match handles case/spacing differences without mutating source quote."""
    # Search string has lowercase and missing punctuation
    candidate = CandidateExtractionResult(
        security_deposit=CandidateFact(
            field_name="security_deposit",
            candidate_value="1,00,000",
            candidate_quote="interest free refundable deposit of rs 1 00 000",
            candidate_clause_id=None,
            is_present=True,
        )
    )
    result = resolve_provenance(candidate, golden_doc_tree)
    dep = result.security_deposit

    assert dep.status == ExtractionStatus.FOUND
    assert dep.claim_tag == ClaimTag.EXPLICIT
    assert dep.match_quality in (MatchQuality.EXACT_SOURCE_MATCH, MatchQuality.NORMALIZED_SOURCE_MATCH)
    # CRITICAL: Exact quote MUST come from DocumentTree preserving original punctuation and capitalization
    assert "interest-free refundable deposit of Rs. 1,00,000" in dep.exact_quote
    assert dep.page == 1
    assert dep.bbox is not None


def test_disambiguation_of_repeated_values(golden_doc_tree):
    """Test 3: '30 days' appears in Clause 2(a) and Clause 4. Resolver must select contextually correct clause."""
    candidate = CandidateExtractionResult(
        deposit_refund_days=CandidateFact(
            field_name="deposit_refund_days",
            candidate_value="30 days",
            candidate_quote="refunded within 30 days",
            candidate_clause_id=None,  # No clause hint provided; resolver must disambiguate
            is_present=True,
        ),
        notice_period_days=CandidateFact(
            field_name="notice_period_days",
            candidate_value="30 days",
            candidate_quote="thirty (30) days",
            candidate_clause_id=None,
            is_present=True,
        ),
    )
    result = resolve_provenance(candidate, golden_doc_tree)

    # deposit_refund_days must resolve to Clause 2(a) on Page 1
    refund = result.deposit_refund_days
    assert refund.status == ExtractionStatus.FOUND
    assert refund.page == 1
    assert "refunded within 30 days" in refund.exact_quote

    # notice_period_days must resolve to Clause 4 on Page 2
    notice = result.notice_period_days
    assert notice.status == ExtractionStatus.FOUND
    assert notice.page == 2
    assert "thirty (30) days" in notice.exact_quote


def test_ambiguous_value_without_context():
    """Test 4: Repeated value across clauses with equal contextual relevance -> AMBIGUOUS."""
    span1 = TextSpan(
        span_id="s1",
        text="Section A penalty rate is 5 percent.",
        bbox=BoundingBox(page=1, x0=10, y0=10, x1=100, y1=20),
        char_start=0,
        char_end=36,
        clause_char_start=0,
        clause_char_end=36,
    )
    span2 = TextSpan(
        span_id="s2",
        text="Section B penalty rate is 5 percent.",
        bbox=BoundingBox(page=1, x0=10, y0=50, x1=100, y1=60),
        char_start=0,
        char_end=36,
        clause_char_start=0,
        clause_char_end=36,
    )

    c1 = Clause(
        clause_id="c_penalty1",
        clause_number="5.1",
        text="Section A penalty rate is 5 percent.",
        page_number=1,
        pages=[1],
        bounding_boxes=[span1.bbox],
        spans=[span1],
    )
    c2 = Clause(
        clause_id="c_penalty2",
        clause_number="5.2",
        text="Section B penalty rate is 5 percent.",
        page_number=1,
        pages=[1],
        bounding_boxes=[span2.bbox],
        spans=[span2],
    )

    tree = DocumentTree(
        document_id="doc_ambig",
        filename="ambig.pdf",
        sha256_hash="hash",
        page_count=1,
        clauses=[c1, c2],
    )

    candidate = CandidateExtractionResult(
        late_payment_penalty=CandidateFact(
            field_name="late_payment_penalty",
            candidate_value="5 percent",
            candidate_quote="5 percent",
            is_present=True,
        )
    )

    result = resolve_provenance(candidate, tree)
    penalty = result.late_payment_penalty
    # Because both clauses have equal relevance, resolver must mark AMBIGUOUS
    assert penalty.status == ExtractionStatus.AMBIGUOUS
    assert penalty.claim_tag is None
    assert penalty.match_quality == MatchQuality.AMBIGUOUS_MATCH
    assert len(penalty.ambiguity_candidates) == 2


def test_unresolved_hallucinated_candidate(golden_doc_tree):
    """Test 5: Hallucinated fact with zero source evidence -> UNRESOLVED, ClaimTag.NOT_FOUND, bbox=None."""
    candidate = CandidateExtractionResult(
        lock_in_months=CandidateFact(
            field_name="lock_in_months",
            candidate_value="6 months",
            candidate_quote="strictly subject to a 6 months lock-in period",
            is_present=True,
        )
    )
    result = resolve_provenance(candidate, golden_doc_tree)
    lock_in = result.lock_in_months

    assert lock_in.status == ExtractionStatus.UNRESOLVED
    assert lock_in.claim_tag is None  # Correction 1: UNRESOLVED must have claim_tag = None
    assert lock_in.bbox is None
    assert lock_in.exact_quote is None
    assert lock_in.match_quality == MatchQuality.NO_MATCH


def test_negative_extraction_not_found(golden_doc_tree):
    """Test 6: Fields with is_present=False or candidate_value=None -> NOT_FOUND, no fake bounding box."""
    candidate = CandidateExtractionResult(
        renewal_terms=CandidateFact(
            field_name="renewal_terms",
            candidate_value=None,
            candidate_quote=None,
            is_present=False,
        )
    )
    result = resolve_provenance(candidate, golden_doc_tree)
    renewal = result.renewal_terms

    assert renewal.status == ExtractionStatus.NOT_FOUND
    assert renewal.claim_tag == ClaimTag.NOT_FOUND
    assert renewal.value is None
    assert renewal.bbox is None
    assert renewal.exact_quote is None


def test_multi_page_clause_span(golden_doc_tree):
    """Test 7: Clause 3 spans across Page 1 and Page 2. Provenance resolver handles both pages."""
    candidate = CandidateExtractionResult(
        maintenance_responsibility=CandidateFact(
            field_name="maintenance_responsibility",
            candidate_value="Major structural repairs shall remain exclusive liability of Licensor",
            candidate_quote="Major structural repairs including seepage, external wall repairs, and electrical wiring failures shall remain the exclusive liability of the Licensor",
            candidate_clause_id="clause_p1_c4",  # Clause 3 starts on page 1
            is_present=True,
        )
    )
    result = resolve_provenance(candidate, golden_doc_tree)
    maint = result.maintenance_responsibility

    assert maint.status == ExtractionStatus.FOUND
    assert maint.claim_tag == ClaimTag.EXPLICIT
    # This portion of Clause 3 is on Page 2
    assert maint.page == 2
    assert "exclusive liability of the Licensor" in maint.exact_quote
    assert maint.bbox is not None
    assert maint.bbox.page == 2


def test_golden_agreement_end_to_end_derived_counts(golden_doc_tree):
    """Test 8: Golden fixture extraction asserts real expected facts and verified summary counts."""
    from backend.extraction.structured_extractor import _mock_extract_candidates

    candidates = _mock_extract_candidates(golden_doc_tree)
    agreement = resolve_provenance(candidates, golden_doc_tree)

    summary = agreement.summary
    assert summary.fields_total == 16
    assert summary.fields_found >= 9
    assert summary.fields_not_found >= 3
    assert summary.fields_provenance_resolved == summary.fields_found

    # 100% of facts marked FOUND must have physical bounding boxes and exact quotes
    for field_name in [
        "agreement_type",
        "execution_date",
        "landlord_name",
        "tenant_name",
        "tenure_months",
        "commencement_date",
        "monthly_rent",
        "security_deposit",
        "deposit_refund_days",
        "notice_period_days",
        "maintenance_responsibility",
    ]:
        field = getattr(agreement, field_name)
        if field.status == ExtractionStatus.FOUND:
            assert field.claim_tag == ClaimTag.EXPLICIT
            assert field.exact_quote is not None
            assert len(field.exact_quote.strip()) > 0
            assert field.bbox is not None
            assert field.page in (1, 2)
            assert field.bbox.page == field.page

    # Negative fields must be NOT_FOUND
    assert agreement.lock_in_months.status == ExtractionStatus.NOT_FOUND
    assert agreement.lock_in_months.claim_tag == ClaimTag.NOT_FOUND
    assert agreement.lock_in_months.bbox is None
