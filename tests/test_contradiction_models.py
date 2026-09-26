import pytest
from pydantic import ValidationError
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionEvidence,
    ContradictionFinding,
    ContradictionResponse,
    ContradictionStatus,
    ContradictionSubject,
)
from backend.models.document import BoundingBox


def test_contradiction_status_values():
    # Only factual statuses allowed, strictly NO risk or legal judgment terms
    valid_statuses = {s.value for s in ContradictionStatus}
    assert valid_statuses == {
        "CONFIRMED_CONFLICT",
        "NO_CONFLICT",
        "INSUFFICIENT_CONTEXT",
        "UNRESOLVED",
    }
    assert "HIGH_RISK" not in valid_statuses
    assert "LOW_RISK" not in valid_statuses
    assert "LEGALLY_INVALID" not in valid_statuses


def test_contradiction_finding_structure():
    ev_a = ContradictionEvidence(
        clause_id="clause_4",
        clause_number="4",
        page_number=2,
        exact_quote="Tenant shall provide 30 days notice.",
        bounding_boxes=[BoundingBox(page=2, x0=50.0, y0=100.0, x1=300.0, y1=115.0)],
    )
    ev_b = ContradictionEvidence(
        clause_id="clause_7",
        clause_number="7",
        page_number=2,
        exact_quote="Tenant shall provide 60 days notice.",
        bounding_boxes=[BoundingBox(page=2, x0=50.0, y0=250.0, x1=300.0, y1=265.0)],
    )

    finding = ContradictionFinding(
        finding_id="cf_notice_001",
        status=ContradictionStatus.CONFIRMED_CONFLICT,
        subject=ContradictionSubject.NOTICE_PERIOD,
        actor=ContradictionActor.TENANT,
        value_a="30",
        value_b="60",
        unit="days",
        claim_a="Tenant notice period is 30 days",
        claim_b="Tenant notice period is 60 days",
        source_a=ev_a,
        source_b=ev_b,
        explanation="The agreement contains two statements assigning different notice periods to the tenant.",
    )

    assert finding.finding_id == "cf_notice_001"
    assert finding.status == ContradictionStatus.CONFIRMED_CONFLICT
    assert finding.actor == ContradictionActor.TENANT
    assert finding.source_a.exact_quote == "Tenant shall provide 30 days notice."
    assert finding.source_b.exact_quote == "Tenant shall provide 60 days notice."


def test_contradiction_response_contract():
    res = ContradictionResponse(
        findings=[],
        total_conflicts=0,
        evaluation_summary="No conflicting statements detected among analyzed covenants.",
    )
    assert res.total_conflicts == 0
    assert len(res.findings) == 0
