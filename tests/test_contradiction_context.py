import pytest
from backend.contradiction.detector import ContradictionDetector
from backend.models.contradiction import ContradictionActor, ContradictionStatus, ContradictionSubject
from backend.models.document import BoundingBox, Clause, DocumentTree, PageData, ParsingStatus


def make_test_tree(clauses_data):
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
                bounding_boxes=[BoundingBox(page=pg, x0=50.0, y0=50.0, x1=350.0, y1=80.0)],
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


def test_unknown_actor_yields_insufficient_context(detector):
    # Hardening Correction 2 & 6:
    # Clause A: "Notice shall be 30 days."
    # Clause B: "Notice shall be 60 days."
    # Without party attribution, must yield INSUFFICIENT_CONTEXT (never automatic NO_CONFLICT).
    doc = make_test_tree([
        ("c_1", "1", "A notice of 30 days shall be given prior to vacating.", 1),
        ("c_2", "2", "Notice shall be 60 days before termination.", 1),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    insufficient = [f for f in res.findings if f.status == ContradictionStatus.INSUFFICIENT_CONTEXT]
    assert len(insufficient) >= 1
    assert insufficient[0].actor == ContradictionActor.UNKNOWN
    assert "party is not explicitly determinable" in insufficient[0].explanation.lower() or "obligated party" in insufficient[0].explanation.lower()


def test_both_mutual_vs_specific_actor_yields_insufficient_context(detector):
    # Hardening Correction 4:
    # "Both parties shall provide 30 days notice." vs "Tenant shall provide 60 days notice."
    # Conservative ambiguity: yields INSUFFICIENT_CONTEXT
    doc = make_test_tree([
        ("c_1", "1", "Both parties shall provide 30 days notice.", 1),
        ("c_2", "2", "Tenant shall provide 60 days notice prior to vacating.", 1),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    insufficient = [f for f in res.findings if f.status == ContradictionStatus.INSUFFICIENT_CONTEXT]
    assert len(insufficient) >= 1
    assert "both parties" in insufficient[0].explanation.lower()


def test_rent_repeated_identically_no_conflict(detector):
    # Rent ₹35,000 stated in main body and schedule -> NO_CONFLICT
    doc = make_test_tree([
        ("c_2", "2", "The monthly rent shall be Rs. 35,000/- per month.", 1),
        ("c_sched", "Schedule", "Monthly rent of Rs. 35,000 payable on 5th.", 2),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 0
    no_conflict = [f for f in res.findings if f.status == ContradictionStatus.NO_CONFLICT]
    assert len(no_conflict) >= 1
    assert "agree" in no_conflict[0].explanation.lower() or "same value" in no_conflict[0].explanation.lower()


def test_conflicting_rent_same_tenant_confirmed_conflict(detector):
    # Clause 2 says ₹35,000, Clause 12 says ₹42,000 -> CONFIRMED_CONFLICT
    doc = make_test_tree([
        ("c_2", "2", "The monthly rent is Rs. 35,000/-.", 1),
        ("c_12", "12", "Tenant agrees to pay monthly rent of Rs. 42,000/-.", 2),
    ])
    res = detector.detect_contradictions(doc)
    assert res.total_conflicts == 1
    conflict = res.findings[0]
    assert conflict.status == ContradictionStatus.CONFIRMED_CONFLICT
    assert conflict.subject == ContradictionSubject.MONTHLY_RENT
    assert "35000" in conflict.value_a or "35000" in conflict.value_b or "35,000" in conflict.value_a or "35,000" in conflict.value_b
    assert "42000" in conflict.value_a or "42000" in conflict.value_b or "42,000" in conflict.value_a or "42,000" in conflict.value_b
