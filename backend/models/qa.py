from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.document import BoundingBox


class QuestionType(str, Enum):
    """Categorization of user inquiry intent."""

    FACT_LOOKUP = "FACT_LOOKUP"
    CLAUSE_LOOKUP = "CLAUSE_LOOKUP"
    RELATIONSHIP_LOOKUP = "RELATIONSHIP_LOOKUP"
    LEGAL_ADVICE = "LEGAL_ADVICE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AnswerStatus(str, Enum):
    """Factual answer outcome status (Correction 2: strictly separate from question type)."""

    ANSWERED = "ANSWERED"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    REFUSED = "REFUSED"


class RetrievalMethod(str, Enum):
    """Underlying retrieval strategy executed."""

    FIELD_LOOKUP = "FIELD_LOOKUP"
    CLAUSE_LOOKUP = "CLAUSE_LOOKUP"
    BM25 = "BM25"
    SEMANTIC = "SEMANTIC"


class EvidenceCitation(BaseModel):
    """Physical document evidence citation supporting a Q&A answer."""

    clause_id: Optional[str] = Field(default=None, description="Identifier of the supporting clause")
    clause_number: Optional[str] = Field(default=None, description="Section or clause number e.g., '2.1'")
    page: int = Field(..., ge=1, description="1-indexed document page number")
    quote: str = Field(..., description="Verbatim quote sliced directly from DocumentTree")
    bbox: Optional[BoundingBox] = Field(default=None, description="Physical bounding box in PDF points")
    char_start: Optional[int] = Field(default=None, description="Start character offset in page text")
    char_end: Optional[int] = Field(default=None, description="End character offset in page text")


class RetrievalMetadata(BaseModel):
    """Observability metadata for the retrieval stage (Correction 4: score is never named confidence)."""

    method: RetrievalMethod
    candidates_reviewed: int = 1
    retrieval_score: Optional[float] = None


class QARequest(BaseModel):
    """Request payload for agreement question answering."""

    question: str = Field(..., min_length=1, description="User question about the agreement")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Lightweight previous turns for coreference resolution (context only, not evidence)",
    )


class QAResponse(BaseModel):
    """Strict response contract for POST /documents/ask."""

    question: str
    status: AnswerStatus
    question_type: QuestionType
    answer: str
    evidence: List[EvidenceCitation] = Field(default_factory=list)
    retrieval: RetrievalMetadata
    refusal_reason: Optional[str] = None
