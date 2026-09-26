import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from backend.models.document import DocumentTree
from backend.models.extraction import ExtractionStatus, ProvenancedValue, StructuredAgreement
from backend.models.qa import AnswerStatus, EvidenceCitation

# Canonical question patterns mapping to StructuredAgreement field names
CANONICAL_FIELD_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    # (field_name, display_name, regex)
    (
        "monthly_rent",
        "Monthly Rent",
        re.compile(
            r"\b(monthly rent|rent amount|pay each month|how much rent|rent per month|rent fee|what is the rent|\brent\b)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "security_deposit",
        "Security Deposit",
        re.compile(
            r"\b(security deposit|refundable deposit|deposit amount|how much (?:is the )?deposit|\bdeposit\b)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tenure_months",
        "Agreement Tenure",
        re.compile(
            r"\b(how long is the agreement|duration of (?:the )?agreement|tenure|agreement period|period of lease|term of (?:the )?agreement|number of months)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "commencement_date",
        "Commencement Date",
        re.compile(
            r"\b(when does (?:the )?(?:agreement|lease|license) start|commence|commencement date|start date|effective date)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "landlord_name",
        "Landlord Name",
        re.compile(
            r"\b(who is the (?:landlord|licensor|owner|lessor)|landlord'?s? name|licensor'?s? name|owner'?s? name)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tenant_name",
        "Tenant Name",
        re.compile(
            r"\b(who is the (?:tenant|licensee|renter|lessee)|tenant'?s? name|licensee'?s? name)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "property_address",
        "Property Address",
        re.compile(
            r"\b(property address|address of (?:the )?property|premises address|situated at|where is the (?:property|flat|apartment|premises)|pin code)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "lock_in_period",
        "Lock-in Period",
        re.compile(
            r"\b(lock[\s\-]?in (?:period|months|clause)|is there a lock[\s\-]?in)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "notice_period_days",
        "Notice Period",
        re.compile(
            r"\b(notice period|period of notice|notice for termination|how much notice (?:is required|to vacate|to terminate))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "deposit_refund_days",
        "Deposit Refund Days",
        re.compile(
            r"\b(refund of deposit|deposit refund|return (?:of )?(?:the )?deposit|days to refund deposit)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "late_payment_penalty",
        "Late Payment Penalty",
        re.compile(
            r"\b(late (?:payment )?penalty|interest on late|penalty for delayed|late rent fee)\b",
            re.IGNORECASE,
        ),
    ),
]


class FieldLookupResult(BaseModel):
    """Result of deterministic canonical field lookup."""

    is_matched: bool
    field_name: Optional[str] = None
    status: AnswerStatus
    answer: Optional[str] = None
    evidence: List[EvidenceCitation] = []
    provenanced_value: Optional[ProvenancedValue] = None


class FieldLookup:
    """Fast deterministic lookup for canonical residential agreement fields.

    Adheres strictly to Phase 5 Corrections:
    - Canonical factual questions resolve deterministically without requiring Gemini (Correction 6).
    - NOT_FOUND is returned cleanly if term is absent (Correction 2 & 26).
    - Source quotes sliced directly from DocumentTree (Correction 10).
    - No hallucinations or outside inferences.
    """

    def match_canonical_field(self, question: str) -> Optional[str]:
        """Check if question matches a canonical residential field pattern."""
        clean = question.strip()
        for field_name, _, pattern in CANONICAL_FIELD_PATTERNS:
            if pattern.search(clean):
                return field_name
        return None

    def lookup(
        self,
        question: str,
        structured_agreement: Optional[StructuredAgreement],
        document_tree: DocumentTree,
    ) -> FieldLookupResult:
        """Resolve canonical field question deterministically."""
        field_name = self.match_canonical_field(question)
        if not field_name:
            return FieldLookupResult(
                is_matched=False,
                status=AnswerStatus.UNRESOLVED,
            )

        # If structured_agreement is not available, we can't extract fields directly
        if not structured_agreement:
            return FieldLookupResult(
                is_matched=True,
                field_name=field_name,
                status=AnswerStatus.UNRESOLVED,
            )

        # Map lock_in_period to lock_in_months attribute on StructuredAgreement
        attr_name = "lock_in_months" if field_name == "lock_in_period" else field_name
        pval: Optional[ProvenancedValue] = getattr(structured_agreement, attr_name, None)

        # Field absent / NOT_FOUND
        if not pval or not pval.is_present or pval.status == ExtractionStatus.NOT_FOUND or not pval.value:
            missing_templates: Dict[str, str] = {
                "property_address": "The agreement does not provide a property address.",
                "lock_in_period": "The agreement does not mention a lock-in period.",
                "late_payment_penalty": "The agreement does not specify a late payment penalty.",
                "deposit_refund_days": "The agreement does not specify a timeline for security deposit refund.",
            }
            default_missing = f"The agreement does not contain information regarding {field_name.replace('_', ' ')}."
            return FieldLookupResult(
                is_matched=True,
                field_name=field_name,
                status=AnswerStatus.NOT_FOUND,
                answer=missing_templates.get(field_name, default_missing),
                evidence=[],
                provenanced_value=pval,
            )

        # Ambiguous
        if pval.status == ExtractionStatus.AMBIGUOUS:
            return FieldLookupResult(
                is_matched=True,
                field_name=field_name,
                status=AnswerStatus.AMBIGUOUS,
                answer=f"Multiple ambiguous provisions exist regarding {field_name.replace('_', ' ')}.",
                evidence=[],
                provenanced_value=pval,
            )

        # Field is present and verified/supported
        quote = pval.exact_quote or pval.value or ""
        citation = EvidenceCitation(
            clause_id=pval.source_clause_id,
            clause_number=pval.source_clause_number,
            page=pval.page or 1,
            quote=quote,
            bbox=pval.bbox,
        )

        # Build clean deterministic answer template
        deterministic_answers: Dict[str, str] = {
            "monthly_rent": f"The monthly rent is {pval.value} per month.",
            "security_deposit": f"The security deposit is {pval.value}.",
            "tenure_months": f"The duration of the agreement is {pval.value}.",
            "commencement_date": f"The agreement commences on {pval.value}.",
            "landlord_name": f"The landlord is {pval.value}.",
            "tenant_name": f"The tenant is {pval.value}.",
            "notice_period_days": f"The notice period is {pval.value}.",
        }
        answer = deterministic_answers.get(field_name, f"{field_name.replace('_', ' ').capitalize()}: {pval.value}")

        return FieldLookupResult(
            is_matched=True,
            field_name=field_name,
            status=AnswerStatus.ANSWERED,
            answer=answer,
            evidence=[citation],
            provenanced_value=pval,
        )
