from abc import ABC, abstractmethod
import logging
from typing import Optional
from pydantic import BaseModel, Field
from backend.core.config import settings
from backend.models.verification import AtomicClaim

logger = logging.getLogger(__name__)


class SemanticEvaluationResult(BaseModel):
    """Result of semantic entailment analysis between claim and source passage."""

    decision: str = Field(..., description="'SUPPORTED' | 'NOT_SUPPORTED' | 'UNRESOLVED'")
    reason_code: str = Field(..., description="Machine-readable rationale code")
    rationale: Optional[str] = Field(default=None, description="Brief explanation")


class SemanticEvaluator(ABC):
    """Abstract interface for evaluating semantic support between a claim and source passage."""

    @abstractmethod
    async def evaluate(self, claim: AtomicClaim, source_text: str) -> SemanticEvaluationResult:
        """Determine whether source_text semantically entails claim."""
        pass


class DeterministicMockSemanticEvaluator(SemanticEvaluator):
    """Deterministic offline evaluator for testing and repeatable evaluation (Correction 9)."""

    async def evaluate(self, claim: AtomicClaim, source_text: str) -> SemanticEvaluationResult:
        if not source_text or not source_text.strip():
            return SemanticEvaluationResult(
                decision="NOT_SUPPORTED",
                reason_code="EMPTY_SOURCE_TEXT",
                rationale="Source text is empty.",
            )

        field = claim.field_name
        src_lower = source_text.lower()
        val_lower = (claim.value or "").lower()

        # Maintenance responsibility semantic entailment
        if field == "maintenance_responsibility":
            if "minor repairs" in src_lower or "structural repairs" in src_lower or "borne by" in src_lower:
                return SemanticEvaluationResult(
                    decision="SUPPORTED",
                    reason_code="SEMANTIC_SUPPORT",
                    rationale="Source passage establishes maintenance liability distribution.",
                )
            return SemanticEvaluationResult(
                decision="NOT_SUPPORTED",
                reason_code="SEMANTIC_NON_SUPPORT",
                rationale="Passage does not establish maintenance terms.",
            )

        # Check keyword presence
        tokens = [t for t in val_lower.split() if len(t) > 3]
        matches = [t for t in tokens if t in src_lower]
        if len(tokens) > 0 and (len(matches) / len(tokens)) >= 0.5:
            return SemanticEvaluationResult(
                decision="SUPPORTED",
                reason_code="SEMANTIC_SUPPORT",
                rationale="Majority of substantive semantic claim tokens match source.",
            )

        return SemanticEvaluationResult(
            decision="NOT_SUPPORTED",
            reason_code="SEMANTIC_NON_SUPPORT",
            rationale="Passage does not semantically entail the claim.",
        )


class GeminiSemanticEvaluator(SemanticEvaluator):
    """Production semantic evaluator powered by Google Gemini official SDK."""

    async def evaluate(self, claim: AtomicClaim, source_text: str) -> SemanticEvaluationResult:
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key in ("mock", "test_key", "your_gemini_api_key_here") or api_key.startswith("test"):
            # Defer to deterministic mock if no live API key
            mock = DeterministicMockSemanticEvaluator()
            return await mock.evaluate(claim, source_text)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            prompt = f"""You are a precision legal verification engine.
Evaluate whether the following SOURCE PASSAGE semantically supports the CLAIM.

RULES:
1. Answer ONLY based on the provided source text.
2. DO NOT assume customary legal terms or invent external facts.
3. Decision must be strictly 'SUPPORTED' or 'NOT_SUPPORTED'.
4. Reason code should be 'SEMANTIC_SUPPORT', 'VALUE_CONFLICT', or 'INSUFFICIENT_EVIDENCE'.

CLAIM:
Subject: {claim.subject}
Actor: {claim.actor}
Predicate: {claim.predicate}
Value: {claim.value}

SOURCE PASSAGE:
"{source_text}"
"""

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SemanticEvaluationResult,
                temperature=0.0,
            )

            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                if isinstance(response.parsed, SemanticEvaluationResult):
                    return response.parsed
                return SemanticEvaluationResult.model_validate(response.parsed)

            clean_text = (response.text or "").strip()
            return SemanticEvaluationResult.model_validate_json(clean_text)

        except Exception as exc:
            logger.warning(f"Semantic evaluation failed: {exc}. Marking UNRESOLVED.", exc_info=True)
            return SemanticEvaluationResult(
                decision="UNRESOLVED",
                reason_code="SEMANTIC_EVALUATION_FAILED",
                rationale=str(exc),
            )
