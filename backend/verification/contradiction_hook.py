from typing import List, Optional
from pydantic import BaseModel
from backend.models.verification import AtomicClaim


class ContradictionResult(BaseModel):
    """Result from contradiction evaluation hook."""

    status: str = "NOT_EVALUATED"
    reason: Optional[str] = None


class ContradictionHook:
    """Interface hook for future Phase 6 contradiction engine (Correction 2).

    Phase 4 maintains a strict boundary: contradiction reasoning is sealed for Phase 6.
    Always returns NOT_EVALUATED unless explicitly configured in future phases.
    """

    def check(
        self,
        claim: AtomicClaim,
        context_claims: List[AtomicClaim],
    ) -> ContradictionResult:
        return ContradictionResult(
            status="NOT_EVALUATED",
            reason="Phase 6 contradiction intelligence engine sealed.",
        )
