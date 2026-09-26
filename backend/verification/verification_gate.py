import logging
from typing import List, Optional
from backend.models.document import DocumentTree
from backend.models.extraction import ExtractionStatus, StructuredAgreement
from backend.models.verification import (
    AtomicClaim,
    ClaimTag,
    DocumentVerificationResult,
    RefusalCategory,
    VerificationStatus,
    VerificationSummary,
)
from backend.verification.claim_decomposer import decompose_agreement
from backend.verification.contradiction_hook import ContradictionHook
from backend.verification.deterministic_checker import DeterministicChecker
from backend.verification.refusal_engine import RefusalEngine
from backend.verification.semantic_evaluator import (
    DeterministicMockSemanticEvaluator,
    GeminiSemanticEvaluator,
    SemanticEvaluator,
)

logger = logging.getLogger(__name__)


class VerificationGate:
    """The central authority for verifying contractual claims against physical evidence.

    Enforces all Phase 4 corrections:
    - UNRESOLVED maps to ClaimTag = None (Correction 1).
    - Contradiction hook remains interface only (Correction 2).
    - Prompt injection is ignored and does NOT reject legitimate documents (Correction 3).
    - Semantic evaluator runs only when deterministic matching is insufficient (Correction 7).
    - No confidence_tier or percentage scoring (Correction 8 & 10).
    - Full DocumentTree is not returned in public verification response (Correction 5).
    """

    def __init__(
        self,
        deterministic_checker: Optional[DeterministicChecker] = None,
        semantic_evaluator: Optional[SemanticEvaluator] = None,
        contradiction_hook: Optional[ContradictionHook] = None,
        refusal_engine: Optional[RefusalEngine] = None,
    ):
        self.deterministic_checker = deterministic_checker or DeterministicChecker()
        self.semantic_evaluator = semantic_evaluator or GeminiSemanticEvaluator()
        self.contradiction_hook = contradiction_hook or ContradictionHook()
        self.refusal_engine = refusal_engine or RefusalEngine()

    async def verify_agreement(
        self,
        structured_agreement: StructuredAgreement,
        document_tree: DocumentTree,
    ) -> DocumentVerificationResult:
        doc_id = document_tree.document_id
        filename = document_tree.filename

        # 1. Document-level refusal check (e.g. scanned PDF without text layer)
        doc_refusal = self.refusal_engine.check_document_refusal(document_tree)
        if doc_refusal == RefusalCategory.UNREADABLE_DOCUMENT:
            claims = decompose_agreement(structured_agreement, doc_id)
            for c in claims:
                c.status = VerificationStatus.REFUSED
                c.claim_tag = None
                c.is_refused = True
                c.refusal_category = RefusalCategory.UNREADABLE_DOCUMENT
            summary = VerificationSummary(total=len(claims), refused=len(claims))
            return DocumentVerificationResult(
                document_id=doc_id,
                filename=filename,
                document_status="UNREADABLE_DOCUMENT",
                refusal_reason="Scanned or image-based PDF without readable text layer (OCR required).",
                claims=claims,
                summary=summary,
            )

        # 2. Decompose canonical agreement fields into atomic claims
        claims: List[AtomicClaim] = decompose_agreement(structured_agreement, doc_id)

        # 3. Verification decision ladder for each claim
        verified_count = 0
        not_found_count = 0
        ambiguous_count = 0
        unresolved_count = 0
        unsupported_count = 0
        contradictory_count = 0
        refused_count = 0

        for claim in claims:
            field_name = claim.field_name
            provenanced_val = getattr(structured_agreement, field_name, None)

            # Step 3a: No source / Term absent from document
            if not provenanced_val or provenanced_val.status == ExtractionStatus.NOT_FOUND or not claim.value:
                claim.status = VerificationStatus.NOT_FOUND
                claim.claim_tag = ClaimTag.NOT_FOUND
                claim.verification.reason_code = "TERM_ABSENT_FROM_DOCUMENT"
                not_found_count += 1
                continue

            # Step 3b: Ambiguous matches in document
            if provenanced_val.status == ExtractionStatus.AMBIGUOUS:
                claim.status = VerificationStatus.AMBIGUOUS
                claim.claim_tag = None  # Correction 1: AMBIGUOUS -> ClaimTag = None
                claim.verification.reason_code = "MULTIPLE_AMBIGUOUS_SOURCES"
                ambiguous_count += 1
                continue

            # Step 3c: Unresolved provenance or missing physical coordinates
            if (
                provenanced_val.status == ExtractionStatus.UNRESOLVED
                or not provenanced_val.exact_quote
                or not provenanced_val.bbox
            ):
                claim.status = VerificationStatus.UNRESOLVED
                claim.claim_tag = None  # Correction 1: UNRESOLVED -> ClaimTag = None
                claim.verification.reason_code = "PROVENANCE_COORDINATES_UNAVAILABLE"
                unresolved_count += 1
                continue

            # Step 3d: Source exists -> Evaluate Deterministic Support
            source_text = provenanced_val.exact_quote
            is_supported, reason_code, method = self.deterministic_checker.check_claim_support(
                claim,
                source_text,
            )
            claim.verification.deterministic_result = reason_code
            claim.verification.resolution_method = method

            if is_supported is True:
                # Deterministic support established -> directly VERIFIED (Correction 7)
                claim.status = VerificationStatus.VERIFIED
                claim.claim_tag = ClaimTag.EXPLICIT
                claim.verification.reason_code = reason_code
                verified_count += 1

            elif is_supported is False:
                # Deterministic check found conflict (e.g. wrong actor, numeric conflict)
                claim.status = VerificationStatus.UNSUPPORTED
                claim.claim_tag = None  # Correction 1: UNSUPPORTED -> ClaimTag = None
                claim.verification.reason_code = reason_code
                unsupported_count += 1

            else:
                # Source exists and deterministic check is insufficient -> Run Semantic Evaluator (Correction 7)
                try:
                    sem_res = await self.semantic_evaluator.evaluate(claim, source_text)
                    claim.verification.semantic_result = sem_res.decision
                    claim.verification.reason_code = sem_res.reason_code

                    if sem_res.decision == "SUPPORTED":
                        claim.status = VerificationStatus.VERIFIED
                        claim.claim_tag = ClaimTag.EXPLICIT
                        verified_count += 1
                    elif sem_res.decision == "NOT_SUPPORTED":
                        claim.status = VerificationStatus.UNSUPPORTED
                        claim.claim_tag = None
                        unsupported_count += 1
                    else:
                        claim.status = VerificationStatus.UNRESOLVED
                        claim.claim_tag = None
                        unresolved_count += 1
                except Exception as exc:
                    logger.warning(f"Semantic evaluation error for {field_name}: {exc}")
                    claim.status = VerificationStatus.UNRESOLVED
                    claim.claim_tag = None
                    unresolved_count += 1

            # Step 3e: Contradiction Hook interface check (Correction 2: returns NOT_EVALUATED in Phase 4)
            contra_res = self.contradiction_hook.check(claim, claims)
            claim.verification.contradiction_result = contra_res.status
            if contra_res.status == "CONTRADICTORY":
                claim.status = VerificationStatus.CONTRADICTORY
                claim.claim_tag = None
                contradictory_count += 1

        summary = VerificationSummary(
            total=len(claims),
            verified=verified_count,
            not_found=not_found_count,
            ambiguous=ambiguous_count,
            unresolved=unresolved_count,
            unsupported=unsupported_count,
            contradictory=contradictory_count,
            refused=refused_count,
        )

        doc_status = "VERIFIED_FULL" if verified_count == len(claims) else "VERIFIED_PARTIAL"

        return DocumentVerificationResult(
            document_id=doc_id,
            filename=filename,
            document_status=doc_status,
            claims=claims,
            summary=summary,
        )
