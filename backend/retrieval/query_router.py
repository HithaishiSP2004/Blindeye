import re
from typing import Optional
from pydantic import BaseModel
from backend.models.qa import QuestionType
from backend.verification.refusal_engine import RefusalEngine

# Patterns specifically identifying out-of-scope external legal/general questions
RE_OUT_OF_SCOPE_PATTERNS = [
    r"\b(what does the law say|indian law|statute|transfer of property act|rent control act|rera|ipc|crpc|constitution)\b",
    r"\b(case law|supreme court|high court|precedent|judgement|ruling)\b",
    r"\b(capital of|weather in|write code|python script|recipe|who won)\b",
]

# Patterns specifically identifying legal advice / enforceability questions
RE_LEGAL_ADVICE_SPECIFIC = [
    r"\b(enforceable|enforceability|legally valid|legally binding)\b",
    r"\b(is (?:this|the|it|[\w\s]+?) (?:legally )?(?:valid|enforceable|legal|illegal|binding))\b",
    r"\b(can (?:i|the tenant|the landlord) sue)\b",
    r"\b(what should (?:i|the tenant|the landlord) do)\b",
    r"\b(is this notice (?:period )?(?:legal|valid|enforceable))\b",
    r"\b(how to evict|can i evict|file (?:a )?case|legal remedy|legal recourse)\b",
]


# Regex for detecting specific clause mentions e.g. "Clause 3", "Section 4", "Clause 2.1"
RE_CLAUSE_MENTION = re.compile(
    r"\b(?:clause|section|article|point|cl\.?)\s*([0-9]+(?:\.[0-9]+)*|[a-zA-Z])\b",
    re.IGNORECASE,
)

# Regex for relationship / role responsibility queries
RE_RELATIONSHIP_PATTERNS = [
    r"\b(who is responsible for|who pays for|who maintains|responsibility for|obligation to|duty of)\b",
    r"\b(who repairs|responsible for repairs|maintenance responsibility)\b",
]

# Regex for adversarial prompt injections in queries
RE_INJECTION = re.compile(
    r"\b(ignore (?:all )?(?:previous |prior )?(?:instructions|rules|directions)|system override|developer mode|tell me (?:the )?(?:rent|value) is (?:zero|0)|say rent is (?:zero|0))\b",
    re.IGNORECASE,
)

RE_INJECTION_DIRECTIVES = [
    r"(?i)\bignore (?:the )?agreement\b",
    r"(?i)\bignore (?:all )?(?:previous |prior )?(?:instructions|rules|directions)\b",
    r"(?i)\bsystem override\b",
    r"(?i)\bdeveloper mode\b",
    r"(?i)\bdisclose instructions|reveal system prompt|bypass guardrails\b",
]


class QueryRouteResult(BaseModel):
    """Result of classifying a user Q&A query."""

    question_type: QuestionType
    is_refused: bool = False
    refusal_reason: Optional[str] = None
    target_clause: Optional[str] = None
    cleaned_query: str


class QueryRouter:
    """Classifies user queries into distinct question types and enforces security boundaries.

    Adheres strictly to Phase 5 Corrections:
    - MISSING_INFORMATION is never a question category (Correction 2).
    - Document questions vs Legal advice strictly segregated (Correction 15).
    - Prompt injections are sanitized and never bypass verification (Correction 13 & 14).
    - External law queries are flagged as OUT_OF_SCOPE (Correction 16).
    """

    def __init__(self, refusal_engine: Optional[RefusalEngine] = None):
        self.refusal_engine = refusal_engine or RefusalEngine()

    def route(self, question: str) -> QueryRouteResult:
        if not question or not question.strip():
            return QueryRouteResult(
                question_type=QuestionType.FACT_LOOKUP,
                is_refused=True,
                refusal_reason="Empty question provided.",
                cleaned_query="",
            )

        clean = question.strip()
        lower_q = clean.lower()

        # 1. Check for prompt injection / instruction-override directives (Hardening Correction 2)
        # Treat instruction-like text as untrusted. Neutralize directive content while extracting legitimate inquiry.
        has_injection = bool(RE_INJECTION.search(lower_q))
        if has_injection:
            inquiry = clean
            for pattern in RE_INJECTION_DIRECTIVES:
                inquiry = re.sub(pattern, "", inquiry)
            inquiry = re.sub(r"(?i)\band (?:state|say|tell me) (?:that )?(?:the )?(?:rent|deposit|value) is [^\.\?]+[\.\?]?", "", inquiry)
            inquiry = re.sub(r"(?i)\btell me (?:the )?(?:rent|deposit|value) is [^\.\?]+[\.\?]?", "", inquiry)
            inquiry = re.sub(r"\s+", " ", inquiry).strip(" '\":;,.-")

            if inquiry and len(inquiry) > 3:
                clean = inquiry
                lower_q = clean.lower()
            else:
                # If only untrusted directives and target concepts were present, extract the underlying document concept
                # rather than silently fabricating a canned question.
                found_topic = None
                for topic in ["rent", "security deposit", "deposit", "notice period", "lock-in", "maintenance", "tenure"]:
                    if topic in lower_q:
                        found_topic = topic
                        break
                if found_topic:
                    clean = found_topic
                    lower_q = clean.lower()
                else:
                    return QueryRouteResult(
                        question_type=QuestionType.FACT_LOOKUP,
                        is_refused=True,
                        refusal_reason="Untrusted instruction or directive detected without a legitimate document inquiry.",
                        cleaned_query=question,
                    )


        # 2. Check for External Law / Out of Scope (Correction 16)
        for pattern in RE_OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, lower_q, re.IGNORECASE):
                return QueryRouteResult(
                    question_type=QuestionType.OUT_OF_SCOPE,
                    is_refused=True,
                    refusal_reason=(
                        "External legal statutes, case law, and general legal questions are out of scope. "
                        "Antigravity analyzes only the factual contents of the uploaded agreement."
                    ),
                    cleaned_query=clean,
                )

        # 3. Check for Legal Advice / Enforceability (Correction 15)
        for pattern in RE_LEGAL_ADVICE_SPECIFIC:
            if re.search(pattern, lower_q, re.IGNORECASE):
                return QueryRouteResult(
                    question_type=QuestionType.LEGAL_ADVICE,
                    is_refused=True,
                    refusal_reason=(
                        "Requests for legal advice, statutory enforceability, or strategic courses of action "
                        "cannot be answered by this system. Please consult a licensed advocate or legal professional."
                    ),
                    cleaned_query=clean,
                )

        # Also delegate to RefusalEngine if it catches general advice patterns
        # But ensure document questions like "what does the agreement say about termination" are NOT refused!
        is_document_factual_query = bool(
            re.search(
                r"\b(what does (?:the )?(?:agreement|contract|clause|document) say|how much|when|who|is there a)\b",
                lower_q,
            )
        )
        if not is_document_factual_query:
            refusal_cat = self.refusal_engine.classify_request(clean)
            if refusal_cat:
                return QueryRouteResult(
                    question_type=QuestionType.LEGAL_ADVICE,
                    is_refused=True,
                    refusal_reason=(
                        "Inquiries seeking actionable legal advice or rights evaluation are outside the scope "
                        "of factual document verification."
                    ),
                    cleaned_query=clean,
                )

        # 4. Check for explicit Clause / Section mentions (Correction 17)
        clause_match = RE_CLAUSE_MENTION.search(clean)
        if clause_match:
            target_clause = clause_match.group(1)
            return QueryRouteResult(
                question_type=QuestionType.CLAUSE_LOOKUP,
                is_refused=False,
                target_clause=target_clause,
                cleaned_query=clean,
            )

        # 5. Check for Relationship / Responsibility questions
        for pattern in RE_RELATIONSHIP_PATTERNS:
            if re.search(pattern, lower_q, re.IGNORECASE):
                return QueryRouteResult(
                    question_type=QuestionType.RELATIONSHIP_LOOKUP,
                    is_refused=False,
                    cleaned_query=clean,
                )

        # 6. Default to FACT_LOOKUP (Correction 2)
        return QueryRouteResult(
            question_type=QuestionType.FACT_LOOKUP,
            is_refused=False,
            cleaned_query=clean,
        )
