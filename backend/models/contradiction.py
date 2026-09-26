from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.document import BoundingBox, TextSpan


class ContradictionStatus(str, Enum):
    """Factual classification of contradiction state between two statements.

    Strictly non-evaluative: no risk ratings or legal judgment labels.
    """

    CONFIRMED_CONFLICT = "CONFIRMED_CONFLICT"
    NO_CONFLICT = "NO_CONFLICT"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    UNRESOLVED = "UNRESOLVED"


class ContradictionActor(str, Enum):
    """Contractual party or actor bound by the obligation/covenant."""

    TENANT = "TENANT"
    LANDLORD = "LANDLORD"
    BOTH = "BOTH"
    MUTUAL = "MUTUAL"
    UNKNOWN = "UNKNOWN"


class ContradictionSubject(str, Enum):
    """Categorized contractual subject matter."""

    NOTICE_PERIOD = "NOTICE_PERIOD"
    MONTHLY_RENT = "MONTHLY_RENT"
    SECURITY_DEPOSIT = "SECURITY_DEPOSIT"
    TENURE = "TENURE"
    COMMENCEMENT_DATE = "COMMENCEMENT_DATE"
    LOCK_IN_PERIOD = "LOCK_IN_PERIOD"
    MAINTENANCE_RESPONSIBILITY = "MAINTENANCE_RESPONSIBILITY"
    UTILITY_RESPONSIBILITY = "UTILITY_RESPONSIBILITY"
    TERMINATION_CONDITIONS = "TERMINATION_CONDITIONS"
    OTHER = "OTHER"


class ContradictionEvidence(BaseModel):
    """Verbatim physical evidence for one side of a compared statement."""

    clause_id: Optional[str] = Field(default=None, description="Clause identifier if anchored to a clause")
    clause_number: Optional[str] = Field(default=None, description="Human-readable clause number e.g. '4'")
    page_number: int = Field(..., ge=1, description="Page number where the statement resides")
    exact_quote: str = Field(..., description="Verbatim text quote from DocumentTree")
    bounding_boxes: List[BoundingBox] = Field(default_factory=list, description="Physical bounding boxes")
    spans: List[TextSpan] = Field(default_factory=list, description="Granular text spans")


class ContradictionFinding(BaseModel):
    """Structured finding comparing two statements within the same agreement.

    Adheres strictly to Phase 6 rules:
    - Identifies textual conflict, never adjudicates legal priority or enforceability.
    - Resolves dual physical provenance (source_a and source_b).
    """

    finding_id: str = Field(..., description="Unique deterministic identifier for finding")
    status: ContradictionStatus = Field(..., description="Contradiction status")
    subject: ContradictionSubject = Field(..., description="Contractual subject")
    actor: ContradictionActor = Field(..., description="Actor bound by the statement")
    value_a: str = Field(..., description="Extracted value for statement A")
    value_b: str = Field(..., description="Extracted value for statement B")
    unit: Optional[str] = Field(default=None, description="Unit of measurement e.g. days, INR, months")
    context_scope: Optional[str] = Field(default=None, description="Temporal or conditional scope if detected")
    claim_a: str = Field(..., description="Concise statement summarizing claim A")
    claim_b: str = Field(..., description="Concise statement summarizing claim B")
    source_a: ContradictionEvidence = Field(..., description="Physical evidence for claim A")
    source_b: ContradictionEvidence = Field(..., description="Physical evidence for claim B")
    explanation: str = Field(..., description="Factual, non-adjudicating explanation of the conflict")
    comparison_method: str = Field(
        default="deterministic_context_match",
        description="Method used to establish comparison (e.g. deterministic_context_match)",
    )


class ContradictionResponse(BaseModel):
    """Stateless response payload for /documents/contradictions endpoint."""

    findings: List[ContradictionFinding] = Field(default_factory=list)
    total_conflicts: int = Field(default=0, ge=0)
    evaluation_summary: str = Field(..., description="Restrained summary of contradiction analysis")
