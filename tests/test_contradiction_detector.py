import pytest
from backend.contradiction.detector import ContradictionDetector
from backend.models.contradiction import ContradictionActor, ContradictionStatus, ContradictionSubject
from backend.models.document import BoundingBox, Clause, DocumentTree, PageData, ParsingStatus


def make_test_tree(clauses_data):
    """Helper to build a synthetic DocumentTree with test clauses."""
    clauses = []
    for c_id, c_num, text, pg in clauses_data:
        clauses.append(
            Clause(
                clause_id=c_id,
                clause_number=c_num,
                title=f"Clause {c_num}",
                text=text,
                page_number=pg,
                pages=[pg],
                bounding_boxes=[BoundingBox(page=pg, x0=50.0, y0=float(100 * len(clauses) + 50), x1=350.0, y1=float(100 * len(clauses) + 80))],
                spans=[],
                source_block_ids=[],
            )
        )
    return DocumentTree(
        document_id="test_doc",
        filename="test_agreement.pdf",
        sha256_hash="dummy",
        file_size_bytes=1000,
        page_count=2,
        parsing_status=ParsingStatus.TEXT_AVAILABLE,
        pages=[PageData(page_number=1, width=595.0, height=842.0), PageData(page_number=2, width=595.0, height=842.0)],
        clauses=clauses,
    )


@pytest.fixture
def detector():
    return ContradictionDetector()


def test_golden_case_a_notice_period_conflict(detector):
    # Case A:
    # Clause 4: "Tenant shall provide 30 days notice."
    # Clause 7: "Tenant shall provide 60 days notice."
    # Expected: CONFIRMED_CONFLICT with both source locations.
    doc = make_test_tree([
        ("c_4", "4", "The Tenant shall provide 30 days notice prior to vacating.", 1),
        ("c_7", "7", "The Tenant shall provide 60 days notice prior to termination.", 1),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 1
    conflict = res.findings[0]
    assert conflict.status == ContradictionStatus.CONFIRMED_CONFLICT
    assert conflict.subject == ContradictionSubject.NOTICE_PERIOD
    assert conflict.actor == ContradictionActor.TENANT
    assert "30" in conflict.value_a or "30" in conflict.value_b
    assert "60" in conflict.value_a or "60" in conflict.value_b
    assert conflict.source_a.clause_number in ("4", "7")
    assert conflict.source_b.clause_number in ("4", "7")
    # Verify non-adjudicating language
    assert "overrides" not in conflict.explanation.lower()
    assert "invalid" not in conflict.explanation.lower()


def test_golden_case_b_actor_asymmetry(detector):
    # Case B:
    # Clause 4: "Tenant shall provide 30 days notice."
    # Clause 7: "Landlord shall provide 60 days notice."
    # Expected: NO_CONFLICT because actors differ (valid asymmetry).
    doc = make_test_tree([
        ("c_4", "4", "The Tenant shall provide 30 days notice.", 1),
        ("c_7", "7", "The Landlord shall provide 60 days notice.", 1),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    # There should be a NO_CONFLICT finding explaining actor asymmetry
    no_conflicts = [f for f in res.findings if f.status == ContradictionStatus.NO_CONFLICT]
    assert len(no_conflicts) >= 1
    assert "different parties" in no_conflicts[0].explanation.lower() or "asymmetry" in no_conflicts[0].explanation.lower()


def test_golden_case_c_identical_values(detector):
    # Case C:
    # Clause 4: "Tenant shall provide 30 days notice."
    # Clause 7: "Tenant shall provide 30 days notice."
    # Expected: NO_CONFLICT.
    doc = make_test_tree([
        ("c_4", "4", "The Tenant shall provide 30 days notice before vacating.", 1),
        ("c_7", "7", "The Tenant shall provide 30 days notice before termination.", 2),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    affirmation = [f for f in res.findings if f.status == ContradictionStatus.NO_CONFLICT]
    assert len(affirmation) >= 1
    assert "same value" in affirmation[0].explanation.lower() or "agree" in affirmation[0].explanation.lower()


def test_golden_case_d_different_temporal_scope(detector):
    # Case D:
    # Clause 4: "Tenant shall provide 30 days notice during the initial term."
    # Clause 7: "Tenant shall provide 60 days notice after renewal."
    # Expected: NO_CONFLICT (different temporal/conditional scopes).
    doc = make_test_tree([
        ("c_4", "4", "Tenant shall provide 30 days notice during the initial term.", 1),
        ("c_7", "7", "Tenant shall provide 60 days notice after renewal.", 2),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    scope_findings = [f for f in res.findings if f.status == ContradictionStatus.NO_CONFLICT]
    assert len(scope_findings) >= 1
    assert "scope" in scope_findings[0].explanation.lower() or "conditions" in scope_findings[0].explanation.lower()
