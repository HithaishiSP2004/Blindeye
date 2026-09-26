from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.document import BoundingBox


class ClaimTag(str, Enum):
    """The persistent 5-tier A–E evidence taxonomy for all user-facing claims."""

    EXPLICIT = "A / EXPLICIT IN DOCUMENT"
    DERIVED = "B / DERIVED FROM CLAUSES"
    GENERAL_LEGAL = "C / GENERAL LEGAL INFORMATION"
    NOT_FOUND = "D / NO SUPPORTING PASSAGE"
    CONFLICTING = "E / CONFLICTING EVIDENCE"


class VerificationStatus(str, Enum):
    """Conservative decision states for claims."""

    VERIFIED = "VERIFIED"          # Physically supported by document provenance (ClaimTag.EXPLICIT)
    UNSUPPORTED = "UNSUPPORTED"    # Claim contradicts or exceeds source passage (ClaimTag = None)
    NOT_FOUND = "NOT_FOUND"        # Term absent from document (ClaimTag.NOT_FOUND)
    AMBIGUOUS = "AMBIGUOUS"        # Multiple unresolved sources (ClaimTag = None)
    UNRESOLVED = "UNRESOLVED"      # Verification inconclusive or source unavailable (ClaimTag = None)
    CONTRADICTORY = "CONTRADICTORY"# Future Phase 6 hook: mutually incompatible clauses (ClaimTag = None)
    REFUSED = "REFUSED"            # Refused by document-level policy (e.g. unreadable scanned document)


class RefusalCategory(str, Enum):
    """Categorical reasons for refusal without hallucinated fallback."""

    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    LEGAL_ADVICE = "LEGAL_ADVICE"           # For Phase 5 Q&A requests
    OUT_OF_SCOPE = "OUT_OF_SCOPE"           # For Phase 5 Q&A requests
    UNTRUSTED_INSTRUCTION = "UNTRUSTED_INSTRUCTION"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"


class ClaimSource(BaseModel):
    """Physical evidence coordinates and verbatim quotation."""

    clause_id: Optional[str] = None
    clause_number: Optional[str] = None
    page: Optional[int] = None
    pages: List[int] = Field(default_factory=list)
    quote: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)


class ClaimVerificationMetadata(BaseModel):
    """Auditability and observability technical metadata."""

    deterministic_result: Optional[str] = None
    semantic_result: Optional[str] = None
    resolution_method: Optional[str] = None
    reason_code: Optional[str] = None
    contradiction_result: str = "NOT_EVALUATED"


class AtomicClaim(BaseModel):
    """Singular verifiable factual statement decomposed from an extracted field."""

    claim_id: str = Field(..., description="Unique claim identifier e.g., 'claim_1'")
    claim_text: Optional[str] = Field(default=None, description="Atomic factual statement")
    field_name: str = Field(default="", description="Canonical field identifier")
    subject: str = Field(default="", description="Subject of the claim")
    actor: Optional[str] = Field(default=None, description="Legal party bound: licensor/licensee/both")
    predicate: str = Field(default="", description="Legal relationship or duty")
    value: Optional[str] = Field(default=None, description="Canonical extracted value")
    unit: Optional[str] = Field(default=None, description="Unit e.g., 'INR', 'MONTHS', 'DAYS'")
    qualifiers: List[str] = Field(default_factory=list, description="Contextual conditions")
    source_document_id: Optional[str] = None
    status: VerificationStatus = Field(default=VerificationStatus.UNRESOLVED)
    claim_tag: Optional[ClaimTag] = None  # None for UNRESOLVED, AMBIGUOUS, UNSUPPORTED, CONTRADICTORY
    tag: Optional[ClaimTag] = None        # Legacy Phase 1 alias
    source: Optional[ClaimSource] = None
    supporting_clause_ids: List[str] = Field(default_factory=list)
    exact_quotes: List[str] = Field(default_factory=list)
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0)
    verification: ClaimVerificationMetadata = Field(default_factory=ClaimVerificationMetadata)


class VerificationSummary(BaseModel):
    """Derived verification counts calculated strictly from atomic claim outcomes."""

    total: int = 0
    verified: int = 0
    not_found: int = 0
    ambiguous: int = 0
    unresolved: int = 0
    unsupported: int = 0
    contradictory: int = 0
    refused: int = 0


class DocumentVerificationResult(BaseModel):
    """Top-level verification payload for POST /documents/verify.

    Does NOT serialize the full DocumentTree in the public response contract.
    """

    document_id: str
    filename: str
    document_status: str  # 'VERIFIED_PARTIAL', 'VERIFIED_FULL', 'UNREADABLE_DOCUMENT'
    refusal_reason: Optional[str] = None
    claims: List[AtomicClaim]
    summary: VerificationSummary


class VerificationResult(BaseModel):
    """Aggregate decision gate result for backwards compatibility with Phase 1."""

    is_verified: bool = Field(..., description="Whether constituent claims pass the verification gate")
    overall_tag: ClaimTag = Field(..., description="Dominant taxonomy classification")
    claims: List[AtomicClaim] = Field(default_factory=list, description="Constituent claims")
    refusal_reason: Optional[str] = Field(default=None)
