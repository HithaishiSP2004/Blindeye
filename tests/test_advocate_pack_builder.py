"""Tests for the deterministic Advocate Preparation Pack Builder.

Verifies:
- Amendment 1: 4-tier evidence taxonomy only.
- Amendment 2: Document Coverage & Clarification Gaps naming and copy.
- Amendment 4: Executive summary values originate strictly from verified AtomicClaims; absent values remain None.
- Amendment 5: Deterministic compilation without unsupported values.
- Amendment 6: DERIVED_FROM_CLAUSES combines only verified claims and lists all supporting clauses.
- Amendment 8: Direct synthesis of DocumentTree + VerificationResult + ContradictionResponse.
"""

import pytest
from backend.advocate.pack_builder import build_advocate_pack
from backend.models.advocate_pack import EvidenceClassification
from backend.models.document import (
    BoundingBox,
    Clause,
    DocumentTree,
    PageData,
    ParsingStatus,
    TextBlock,
)
from backend.models.verification import (
    AtomicClaim,
    ClaimSource,
    ClaimTag,
    VerificationResult,
    VerificationStatus,
)
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionEvidence,
    ContradictionFinding,
    ContradictionResponse,
    ContradictionStatus,
    ContradictionSubject,
)


def _make_dummy_doc_tree() -> DocumentTree:
    box = BoundingBox(page=1, x0=10.0, y0=10.0, x1=90.0, y1=20.0)
    block = TextBlock(block_id="b1", block_number=0, page=1, text="Dummy Agreement Text", bbox=box)
    clause = Clause(
        clause_id="clause_1",
        clause_number="Clause 1",
        title="RENT",
        text="Monthly rent shall be Rs. 25,000/-.",
        page_number=1,
        pages=[1],
        bounding_boxes=[box],
        source_block_ids=["b1"],
    )
    page = PageData(page_number=1, width=595.0, height=842.0, blocks=[block], raw_text="Dummy")
    return DocumentTree(
        document_id="doc_123",
        filename="dummy.pdf",
        sha256_hash="dummy_hash",
        file_size_bytes=1000,
        page_count=1,
        parsing_status=ParsingStatus.TEXT_AVAILABLE,
        pages=[page],
        clauses=[clause],
    )


def test_clean_agreement_pack_builder():
    """Verify clean agreement pack builder generates verified summary, financial matrix, and coverage gaps."""
    doc_tree = _make_dummy_doc_tree()
    bbox = BoundingBox(page=1, x0=10.0, y0=20.0, x1=80.0, y1=25.0)

    claims = [
        AtomicClaim(
            claim_id="c_rent",
            field_name="monthly_rent",
            subject="monthly_rent",
            value="Rs. 25,000/-",
            status=VerificationStatus.VERIFIED,
            claim_tag=ClaimTag.EXPLICIT,
            source=ClaimSource(
                clause_id="clause_4",
                clause_number="Clause 4",
                page=1,
                quote="The monthly rent is Rs. 25,000/-.",
                bbox=bbox,
            ),
            supporting_clause_ids=["clause_4"],
            exact_quotes=["The monthly rent is Rs. 25,000/-."],
        ),
        AtomicClaim(
            claim_id="c_deposit",
            field_name="security_deposit",
            subject="security_deposit",
            value="Rs. 1,00,000/-",
            status=VerificationStatus.VERIFIED,
            claim_tag=ClaimTag.EXPLICIT,
            source=ClaimSource(
                clause_id="clause_5",
                clause_number="Clause 5",
                page=1,
                quote="Security deposit shall be Rs. 1,00,000/-.",
                bbox=bbox,
            ),
            supporting_clause_ids=["clause_5"],
            exact_quotes=["Security deposit shall be Rs. 1,00,000/-."],
        ),
        AtomicClaim(
            claim_id="c_landlord",
            field_name="landlord_name",
            subject="landlord_name",
            value="Mr. Ramesh Kumar",
            status=VerificationStatus.VERIFIED,
            claim_tag=ClaimTag.EXPLICIT,
            source=ClaimSource(
                clause_id="preamble",
                clause_number="Preamble",
                page=1,
                quote="Mr. Ramesh Kumar, hereinafter called the Licensor",
                bbox=bbox,
            ),
            supporting_clause_ids=["preamble"],
            exact_quotes=["Mr. Ramesh Kumar, hereinafter called the Licensor"],
        ),
        AtomicClaim(
            claim_id="c_tenant",
            field_name="tenant_name",
            subject="tenant_name",
            value="Ms. Anita Desai",
            status=VerificationStatus.VERIFIED,
            claim_tag=ClaimTag.EXPLICIT,
            source=ClaimSource(
                clause_id="preamble",
                clause_number="Preamble",
                page=1,
                quote="Ms. Anita Desai, hereinafter called the Licensee",
                bbox=bbox,
            ),
            supporting_clause_ids=["preamble"],
            exact_quotes=["Ms. Anita Desai, hereinafter called the Licensee"],
        ),
    ]

    veri_res = VerificationResult(
        is_verified=True,
        overall_tag=ClaimTag.EXPLICIT,
        claims=claims,
    )

    pack = build_advocate_pack(doc_tree, veri_res, document_name="Clean_Agreement.pdf")

    # 1. Executive Summary checks
    assert pack.executive_summary.parties_licensor.value == "Mr. Ramesh Kumar"
    assert pack.executive_summary.parties_licensor.classification == EvidenceClassification.EXPLICIT_IN_DOCUMENT
    assert pack.executive_summary.parties_licensee.value == "Ms. Anita Desai"
    assert pack.executive_summary.monthly_rent.value == "Rs. 25,000/-"
    assert pack.executive_summary.security_deposit.value == "Rs. 1,00,000/-"
    # Unverified items remain absent (Amendment 4)
    assert pack.executive_summary.property_address.value is None
    assert pack.executive_summary.property_address.classification == EvidenceClassification.NO_SUPPORTING_PASSAGE
    assert pack.executive_summary.property_address.notes == "No supporting provision found for this field."

    # 2. Financial Covenants checks (Amendment 6: DERIVED_FROM_CLAUSES combines verified claims)
    terms = [row.term for row in pack.financial_covenants]
    assert any("Monthly License Fee" in t for t in terms)
    assert any("Security Deposit" in t for t in terms)

    derived_row = next(r for r in pack.financial_covenants if r.classification == EvidenceClassification.DERIVED_FROM_CLAUSES)
    assert "Rs. 1,00,000/-" in derived_row.amount_or_terms
    assert "Rs. 25,000/-" in derived_row.amount_or_terms
    assert "Clause 4" in derived_row.source_clauses
    assert "Clause 5" in derived_row.source_clauses

    # 3. Textual divergence is empty for clean agreement
    assert len(pack.textual_divergence_schedule) == 0

    # 4. Document Coverage Gaps
    gap_names = [g.field_name for g in pack.coverage_gaps]
    assert "Security Deposit Refund Timeline" in gap_names
    assert "Lock-in Period Commitment" in gap_names
    for gap in pack.coverage_gaps:
        assert gap.status_display == "UNADDRESSED"
        assert gap.coverage_note == "No supporting provision found for this field."
        assert gap.classification == EvidenceClassification.NO_SUPPORTING_PASSAGE

    # 5. Footnotes populated
    assert len(pack.footnotes) >= 2


def test_conflicting_agreement_pack_builder():
    """Verify conflicting agreement adds discrepancy schedule with dual footnotes."""
    doc_tree = _make_dummy_doc_tree()
    bbox = BoundingBox(page=1, x0=10.0, y0=20.0, x1=80.0, y1=25.0)

    veri_res = VerificationResult(
        is_verified=True,
        overall_tag=ClaimTag.EXPLICIT,
        claims=[],
    )

    finding = ContradictionFinding(
        finding_id="finding_1",
        status=ContradictionStatus.CONFIRMED_CONFLICT,
        subject=ContradictionSubject.NOTICE_PERIOD,
        actor=ContradictionActor.TENANT,
        value_a="1 month",
        value_b="2 months",
        unit="months",
        claim_a="Notice period is 1 month",
        claim_b="Notice period is 2 months",
        source_a=ContradictionEvidence(
            clause_id="clause_4",
            clause_number="Clause 4",
            page_number=1,
            exact_quote="Either party may terminate by giving one month notice.",
            bounding_boxes=[bbox],
        ),
        source_b=ContradictionEvidence(
            clause_id="clause_11",
            clause_number="Clause 11",
            page_number=2,
            exact_quote="The licensee shall provide two months prior written notice before vacating.",
            bounding_boxes=[bbox],
        ),
        explanation="Clause 4 specifies 1 month notice while Clause 11 specifies 2 months notice for the tenant.",
    )

    contra_resp = ContradictionResponse(
        findings=[finding],
        total_conflicts=1,
        evaluation_summary="1 confirmed conflict detected.",
    )

    pack = build_advocate_pack(
        doc_tree,
        veri_res,
        contradiction_response=contra_resp,
        document_name="Conflicting_Agreement.pdf",
    )

    assert len(pack.textual_divergence_schedule) == 1
    item = pack.textual_divergence_schedule[0]
    assert item.classification == EvidenceClassification.CONFLICTING_EVIDENCE
    assert item.subject == "NOTICE_PERIOD"
    assert item.source_a_clause == "Clause 4"
    assert item.source_a_page == 1
    assert item.source_b_clause == "Clause 11"
    assert item.source_b_page == 2
    assert item.source_a_provenance_index is not None
    assert item.source_b_provenance_index is not None
    assert item.source_a_provenance_index != item.source_b_provenance_index
    assert "Clause 4 specifies 1 month" in item.neutral_comparison_statement


def test_builder_is_deterministic():
    """Amendment 5: Pack builder is deterministic and yields identical results."""
    doc_tree = _make_dummy_doc_tree()
    bbox = BoundingBox(page=1, x0=10.0, y0=20.0, x1=80.0, y1=25.0)
    claim = AtomicClaim(
        claim_id="c_rent",
        field_name="monthly_rent",
        value="Rs. 25,000/-",
        status=VerificationStatus.VERIFIED,
        claim_tag=ClaimTag.EXPLICIT,
        source=ClaimSource(
            clause_id="clause_4",
            clause_number="Clause 4",
            page=1,
            quote="The monthly rent is Rs. 25,000/-.",
            bbox=bbox,
        ),
    )
    veri_res = VerificationResult(is_verified=True, overall_tag=ClaimTag.EXPLICIT, claims=[claim])

    pack1 = build_advocate_pack(doc_tree, veri_res, document_name="test.pdf")
    pack2 = build_advocate_pack(doc_tree, veri_res, document_name="test.pdf")

    # Ignoring timestamp differences
    p1_dict = pack1.model_dump()
    p2_dict = pack2.model_dump()
    p1_dict.pop("compilation_timestamp")
    p2_dict.pop("compilation_timestamp")
    assert p1_dict == p2_dict
