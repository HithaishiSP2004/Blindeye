import re
from typing import Optional
from backend.models.document import DocumentTree, ParsingStatus
from backend.models.verification import RefusalCategory

# Reusable patterns for legal advice classification (Ready for Phase 5 user Q&A)
RE_LEGAL_ADVICE_PATTERNS = [
    r"\b(should I|can I sue|sue my|legal strategy|legal action|how to evict|to evict|enforceability|comply with|compliance with)\b",
    r"\b(is this clause legal|is it legal to|what are my rights|chances of winning)\b",
    r"\b(advice on|advise me|legal advice|legal recourse|police complaint|file a complaint)\b",
]

# Patterns for adversarial prompt injection in user queries
RE_INJECTION_PATTERNS = [
    r"\b(ignore all previous instructions|system override|developer message|reveal system prompt)\b",
    r"\b(disclose instructions|output internal prompt|bypass guardrails)\b",
]


class RefusalEngine:
    """Central engine for policy-based refusals and safety gates.

    Enforces:
    - Document prompt injection does NOT reject legitimate documents (Correction 3).
    - Request-level legal advice classification is modularized for Phase 5 (Correction 4).
    """

    def check_document_refusal(self, document_tree: DocumentTree) -> Optional[RefusalCategory]:
        """Inspect document for unreadable or scanned status requiring OCR."""
        if document_tree.parsing_status == ParsingStatus.OCR_REQUIRED:
            return RefusalCategory.UNREADABLE_DOCUMENT
        return None

    def classify_request(self, request_text: str) -> Optional[RefusalCategory]:
        """Classify user query for Phase 5 Q&A readiness (Correction 4)."""
        if not request_text or not request_text.strip():
            return None

        clean = request_text.strip().lower()

        # Check prompt injection in user query
        for pattern in RE_INJECTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                return RefusalCategory.UNTRUSTED_INSTRUCTION

        # Check legal advice request
        for pattern in RE_LEGAL_ADVICE_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                return RefusalCategory.LEGAL_ADVICE

        return None
