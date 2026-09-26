import pytest
from backend.models.qa import AnswerStatus, EvidenceCitation
from backend.retrieval.constrained_generator import (
    DeterministicGenerator,
    GeminiGenerator,
)


@pytest.fixture
def deterministic_gen():
    return DeterministicGenerator()


@pytest.fixture
def gemini_gen():
    return GeminiGenerator()


@pytest.mark.asyncio
async def test_deterministic_generator_answered(deterministic_gen):
    cit = EvidenceCitation(
        clause_id="c_2_1",
        clause_number="2.1",
        page=1,
        quote="Rs. 35,000/- per month",
    )
    ans = await deterministic_gen.generate_answer(
        question="What is the rent?",
        evidence=[cit],
        status=AnswerStatus.ANSWERED,
    )
    assert "Clause 2.1: Rs. 35,000/- per month" == ans


@pytest.mark.asyncio
async def test_deterministic_generator_not_found(deterministic_gen):
    ans = await deterministic_gen.generate_answer(
        question="What is the property address?",
        evidence=[],
        status=AnswerStatus.NOT_FOUND,
    )
    assert "does not provide a property address" in ans


@pytest.mark.asyncio
async def test_deterministic_generator_refused(deterministic_gen):
    ans = await deterministic_gen.generate_answer(
        question="Is this legal?",
        evidence=[],
        status=AnswerStatus.REFUSED,
        refusal_reason="Legal advice cannot be provided.",
    )
    assert "Legal advice cannot be provided." == ans


@pytest.mark.asyncio
async def test_gemini_generator_fallback_without_live_key(gemini_gen):
    # Without live API key, GeminiGenerator cleanly falls back to deterministic path
    cit = EvidenceCitation(
        clause_id="c_1",
        clause_number="1",
        page=1,
        quote="The term shall be 11 months",
    )
    ans = await gemini_gen.generate_answer(
        question="How long is the agreement?",
        evidence=[cit],
        status=AnswerStatus.ANSWERED,
    )
    assert "11 months" in ans
