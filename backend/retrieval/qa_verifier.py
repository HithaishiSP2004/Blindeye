import re
import uuid
from typing import List, Optional
from pydantic import BaseModel
from backend.models.qa import AnswerStatus, EvidenceCitation
from backend.models.verification import (
    AtomicClaim,
    ClaimSource,
    ClaimTag,
    VerificationStatus,
)
from backend.verification.deterministic_checker import DeterministicChecker
from backend.verification.semantic_evaluator import (
    DeterministicMockSemanticEvaluator,
    GeminiSemanticEvaluator,
    SemanticEvaluator,
)


class QAVerificationResult(BaseModel):
    """Result of passing a Q&A candidate through the formal verification contract."""

    status: AnswerStatus
    is_verified: bool
    reason_code: str
    atomic_claim: Optional[AtomicClaim] = None


class QAVerifier:
    """Formal Q&A verification adapter gating all answers before presentation.

    Adheres strictly to Phase 5 Corrections:
    - Q&A verification contract converts question + candidate evidence into AtomicClaim (Correction 3).
    - Existing Phase 4 DeterministicChecker and SemanticEvaluator are invoked (no duplicate logic).
    - The LLM does NOT decide whether support exists (Correction 3 & 4).
    - Multiple candidate passages produce AMBIGUOUS, not contradiction (Correction 5).
    - Unverified or conflicting evidence produces UNRESOLVED, never hallucinated answers (Correction 9 & 28).
    """

    def __init__(
        self,
        deterministic_checker: Optional[DeterministicChecker] = None,
        semantic_evaluator: Optional[SemanticEvaluator] = None,
    ):
        self.deterministic_checker = deterministic_checker or DeterministicChecker()
        self.semantic_evaluator = semantic_evaluator or GeminiSemanticEvaluator()

    def construct_atomic_claim(
        self,
        question: str,
        candidate_evidence: List[EvidenceCitation],
        candidate_answer: Optional[str] = None,
    ) -> AtomicClaim:
        """Construct an AtomicClaim from question and retrieved evidence."""
        claim_id = f"qa_claim_{uuid.uuid4().hex[:8]}"
        primary_quote = candidate_evidence[0].quote if candidate_evidence else ""

        # Determine value to test for support from candidate_answer
        test_val = candidate_answer or ""
        if candidate_answer:
            val_match_ans = re.search(r"(?:Rs\.?\s*[\d,]+|[\d]+\s*months?|[\d]+\s*days?)", candidate_answer, re.IGNORECASE)
            inferred_val = val_match_ans.group(0) if val_match_ans else test_val
        else:
            val_match = re.search(r"(?:Rs\.?\s*[\d,]+|[\d]+\s*months?|[\d]+\s*days?)", primary_quote, re.IGNORECASE)
            inferred_val = val_match.group(0) if val_match else primary_quote[:60]

        # Infer unit from claim and quote context
        unit = None
        check_text = (inferred_val + " " + (candidate_answer or "") + " " + primary_quote).lower()
        if "rs" in check_text or "rupees" in check_text or "/-" in check_text:
            unit = "INR"
        elif "month" in check_text:
            unit = "MONTHS"
        elif "day" in check_text:
            unit = "DAYS"


        claim = AtomicClaim(
            claim_id=claim_id,
            claim_text=candidate_answer or question,
            field_name="qa_query",
            subject=question,
            predicate="asserts",
            value=inferred_val or primary_quote[:60],
            unit=unit,
            status=VerificationStatus.UNRESOLVED,
            exact_quotes=[c.quote for c in candidate_evidence],
            bounding_boxes=[c.bbox for c in candidate_evidence if c.bbox],
        )

        if candidate_evidence:
            first_cit = candidate_evidence[0]
            claim.source = ClaimSource(
                clause_id=first_cit.clause_id,
                clause_number=first_cit.clause_number,
                page=first_cit.page,
                quote=first_cit.quote,
                bbox=first_cit.bbox,
            )

        return claim

    async def verify(
        self,
        question: str,
        candidate_evidence: List[EvidenceCitation],
        candidate_answer: Optional[str] = None,
        is_ambiguous_retrieval: bool = False,
    ) -> QAVerificationResult:
        """Pass candidate question + evidence through the verification ladder."""
        # 1. No evidence available -> NOT_FOUND (Correction 2 & 4)
        if not candidate_evidence:
            return QAVerificationResult(
                status=AnswerStatus.NOT_FOUND,
                is_verified=False,
                reason_code="NO_SUPPORTING_PASSAGE",
            )

        # 2. Ambiguous multi-candidate retrieval -> AMBIGUOUS (Correction 5)
        if is_ambiguous_retrieval:
            return QAVerificationResult(
                status=AnswerStatus.AMBIGUOUS,
                is_verified=False,
                reason_code="MULTIPLE_PLAUSIBLE_CANDIDATES",
            )

        # 3. Construct atomic candidate claim (Correction 3)
        atomic_claim = self.construct_atomic_claim(question, candidate_evidence, candidate_answer)
        primary_quote = candidate_evidence[0].quote

        # 4. Deterministic support check
        is_supported, reason_code, method = self.deterministic_checker.check_claim_support(
            atomic_claim,
            primary_quote,
        )

        if is_supported is True:
            atomic_claim.status = VerificationStatus.VERIFIED
            atomic_claim.claim_tag = ClaimTag.EXPLICIT
            return QAVerificationResult(
                status=AnswerStatus.ANSWERED,
                is_verified=True,
                reason_code=reason_code,
                atomic_claim=atomic_claim,
            )

        if is_supported is False:
            # Deterministic conflict detected
            atomic_claim.status = VerificationStatus.UNSUPPORTED
            return QAVerificationResult(
                status=AnswerStatus.UNRESOLVED,
                is_verified=False,
                reason_code=reason_code,
                atomic_claim=atomic_claim,
            )

        # 5. Deterministic check was inconclusive -> Semantic Evaluator
        try:
            sem_res = await self.semantic_evaluator.evaluate(atomic_claim, primary_quote)
            if sem_res.decision == "SUPPORTED":
                atomic_claim.status = VerificationStatus.VERIFIED
                atomic_claim.claim_tag = ClaimTag.EXPLICIT
                return QAVerificationResult(
                    status=AnswerStatus.ANSWERED,
                    is_verified=True,
                    reason_code=sem_res.reason_code,
                    atomic_claim=atomic_claim,
                )
            else:
                atomic_claim.status = VerificationStatus.UNRESOLVED
                return QAVerificationResult(
                    status=AnswerStatus.UNRESOLVED,
                    is_verified=False,
                    reason_code=sem_res.reason_code,
                    atomic_claim=atomic_claim,
                )
        except Exception as exc:
            atomic_claim.status = VerificationStatus.UNRESOLVED
            return QAVerificationResult(
                status=AnswerStatus.UNRESOLVED,
                is_verified=False,
                reason_code=f"SEMANTIC_EVAL_ERROR: {str(exc)}",
                atomic_claim=atomic_claim,
            )
