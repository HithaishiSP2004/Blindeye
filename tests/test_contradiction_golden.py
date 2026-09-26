import os
import pytest
from backend.contradiction.detector import ContradictionDetector
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.extraction.provenance_resolver import resolve_provenance
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.models.contradiction import ContradictionStatus, ContradictionSubject
from backend.models.document import DocumentTree
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_doc_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, parsing_status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="golden_doc",
        filename="golden_agreement.pdf",
        sha256_hash="dummy",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
    )


@pytest.fixture
def golden_structured_agreement(golden_doc_tree):
    candidates = _mock_extract_candidates(golden_doc_tree)
    return resolve_provenance(candidates, golden_doc_tree)



def test_golden_agreement_has_zero_conflicts(golden_doc_tree, golden_structured_agreement):
    # In the clean golden residential agreement, covenants are harmonious:
    # Rent = ₹35,000, Deposit = ₹1,00,000, Notice = 30 days.
    # Total conflicts must be 0.
    detector = ContradictionDetector()
    res = detector.detect_contradictions(golden_doc_tree, golden_structured_agreement)
    assert res.total_conflicts == 0
    assert "No conflicting statements" in res.evaluation_summary


def test_golden_agreement_with_conflicting_notice_clause(golden_doc_tree, golden_structured_agreement):
    # Introduce an injected conflicting clause: Clause 15 stating tenant notice is 60 days
    from backend.models.document import BoundingBox, Clause
    conflicting_clause = Clause(
        clause_id="clause_15",
        clause_number="15",
        title="Termination Notice",
        text="Notwithstanding anything contained herein, either party may terminate this agreement by serving sixty (60) days written notice.",
        page_number=2,
        pages=[2],
        bounding_boxes=[BoundingBox(page=2, x0=50.0, y0=600.0, x1=400.0, y1=620.0)],
        spans=[],
        source_block_ids=[],
    )

    custom_tree = DocumentTree(
        document_id="conflict_doc",
        filename="golden_agreement_with_conflict.pdf",
        sha256_hash="dummy",
        file_size_bytes=golden_doc_tree.file_size_bytes,
        page_count=golden_doc_tree.page_count,
        parsing_status=golden_doc_tree.parsing_status,
        pages=golden_doc_tree.pages,
        clauses=golden_doc_tree.clauses + [conflicting_clause],
    )

    detector = ContradictionDetector()
    res = detector.detect_contradictions(custom_tree, golden_structured_agreement)
    assert res.total_conflicts >= 1

    notice_conflicts = [
        f for f in res.findings
        if f.status == ContradictionStatus.CONFIRMED_CONFLICT and f.subject == ContradictionSubject.NOTICE_PERIOD
    ]
    assert len(notice_conflicts) == 1
    conflict = notice_conflicts[0]
    assert "30" in conflict.value_a or "30" in conflict.value_b
    assert "60" in conflict.value_a or "60" in conflict.value_b
    # Must have dual physical provenance
    assert conflict.source_a.page_number in (1, 2)
    assert conflict.source_b.page_number in (1, 2)
    assert len(conflict.source_a.bounding_boxes) >= 1
    assert len(conflict.source_b.bounding_boxes) >= 1
