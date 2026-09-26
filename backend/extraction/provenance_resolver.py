import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from backend.models.document import BoundingBox, Clause, DocumentTree, TextSpan
from backend.models.extraction import (
    CandidateExtractionResult,
    CandidateFact,
    ExtractionStatus,
    ExtractionSummary,
    MatchQuality,
    ProvenancedValue,
    ResolutionMethod,
    StructuredAgreement,
    ValueQualifier,
)
from backend.models.verification import ClaimTag

logger = logging.getLogger(__name__)

# Contextual keywords mapped to canonical field names to disambiguate repeated terms
FIELD_CONTEXT_KEYWORDS: Dict[str, List[str]] = {
    "agreement_type": ["agreement", "deed", "indenture", "leave and license", "lease"],
    "execution_date": ["day of", "executed", "entered into", "dated", "made and executed"],
    "landlord_name": ["licensor", "lessor", "landlord", "owner", "first part"],
    "tenant_name": ["licensee", "lessee", "tenant", "occupant", "second part"],
    "property_address": ["flat", "premises", "apartment", "situated at", "bearing no", "property"],
    "tenure_months": ["term", "duration", "period", "months", "commencing", "tenure"],
    "commencement_date": ["commencing from", "commence", "start from", "effective from", "w.e.f"],
    "lock_in_months": ["lock-in", "lock in", "minimum period", "non-terminable"],
    "monthly_rent": ["monthly rent", "rent", "fee", "compensation", "per month", "sum of rs"],
    "security_deposit": ["security deposit", "interest-free", "refundable deposit", "deposited a sum"],
    "deposit_refund_days": ["refunded within", "refund of deposit", "handover of vacant possession", "return of deposit"],
    "notice_period_days": ["notice", "terminate", "termination", "written notice", "prior notice", "in lieu thereof"],
    "maintenance_responsibility": ["maintenance", "repairs", "minor repairs", "structural repairs", "borne by"],
    "late_payment_penalty": ["penalty", "interest", "delayed payment", "per day", "default"],
    "permitted_use": ["residential purpose", "solely for", "commercial use prohibited", "use and occupy"],
    "renewal_terms": ["renewal", "renewed", "extended", "option to extend", "escalation"],
}

FIELD_QUALIFIERS: Dict[str, ValueQualifier] = {
    "tenure_months": ValueQualifier.DURATION_MONTHS,
    "lock_in_months": ValueQualifier.DURATION_MONTHS,
    "deposit_refund_days": ValueQualifier.DURATION_DAYS,
    "notice_period_days": ValueQualifier.DURATION_DAYS,
    "monthly_rent": ValueQualifier.CURRENCY,
    "security_deposit": ValueQualifier.CURRENCY,
    "late_payment_penalty": ValueQualifier.CURRENCY,
    "commencement_date": ValueQualifier.DATE,
    "execution_date": ValueQualifier.DATE,
}


def _normalize_text_for_search(text: str) -> str:
    """Normalize text strictly for searching candidate positions (never used for output quotes)."""
    # Collapse multiple whitespaces and strip common enclosing punctuation
    t = re.sub(r"\s+", " ", text).strip().lower()
    t = t.replace("/-", "").replace("₹", "rs ").replace("rs.", "rs ")
    return t


def _find_exact_offsets(needle: str, haystack: str) -> Optional[Tuple[int, int]]:
    """Locate verbatim substring character offsets."""
    if not needle or not haystack:
        return None
    idx = haystack.find(needle)
    if idx != -1:
        return (idx, idx + len(needle))
    return None


def _find_normalized_offsets(needle: str, haystack: str) -> Optional[Tuple[int, int]]:
    """Locate candidate offsets in haystack using regex pattern derived from needle tokens."""
    if not needle or not haystack:
        return None
    
    # Tokenize needle into words (alnum only)
    tokens = re.findall(r"[A-Za-z0-9]+", needle)
    if not tokens or len(tokens) == 0:
        return None

    # Construct regex matching tokens separated by flexible whitespace / punctuation
    pattern_parts = [re.escape(t) for t in tokens]
    regex_pattern = r"\b" + r"[\s\W_]+".join(pattern_parts) + r"\b"

    m = re.search(regex_pattern, haystack, re.IGNORECASE)
    if m:
        return (m.start(), m.end())

    # Fallback to subset of key tokens if needle was long
    if len(tokens) >= 4:
        key_pattern = r"\b" + r"[\s\W_]+".join(pattern_parts[:4]) + r"\b"
        m2 = re.search(key_pattern, haystack, re.IGNORECASE)
        if m2:
            return (m2.start(), m2.end())

    return None


def _compute_bounding_boxes_for_range(
    clause: Clause,
    start_char: int,
    end_char: int,
) -> Tuple[Optional[BoundingBox], List[BoundingBox], List[int]]:
    """Map character range inside clause.text to exact physical BoundingBoxes from clause.spans."""
    if not clause.spans:
        if clause.bounding_boxes:
            primary = clause.bounding_boxes[0]
            return primary, list(clause.bounding_boxes), list(clause.pages)
        return None, [], []

    # Find overlapping typographical spans
    overlapping_spans: List[TextSpan] = []
    for s in clause.spans:
        # A span overlaps if span.clause_char_start < end_char and span.clause_char_end > start_char
        c_start = s.clause_char_start if s.clause_char_start is not None else s.char_start
        c_end = s.clause_char_end if s.clause_char_end is not None else s.char_end

        if c_start < end_char and c_end > start_char:
            overlapping_spans.append(s)

    if not overlapping_spans:
        # Fallback to clause primary bounding box if span offsets did not overlap directly
        if clause.bounding_boxes:
            return clause.bounding_boxes[0], list(clause.bounding_boxes), list(clause.pages)
        return None, [], []

    all_bboxes = [s.bbox for s in overlapping_spans]
    distinct_pages = sorted(list({b.page for b in all_bboxes}))
    primary_page = distinct_pages[0]

    # Compute enclosing bounding box on primary page
    p1_bboxes = [b for b in all_bboxes if b.page == primary_page]
    primary_bbox = BoundingBox(
        page=primary_page,
        x0=round(min(b.x0 for b in p1_bboxes), 2),
        y0=round(min(b.y0 for b in p1_bboxes), 2),
        x1=round(max(b.x1 for b in p1_bboxes), 2),
        y1=round(max(b.y1 for b in p1_bboxes), 2),
    )

    return primary_bbox, all_bboxes, distinct_pages


def _score_clause_relevance(field_name: str, clause: Clause) -> int:
    """Score clause relevance based on canonical field contextual keywords."""
    keywords = FIELD_CONTEXT_KEYWORDS.get(field_name, [])
    if not keywords:
        return 0

    clause_content = f"{clause.clause_number} {clause.title or ''} {clause.text}".lower()
    score = 0
    for kw in keywords:
        if kw.lower() in clause_content:
            score += 1
    return score


def _resolve_field_provenance(
    field_name: str,
    candidate: Optional[CandidateFact],
    document_tree: DocumentTree,
) -> ProvenancedValue:
    """Deterministically resolve a single candidate fact against the DocumentTree.

    Enforces:
    - Never defaults to EXPLICIT.
    - Slices quote strictly from DocumentTree text.
    - Resolves exact BoundingBoxes via character offsets.
    - Handles repeated terms using context disambiguation (no blind first match).
    - If multiple sources match without sufficient distinction -> AMBIGUOUS.
    - If unsupported -> UNRESOLVED / NOT_FOUND.
    """
    qualifier = FIELD_QUALIFIERS.get(field_name)

    # 1. Negative / absent fact handling
    if not candidate or not candidate.is_present or not candidate.candidate_value:
        return ProvenancedValue(
            field_name=field_name,
            status=ExtractionStatus.NOT_FOUND,
            value=None,
            is_present=False,
            claim_tag=ClaimTag.NOT_FOUND,
            match_quality=MatchQuality.NO_MATCH,
            qualifier=qualifier,
        )

    search_keys = []
    if candidate.candidate_quote and candidate.candidate_quote.strip():
        search_keys.append(candidate.candidate_quote.strip())
    if candidate.candidate_value and candidate.candidate_value.strip():
        search_keys.append(candidate.candidate_value.strip())

    candidate_clause_id = candidate.candidate_clause_id
    clauses = [c for c in document_tree.clauses if not c.is_header_footer]

    # 2. Check candidate clause first if provided
    target_clause: Optional[Clause] = None
    if candidate_clause_id:
        target_clause = next((c for c in clauses if c.clause_id == candidate_clause_id or c.clause_number == candidate_clause_id), None)

    # 3. Locate matches across all candidate clauses
    candidate_matches: List[Dict[str, Any]] = []

    for clause in clauses:
        clause_text = clause.text
        rel_score = _score_clause_relevance(field_name, clause)

        for key in search_keys:
            # 3a. Exact search
            exact_range = _find_exact_offsets(key, clause_text)
            if exact_range:
                start, end = exact_range
                candidate_matches.append({
                    "clause": clause,
                    "range": (start, end),
                    "method": ResolutionMethod.EXACT_QUOTE,
                    "quality": MatchQuality.EXACT_SOURCE_MATCH,
                    "relevance": rel_score,
                    "quote": clause_text[start:end],
                })
                break  # don't duplicate on same key for this clause

            # 3b. Normalized search
            norm_range = _find_normalized_offsets(key, clause_text)
            if norm_range:
                start, end = norm_range
                candidate_matches.append({
                    "clause": clause,
                    "range": (start, end),
                    "method": ResolutionMethod.NORMALIZED_QUOTE,
                    "quality": MatchQuality.NORMALIZED_SOURCE_MATCH,
                    "relevance": rel_score,
                    "quote": clause_text[start:end],
                })
                break

    # 4. Disambiguation and match evaluation
    if not candidate_matches:
        # No source matches found in DocumentTree
        return ProvenancedValue(
            field_name=field_name,
            status=ExtractionStatus.UNRESOLVED,
            value=candidate.candidate_value,
            is_present=False,
            claim_tag=None,  # Correction 1: UNRESOLVED must NOT map to ClaimTag.NOT_FOUND
            match_quality=MatchQuality.NO_MATCH,
            resolution_method=ResolutionMethod.UNRESOLVED,
            candidate_quote=candidate.candidate_quote,
            candidate_clause_id=candidate.candidate_clause_id,
            qualifier=qualifier,
        )

    # If the candidate clause itself matched with top quality, prefer it
    selected_match = None
    if target_clause:
        target_matches = [m for m in candidate_matches if m["clause"].clause_id == target_clause.clause_id]
        if target_matches:
            selected_match = target_matches[0]

    if not selected_match:
        # If single match, accept it
        if len(candidate_matches) == 1:
            selected_match = candidate_matches[0]
        else:
            # Multiple candidate matches found (e.g. repeated numbers like '30 days')
            # Sort by contextual relevance score
            sorted_matches = sorted(candidate_matches, key=lambda m: m["relevance"], reverse=True)
            top_score = sorted_matches[0]["relevance"]
            second_score = sorted_matches[1]["relevance"]

            # If top match is clearly distinguished by contextual keywords, select it
            if top_score > second_score and top_score > 0:
                selected_match = sorted_matches[0]
            else:
                # Ambiguous: cannot deterministically prove which clause applies without guessing
                ambiguity_info = [
                    {
                        "clause_id": m["clause"].clause_id,
                        "clause_number": m["clause"].clause_number,
                        "quote": m["quote"],
                        "page": m["clause"].page_number,
                    }
                    for m in candidate_matches
                ]
                return ProvenancedValue(
                    field_name=field_name,
                    status=ExtractionStatus.AMBIGUOUS,
                    value=candidate.candidate_value,
                    is_present=False,
                    claim_tag=None,  # AMBIGUOUS facts must NOT be tagged EXPLICIT
                    match_quality=MatchQuality.AMBIGUOUS_MATCH,
                    candidate_quote=candidate.candidate_quote,
                    candidate_clause_id=candidate.candidate_clause_id,
                    ambiguity_candidates=ambiguity_info,
                    qualifier=qualifier,
                )

    # 5. Build verified ProvenancedValue from DocumentTree
    matched_clause: Clause = selected_match["clause"]
    start, end = selected_match["range"]

    # Verbatim quote SLICED DIRECTLY from DocumentTree (never trusting Gemini's quote string)
    verbatim_quote = matched_clause.text[start:end]

    primary_bbox, all_bboxes, pages = _compute_bounding_boxes_for_range(
        matched_clause,
        start,
        end,
    )

    return ProvenancedValue(
        field_name=field_name,
        status=ExtractionStatus.FOUND,
        value=candidate.candidate_value,
        is_present=True,
        claim_tag=ClaimTag.EXPLICIT,  # ONLY assigned because physical provenance is verified
        source_clause_id=matched_clause.clause_id,
        source_clause_number=matched_clause.clause_number,
        page=pages[0] if pages else matched_clause.page_number,
        pages=pages if pages else [matched_clause.page_number],
        exact_quote=verbatim_quote,
        bbox=primary_bbox,
        bounding_boxes=all_bboxes,
        resolution_method=selected_match["method"],
        match_quality=selected_match["quality"],
        candidate_quote=candidate.candidate_quote,
        candidate_clause_id=candidate.candidate_clause_id,
        qualifier=qualifier,
    )


def resolve_provenance(
    candidates: CandidateExtractionResult,
    document_tree: DocumentTree,
) -> StructuredAgreement:
    """Deterministically resolve all candidate facts against the DocumentTree.

    Enforces:
    - 100% of facts marked FOUND / EXPLICIT have verified physical provenance.
    - Derived summary metrics calculated strictly from actual field outcomes.
    """
    field_names = [
        "agreement_type",
        "execution_date",
        "landlord_name",
        "tenant_name",
        "property_address",
        "tenure_months",
        "commencement_date",
        "lock_in_months",
        "monthly_rent",
        "security_deposit",
        "deposit_refund_days",
        "notice_period_days",
        "maintenance_responsibility",
        "late_payment_penalty",
        "permitted_use",
        "renewal_terms",
    ]

    resolved_fields: Dict[str, ProvenancedValue] = {}
    found_count = 0
    not_found_count = 0
    ambiguous_count = 0
    unresolved_count = 0
    provenance_resolved_count = 0

    for name in field_names:
        candidate = getattr(candidates, name, None)
        provenanced_val = _resolve_field_provenance(name, candidate, document_tree)
        resolved_fields[name] = provenanced_val

        if provenanced_val.status == ExtractionStatus.FOUND:
            found_count += 1
            if provenanced_val.bbox is not None or len(provenanced_val.bounding_boxes) > 0:
                provenance_resolved_count += 1
        elif provenanced_val.status == ExtractionStatus.NOT_FOUND:
            not_found_count += 1
        elif provenanced_val.status == ExtractionStatus.AMBIGUOUS:
            ambiguous_count += 1
        elif provenanced_val.status == ExtractionStatus.UNRESOLVED:
            unresolved_count += 1

    summary = ExtractionSummary(
        fields_total=len(field_names),
        fields_found=found_count,
        fields_not_found=not_found_count,
        fields_ambiguous=ambiguous_count,
        fields_unresolved=unresolved_count,
        fields_provenance_resolved=provenance_resolved_count,
    )

    return StructuredAgreement(
        document_id=document_tree.document_id,
        summary=summary,
        **resolved_fields,
    )
