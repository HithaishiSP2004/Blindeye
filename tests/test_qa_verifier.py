import pytest
from backend.models.document import BoundingBox
from backend.models.qa import AnswerStatus, EvidenceCitation
from backend.models.verification import ClaimTag, VerificationStatus
from backend.retrieval.qa_verifier import QAVerifier
from backend.verification.deterministic_checker import DeterministicChecker
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator


@pytest.fixture
def verifier():
    return QAVerifier(
        deterministic_checker=DeterministicChecker(),
        semantic_evaluator=DeterministicMockSemanticEvaluator(),
    )


@pytest.mark.asyncio
async def test_qa_verifier_supported_claim(verifier):
    cit = EvidenceCitation(
        clause_id="c_2_1",
        clause_number="2.1",
        page=1,
        quote="Rs. 35,000/- (Rupees Thirty Five Thousand) per month",
        bbox=BoundingBox(page=1, x0=50, y0=100, x1=200, y1=120),
    )
    res = await verifier.verify(
        question="What is the monthly rent?",
        candidate_evidence=[cit],
        candidate_answer="The monthly rent is Rs. 35,000/- per month.",
    )
    assert res.is_verified is True
    assert res.status == AnswerStatus.ANSWERED
    assert res.atomic_claim is not None
    assert res.atomic_claim.status == VerificationStatus.VERIFIED
    assert res.atomic_claim.claim_tag == ClaimTag.EXPLICIT


@pytest.mark.asyncio
async def test_qa_verifier_empty_evidence_not_found(verifier):
    res = await verifier.verify(
        question="What is the property address?",
        candidate_evidence=[],
    )
    assert res.is_verified is False
    assert res.status == AnswerStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_qa_verifier_ambiguous_retrieval(verifier):
    cit1 = EvidenceCitation(
        clause_id="c1",
        clause_number="1",
        page=1,
        quote="First term mentions notice 30 days",
    )
    cit2 = EvidenceCitation(
        clause_id="c2",
        clause_number="2",
        page=1,
        quote="Second term mentions notice 60 days",
    )
    # Correction 5: multiple candidate passages produce AMBIGUOUS, not contradiction
    res = await verifier.verify(
        question="What is the notice period?",
        candidate_evidence=[cit1, cit2],
        is_ambiguous_retrieval=True,
    )
    assert res.is_verified is False
    assert res.status == AnswerStatus.AMBIGUOUS


@pytest.mark.asyncio
async def test_qa_verifier_value_conflict_unresolved(verifier):
    # Candidate asserts 50,000 but source text clearly says 35,000
    cit = EvidenceCitation(
        clause_id="c_2_1",
        clause_number="2.1",
        page=1,
        quote="Rs. 35,000/- per month",
    )
    res = await verifier.verify(
        question="What is the monthly rent?",
        candidate_evidence=[cit],
        candidate_answer="Rs. 50,000/- per month",
    )
    assert res.is_verified is False
    assert res.status == AnswerStatus.UNRESOLVED
