from abc import ABC, abstractmethod
import logging
from typing import List, Optional
from backend.core.config import settings
from backend.models.qa import AnswerStatus, EvidenceCitation

logger = logging.getLogger(__name__)


class AnswerGenerator(ABC):
    """Abstract interface for constrained answer generation."""

    @abstractmethod
    async def generate_answer(
        self,
        question: str,
        evidence: List[EvidenceCitation],
        status: AnswerStatus,
        refusal_reason: Optional[str] = None,
    ) -> str:
        """Generate human-readable answer grounded strictly in verified evidence."""
        pass


class DeterministicGenerator(AnswerGenerator):
    """Deterministic, offline generator for canonical facts and verbatim clause quotes.

    Enforces Phase 5 Corrections:
    - Canonical factual questions resolve deterministically without Gemini (Correction 6).
    - Source quotes sliced directly from DocumentTree (Correction 10).
    - NOT_FOUND and AMBIGUOUS have strict, honest phrasing (Correction 26 & 27).
    - Zero dependencies on API keys or external services.
    """

    async def generate_answer(
        self,
        question: str,
        evidence: List[EvidenceCitation],
        status: AnswerStatus,
        refusal_reason: Optional[str] = None,
    ) -> str:
        if status == AnswerStatus.REFUSED:
            return refusal_reason or (
                "This request is outside the scope of document verification. "
                "Antigravity answers only factual questions regarding the contents of the agreement."
            )

        if status == AnswerStatus.NOT_FOUND:
            # Generate honest NOT_FOUND response
            q_lower = question.lower()
            if "address" in q_lower or "property" in q_lower:
                return "The agreement does not provide a property address."
            if "lock" in q_lower:
                return "The agreement does not mention a lock-in period."
            if "penalty" in q_lower or "late" in q_lower:
                return "The agreement does not specify a late payment penalty."
            if "phone" in q_lower or "contact" in q_lower or "email" in q_lower:
                return "The agreement does not contain contact details for the parties."
            if "pin" in q_lower or "postal" in q_lower:
                return "The agreement does not contain a PIN code."
            return "The agreement does not contain information to answer this question."

        if status == AnswerStatus.AMBIGUOUS:
            return (
                "The agreement contains multiple plausible provisions on this subject that cannot be "
                "unambiguously resolved from the text alone."
            )

        if status == AnswerStatus.UNRESOLVED:
            return "The available passage does not provide enough verified support for a reliable answer."

        # ANSWERED status: express verified evidence
        if not evidence:
            return "The agreement does not contain supporting evidence for this question."

        # If evidence citation has a clean quote, format cleanly
        cit = evidence[0]
        clause_prefix = f"Clause {cit.clause_number}: " if cit.clause_number else ""
        return f"{clause_prefix}{cit.quote}"


class GeminiGenerator(AnswerGenerator):
    """Production generator that uses Google Gemini official SDK with strict evidence-only input.

    Enforces Phase 5 Corrections:
    - Model is configurable via GEMINI_MODEL (default: gemini-3.8-flash) (Correction 1).
    - Gemini receives VERIFIED EVIDENCE ONLY, never full DocumentTree (Correction 8).
    - Gemini cannot independently search the document or invent source locations (Correction 8).
    - If Gemini fails or API key is missing, falls back seamlessly to DeterministicGenerator (Correction 7).
    """

    def __init__(self, fallback_generator: Optional[DeterministicGenerator] = None):
        self.fallback = fallback_generator or DeterministicGenerator()

    async def generate_answer(
        self,
        question: str,
        evidence: List[EvidenceCitation],
        status: AnswerStatus,
        refusal_reason: Optional[str] = None,
    ) -> str:
        # If not an ANSWERED status, defer to deterministic templates
        if status != AnswerStatus.ANSWERED or not evidence:
            return await self.fallback.generate_answer(question, evidence, status, refusal_reason)

        api_key = settings.GEMINI_API_KEY
        # If no valid API key, use deterministic generator (Correction 6 & 7)
        if not api_key or api_key in ("mock", "test_key", "your_gemini_api_key_here") or api_key.startswith("test"):
            return await self.fallback.generate_answer(question, evidence, status, refusal_reason)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # EVIDENCE-ONLY INPUT (Correction 8): Sent strictly normalized question + verified quote
            evidence_quotes = "\n".join(
                f"[Clause {c.clause_number or 'N/A'}, Page {c.page}]: \"{c.quote}\"" for c in evidence
            )

            prompt = f"""You are an evidence-grounded legal assistant for residential agreements.
Your task is to answer the user's question concisely and accurately using ONLY the provided verified document evidence.

CRITICAL INSTRUCTIONS:
1. Base your answer ENTIRELY and EXCLUSIVELY on the verified evidence below.
2. DO NOT assume, extrapolate, or introduce facts not stated in the evidence.
3. Keep the answer direct, professional, and factual (1-2 sentences).
4. DO NOT provide legal advice or comment on statutory enforceability.

QUESTION:
{question}

VERIFIED DOCUMENT EVIDENCE:
{evidence_quotes}

ANSWER:"""

            models_to_try = settings.gemini_models_cascade
            for model_name in models_to_try:
                try:
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            max_output_tokens=256,
                        ),
                    )

                    generated_text = (response.text or "").strip()
                    if generated_text:
                        return generated_text

                except Exception as exc:
                    logger.warning(
                        f"Gemini generation failed on model '{model_name}': {exc}. Trying next fallback model if available."
                    )

            logger.warning(f"All live Gemini models ({models_to_try}) failed, falling back to deterministic.")

        except Exception as exc:
            logger.warning(f"Gemini client setup or generation failed, falling back to deterministic: {exc}")

        # Fallback to deterministic generator if all LLMs fail
        return await self.fallback.generate_answer(question, evidence, status, refusal_reason)
