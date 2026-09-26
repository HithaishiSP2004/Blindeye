import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.core.config import settings
from backend.models.qa import AnswerStatus, EvidenceCitation
from backend.retrieval.constrained_generator import GeminiGenerator
from backend.verification.semantic_evaluator import GeminiSemanticEvaluator, AtomicClaim


def test_settings_models_cascade():
    """Verify that settings correctly cascades primary and fallback models."""
    cascade = settings.gemini_models_cascade
    assert len(cascade) >= 3
    assert cascade[0] == "gemini-3.8-flash"
    assert "gemini-3.7-flash" in cascade
    assert "gemini-3.6-flash" in cascade
    assert settings.gemini_fallback_models_list == ["gemini-3.7-flash", "gemini-3.6-flash"]


@pytest.mark.asyncio
async def test_gemini_generator_fallback_to_gemini_37(monkeypatch):
    """Test that GeminiGenerator falls back to Gemini 3.7 Flash if 3.8 fails."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "live_fake_key_12345")
    
    gen = GeminiGenerator()
    called_models = []

    mock_response = MagicMock()
    mock_response.text = "The monthly rent is Rs. 28,000/- as per Clause 1."

    async def mock_generate_content(model, contents, config):
        called_models.append(model)
        if model == "gemini-3.8-flash":
            raise Exception("Model gemini-3.8-flash overloaded / 503")
        return mock_response

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)

    with patch("google.genai.Client", return_value=mock_client):
        cit = EvidenceCitation(
            clause_id="c_1",
            clause_number="1",
            page=1,
            quote="The rent shall be Rs. 28,000/- per month.",
        )
        answer = await gen.generate_answer(
            question="What is the rent?",
            evidence=[cit],
            status=AnswerStatus.ANSWERED,
        )

        assert "Rs. 28,000/-" in answer
        assert called_models[0] == "gemini-3.8-flash"
        assert called_models[1] == "gemini-3.7-flash"


@pytest.mark.asyncio
async def test_gemini_generator_fallback_to_gemini_36(monkeypatch):
    """Test that GeminiGenerator falls back to Gemini 3.6 Flash if 3.8 and 3.7 fail."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "live_fake_key_12345")
    
    gen = GeminiGenerator()
    called_models = []

    mock_response = MagicMock()
    mock_response.text = "Answer generated via Gemini 3.6 Flash."

    async def mock_generate_content(model, contents, config):
        called_models.append(model)
        if model in ("gemini-3.8-flash", "gemini-3.7-flash"):
            raise Exception(f"Model {model} unavailable / rate limited")
        return mock_response

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)

    with patch("google.genai.Client", return_value=mock_client):
        cit = EvidenceCitation(
            clause_id="c_1",
            clause_number="1",
            page=1,
            quote="The rent shall be Rs. 28,000/- per month.",
        )
        answer = await gen.generate_answer(
            question="What is the rent?",
            evidence=[cit],
            status=AnswerStatus.ANSWERED,
        )

        assert answer == "Answer generated via Gemini 3.6 Flash."
        assert called_models == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]


@pytest.mark.asyncio
async def test_gemini_generator_complete_fallback_to_deterministic(monkeypatch):
    """Test that if all Gemini models fail, generator falls back to deterministic without crash."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "live_fake_key_12345")
    
    gen = GeminiGenerator()

    async def mock_generate_content(model, contents, config):
        raise Exception(f"Model {model} failure")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)

    with patch("google.genai.Client", return_value=mock_client):
        cit = EvidenceCitation(
            clause_id="c_1",
            clause_number="1",
            page=1,
            quote="The rent shall be Rs. 28,000/- per month.",
        )
        answer = await gen.generate_answer(
            question="What is the rent?",
            evidence=[cit],
            status=AnswerStatus.ANSWERED,
        )

        assert "Clause 1: The rent shall be Rs. 28,000/- per month." == answer
