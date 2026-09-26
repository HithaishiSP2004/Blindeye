import pytest
from backend.contradiction.context_matcher import ContextMatcher
from backend.contradiction.detector import ContradictionDetector
from backend.contradiction.extractor import CandidateStatement
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionEvidence,
    ContradictionStatus,
    ContradictionSubject,
)
from backend.models.document import BoundingBox, Clause, DocumentTree, PageData, ParsingStatus


def test_missing_provenance_never_confirmed_conflict():
    # If a candidate statement lacks physical provenance, it must not become CONFIRMED_CONFLICT
    matcher = ContextMatcher()

    ev_a = ContradictionEvidence(
        clause_id="c_1",
        clause_number="1",
        page_number=1,
        exact_quote="",  # Missing quote
        bounding_boxes=[],  # Missing bboxes
    )
    ev_b = ContradictionEvidence(
        clause_id="c_2",
        clause_number="2",
        page_number=2,
        exact_quote="Tenant shall provide 60 days notice.",
        bounding_boxes=[BoundingBox(page=2, x0=50.0, y0=100.0, x1=200.0, y1=120.0)],
    )

    stmt_a = CandidateStatement(
        statement_id="stmt_1",
        subject=ContradictionSubject.NOTICE_PERIOD,
        actor=ContradictionActor.TENANT,
        raw_value="30 days",
        normalized_value="30",
        unit="days",
        claim_summary="Tenant notice period: 30 days",
        evidence=ev_a,
    )
    stmt_b = CandidateStatement(
        statement_id="stmt_2",
        subject=ContradictionSubject.NOTICE_PERIOD,
        actor=ContradictionActor.TENANT,
        raw_value="60 days",
        normalized_value="60",
        unit="days",
        claim_summary="Tenant notice period: 60 days",
        evidence=ev_b,
    )

    finding = matcher.evaluate_pair(stmt_a, stmt_b)
    assert finding.status in (ContradictionStatus.INSUFFICIENT_CONTEXT, ContradictionStatus.UNRESOLVED)
    assert finding.status != ContradictionStatus.CONFIRMED_CONFLICT
    assert "provenance" in finding.explanation.lower()


def test_multipage_contradiction_preserves_dual_locations():
    detector = ContradictionDetector()
    clauses = [
        Clause(
            clause_id="c_p1",
            clause_number="3",
            title="Notice on Page 1",
            text="The Tenant shall provide 30 days notice.",
            page_number=1,
            pages=[1],
            bounding_boxes=[BoundingBox(page=1, x0=50.0, y0=200.0, x1=300.0, y1=220.0)],
            spans=[],
            source_block_ids=[],
        ),
        Clause(
            clause_id="c_p2",
            clause_number="11",
            title="Notice on Page 2",
            text="The Tenant shall provide 60 days notice before moving out.",
            page_number=2,
            pages=[2],
            bounding_boxes=[BoundingBox(page=2, x0=60.0, y0=400.0, x1=350.0, y1=420.0)],
            spans=[],
            source_block_ids=[],
        ),
    ]
    doc = DocumentTree(
        document_id="multipage_doc",
        filename="multipage_test.pdf",
        sha256_hash="dummy",
        file_size_bytes=2000,
        page_count=2,
        parsing_status=ParsingStatus.TEXT_AVAILABLE,
        pages=[PageData(page_number=1, width=595.0, height=842.0), PageData(page_number=2, width=595.0, height=842.0)],
        clauses=clauses,
    )

    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 1
    conflict = res.findings[0]
    assert conflict.status == ContradictionStatus.CONFIRMED_CONFLICT
    # Ensure source A is on page 1 and source B is on page 2 (or vice versa)
    pages = {conflict.source_a.page_number, conflict.source_b.page_number}
    assert pages == {1, 2}
    assert len(conflict.source_a.bounding_boxes) >= 1
    assert len(conflict.source_b.bounding_boxes) >= 1
