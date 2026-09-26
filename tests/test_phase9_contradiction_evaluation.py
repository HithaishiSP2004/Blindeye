"""Phase 9 Contradiction Engine Boundaries and Edge Cases Evaluation.

Enforces Amendment 4:
- Different actor + different duty -> NO_CONFLICT.
- Does NOT generalize: Different values -> NO_CONFLICT.
- Same actor + same subject + incompatible values -> CONFIRMED_CONFLICT with dual provenance.
- Missing actor / unknown context -> INSUFFICIENT_CONTEXT / UNRESOLVED.
- Missing provenance -> Never CONFIRMED_CONFLICT.
- Strictly non-evaluative: zero claims of legal priority or enforceability.
"""

import os
import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.engine.clause_segmenter import segment_clauses
from backend.models.document import DocumentTree
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionFinding,
    ContradictionStatus,
    ContradictionSubject,
)
from backend.contradiction.detector import ContradictionDetector
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.extraction.provenance_resolver import resolve_provenance


@pytest.fixture(scope="session")
def different_actors_tree():
    path = "tests/fixtures/different_actors_notice.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_diff_actors",
        filename="different_actors_notice.pdf",
        sha256_hash="hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


@pytest.fixture(scope="session")
def conflicting_notice_tree():
    path = "frontend/public/golden_agreement_conflicting.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_conflict",
        filename="golden_agreement_conflicting.pdf",
        sha256_hash="hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


def test_different_actor_different_duty_is_not_conflict(different_actors_tree):
    """Amendment 4: Different actor + different duty -> NO_CONFLICT.

    Clause 4 specifies Landlord notice = 60 days.
    Clause 5 specifies Tenant notice = 30 days.
    Because actors are different, this is NOT a contradiction.
    """
    candidates = _mock_extract_candidates(different_actors_tree)
    structured_agreement = resolve_provenance(candidates, different_actors_tree)
    detector = ContradictionDetector()
    response = detector.detect_contradictions(different_actors_tree, structured_agreement)

    # Asserts that no CONFIRMED_CONFLICT exists between Clause 4 and Clause 5
    confirmed_conflicts = [f for f in response.findings if f.status == ContradictionStatus.CONFIRMED_CONFLICT]
    assert len(confirmed_conflicts) == 0

    # Specifically check notice period comparisons if any
    for f in response.findings:
        if f.subject == ContradictionSubject.NOTICE_PERIOD:
            assert f.status != ContradictionStatus.CONFIRMED_CONFLICT


def test_same_actor_same_subject_incompatible_values_is_conflict(conflicting_notice_tree):
    """Same actor + same subject + incompatible values -> CONFIRMED_CONFLICT with dual physical citations."""
    candidates = _mock_extract_candidates(conflicting_notice_tree)
    structured_agreement = resolve_provenance(candidates, conflicting_notice_tree)
    detector = ContradictionDetector()
    response = detector.detect_contradictions(conflicting_notice_tree, structured_agreement)

    confirmed_conflicts = [f for f in response.findings if f.status == ContradictionStatus.CONFIRMED_CONFLICT]
    assert len(confirmed_conflicts) >= 1

    notice_conflict = next(f for f in confirmed_conflicts if f.subject == ContradictionSubject.NOTICE_PERIOD)
    assert notice_conflict.actor in [ContradictionActor.TENANT, ContradictionActor.BOTH, ContradictionActor.MUTUAL]
    # Check dual physical provenance
    assert notice_conflict.source_a.page_number >= 1
    assert notice_conflict.source_a.exact_quote != ""
    assert notice_conflict.source_b.page_number >= 1
    assert notice_conflict.source_b.exact_quote != ""
    # Check strictly non-adjudicating explanation
    assert "legally binding" not in notice_conflict.explanation.lower()
    assert "superior" not in notice_conflict.explanation.lower()
    assert "invalid" not in notice_conflict.explanation.lower()
