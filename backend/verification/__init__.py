"""Phase 4: Verification and Refusal Core."""

from backend.verification.claim_decomposer import decompose_agreement, decompose_field_to_atomic_claim
from backend.verification.contradiction_hook import ContradictionHook, ContradictionResult
from backend.verification.deterministic_checker import DeterministicChecker
from backend.verification.refusal_engine import RefusalEngine
from backend.verification.semantic_evaluator import (
    DeterministicMockSemanticEvaluator,
    GeminiSemanticEvaluator,
    SemanticEvaluationResult,
    SemanticEvaluator,
)
from backend.verification.verification_gate import VerificationGate

__all__ = [
    "VerificationGate",
    "DeterministicChecker",
    "SemanticEvaluator",
    "DeterministicMockSemanticEvaluator",
    "GeminiSemanticEvaluator",
    "SemanticEvaluationResult",
    "ContradictionHook",
    "ContradictionResult",
    "RefusalEngine",
    "decompose_agreement",
    "decompose_field_to_atomic_claim",
]
