from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.models.document import BoundingBox, DocumentTree
from backend.models.verification import ClaimTag


class ExtractionStatus(str, Enum):
    """Field-level resolution state."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class ResolutionMethod(str, Enum):
    """Deterministic method used to resolve source text from DocumentTree."""

    EXACT_QUOTE = "EXACT_QUOTE"
    NORMALIZED_QUOTE = "NORMALIZED_QUOTE"
    VALUE_WITHIN_CANDIDATE_CLAUSE = "VALUE_WITHIN_CANDIDATE_CLAUSE"
    UNRESOLVED = "UNRESOLVED"


class MatchQuality(str, Enum):
    """Internal technical source match classification (NOT presented as an AI confidence score)."""

    EXACT_SOURCE_MATCH = "EXACT_SOURCE_MATCH"
    NORMALIZED_SOURCE_MATCH = "NORMALIZED_SOURCE_MATCH"
    VALUE_CONTEXT_MATCH = "VALUE_CONTEXT_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    NO_MATCH = "NO_MATCH"


class ValueQualifier(str, Enum):
    """Semantic dimension/unit of the extracted term."""

    CURRENCY = "INR"
    DURATION_MONTHS = "MONTHS"
    DURATION_DAYS = "DAYS"
    DATE = "DATE"
    TEXT = "TEXT"
    PERCENTAGE = "PERCENTAGE"


class CandidateFact(BaseModel):
    """Raw candidate fact suggested by the Gemini structured extraction model.

    CRITICAL: This is only a hint/suggestion. The model CANNOT prove truth or bounding boxes.
    """

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(..., description="Canonical field identifier e.g., 'monthly_rent'")
    candidate_value: Optional[str] = Field(default=None, description="Suggested canonical or standardized value")
    candidate_quote: Optional[str] = Field(default=None, description="Candidate search string / quote from agreement")
    candidate_clause_id: Optional[str] = Field(default=None, description="Suggested source clause ID or clause number")
    is_present: bool = Field(default=True, description="Whether the model believes this term is present")
    reasoning_summary: Optional[str] = Field(default=None, description="Brief rationale for extraction")


class CandidateExtractionResult(BaseModel):
    """Pydantic schema passed to Gemini native structured output (response_schema)."""

    model_config = ConfigDict(extra="forbid")

    agreement_type: Optional[CandidateFact] = None
    execution_date: Optional[CandidateFact] = None
    landlord_name: Optional[CandidateFact] = None
    tenant_name: Optional[CandidateFact] = None
    property_address: Optional[CandidateFact] = None
    tenure_months: Optional[CandidateFact] = None
    commencement_date: Optional[CandidateFact] = None
    lock_in_months: Optional[CandidateFact] = None
    monthly_rent: Optional[CandidateFact] = None
    security_deposit: Optional[CandidateFact] = None
    deposit_refund_days: Optional[CandidateFact] = None
    notice_period_days: Optional[CandidateFact] = None
    maintenance_responsibility: Optional[CandidateFact] = None
    late_payment_penalty: Optional[CandidateFact] = None
    permitted_use: Optional[CandidateFact] = None
    renewal_terms: Optional[CandidateFact] = None


class ProvenancedValue(BaseModel):
    """An extracted factual value physically anchored to a source clause."""

    field_name: str = Field(default="", description="Canonical field identifier")
    status: ExtractionStatus = Field(default=ExtractionStatus.NOT_FOUND, description="Field resolution state")
    value: Optional[str] = Field(default=None, description="Extracted canonical string value")
    is_present: bool = Field(default=False, description="Whether the term was found and verified in the document")

    # CRITICAL Correction 3: claim_tag is Optional[ClaimTag] = None during initialization.
    # It must NEVER default to EXPLICIT. Assigned deterministically based on resolution state.
    claim_tag: Optional[ClaimTag] = Field(
        default=None,
        description="Assigned ClaimTag taxonomy. NEVER defaulted to EXPLICIT.",
    )

    source_clause_id: Optional[str] = Field(default=None, description="Referenced clause ID")
    source_clause_number: Optional[str] = Field(default=None, description="Human clause number e.g., '2.1'")
    page: Optional[int] = Field(default=None, ge=1, description="Primary page number where the term appears")
    pages: List[int] = Field(default_factory=list, description="All pages covering the source quote")
    exact_quote: Optional[str] = Field(
        default=None,
        description="Verbatim quote sliced directly from DocumentTree (never raw candidate quote)",
    )
    bbox: Optional[BoundingBox] = Field(default=None, description="Primary spatial coordinate on page for illumination")
    bounding_boxes: List[BoundingBox] = Field(
        default_factory=list,
        description="All bounding boxes covering the exact quote across spans/lines",
    )
    resolution_method: Optional[ResolutionMethod] = Field(
        default=None,
        description="Internal technical metadata for how the source was matched",
    )
    match_quality: Optional[MatchQuality] = Field(
        default=None,
        description="Internal technical classification of match quality",
    )
    candidate_quote: Optional[str] = Field(
        default=None,
        description="Internal record of what the model initially suggested",
    )
    candidate_clause_id: Optional[str] = Field(
        default=None,
        description="Internal record of clause suggested by model",
    )
    qualifier: Optional[ValueQualifier] = Field(default=None, description="Semantic dimension/unit")
    ambiguity_candidates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Candidate matches when status is AMBIGUOUS",
    )


class ExtractionSummary(BaseModel):
    """Derived extraction counts calculated strictly from actual field-level results."""

    fields_total: int = Field(default=0, description="Total fields evaluated")
    fields_found: int = Field(default=0, description="Fields resolved as FOUND with verified provenance")
    fields_not_found: int = Field(default=0, description="Fields confirmed NOT_FOUND in document")
    fields_ambiguous: int = Field(default=0, description="Fields with multiple conflicting/unclear sources")
    fields_unresolved: int = Field(default=0, description="Fields suggested by model but unsupported by document")
    fields_provenance_resolved: int = Field(default=0, description="Fields with confirmed physical bounding boxes")


class StructuredAgreement(BaseModel):
    """Core structured agreement terms extracted from an Indian residential agreement."""

    document_id: str = Field(..., description="Referenced document session UUID")
    summary: ExtractionSummary = Field(default_factory=ExtractionSummary)
    agreement_type: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="agreement_type"))
    execution_date: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="execution_date"))
    landlord_name: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="landlord_name"))
    tenant_name: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="tenant_name"))
    property_address: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="property_address"))
    tenure_months: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="tenure_months"))
    commencement_date: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="commencement_date"))
    lock_in_months: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="lock_in_months"))
    monthly_rent: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="monthly_rent"))
    security_deposit: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="security_deposit"))
    deposit_refund_days: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="deposit_refund_days"))
    notice_period_days: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="notice_period_days"))
    maintenance_responsibility: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="maintenance_responsibility"))
    late_payment_penalty: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="late_payment_penalty"))
    permitted_use: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="permitted_use"))
    renewal_terms: ProvenancedValue = Field(default_factory=lambda: ProvenancedValue(field_name="renewal_terms"))


class StructuredAgreementResult(BaseModel):
    """Top-level payload returned by POST /documents/extract."""

    document_tree: DocumentTree
    structured_agreement: StructuredAgreement
