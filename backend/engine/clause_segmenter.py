import re
from typing import List, Optional, Tuple
from backend.models.document import Clause, PageData


# Regex patterns for clause boundary detection
RE_HIERARCHICAL = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)[\.\:\-\s]\s*(.*)", re.DOTALL)
RE_NUMBERED = re.compile(r"^(?:(?:Clause|Article|Section|Item)\s+)?(\d{1,2})[\.\:\-\)]\s*(.*)", re.IGNORECASE | re.DOTALL)
RE_LETTERED = re.compile(r"^(?:\(([a-zA-Z]|[ivxIVX]+)\)|([a-zA-Z]|[ivxIVX]+)[\.\)])\s+(.*)", re.DOTALL)
RE_PREAMBLE_HEADING = re.compile(
    r"^(?:NOW\s+THIS\s+(?:AGREEMENT|DEED|INDENTURE)\s+WITNESSETH|WHEREAS|WITNESSETH|SCHEDULE\s+[A-Z0-9]+)",
    re.IGNORECASE,
)


def _match_clause_header(text: str) -> Optional[Tuple[str, Optional[str], int, bool]]:
    """Inspect text block start to detect clause numbers, titles, and hierarchy.

    Returns:
        Tuple of (clause_number, title_candidate, hierarchy_level, is_heading) or None
    """
    clean = text.strip()

    # 1. Check Hierarchical numbering e.g., '1.1', '2.3.1'
    m_hier = RE_HIERARCHICAL.match(clean)
    if m_hier:
        num = m_hier.group(1)
        level = len(num.split("."))
        rest = m_hier.group(2).strip()
        title = _extract_inline_title(rest)
        return (num, title, level, False)

    # 2. Check Standard numbered clause e.g., '1.', 'Clause 4:', '5)'
    m_num = RE_NUMBERED.match(clean)
    if m_num:
        num = m_num.group(1)
        rest = m_num.group(2).strip()
        title = _extract_inline_title(rest)
        return (num, title, 1, False)

    # 3. Check Subclause lettered/roman e.g., '(a)', '(ii)', 'b)'
    m_let = RE_LETTERED.match(clean)
    if m_let:
        num = m_let.group(1) or m_let.group(2)
        rest = m_let.group(3).strip()
        return (f"({num})", None, 2, False)

    # 4. Check Legal preamble or formal section headings
    if RE_PREAMBLE_HEADING.match(clean):
        first_line = clean.split("\n")[0][:60]
        return ("HEADING", first_line, 1, True)

    # 5. Check Standalone uppercase or title-case section headings
    if len(clean) < 65 and "\n" not in clean:
        if clean.isupper() and any(k in clean for k in ["RENT", "LICENSE", "AGREEMENT", "TERMS", "CONDITIONS", "DEPOSIT", "TERMINATION", "MAINTENANCE"]):
            return ("HEADING", clean, 1, True)

    return None


def _extract_inline_title(rest_of_text: str) -> Optional[str]:
    """Attempt to extract inline clause title (e.g. 'RENT AND CHARGES: The tenant shall...')."""
    if not rest_of_text:
        return None
    # Check colon or dash separator: e.g., 'SECURITY DEPOSIT: The licensee...'
    m_title = re.match(r"^([A-Z\s]{3,40}|[A-Z][a-zA-Z\s]{2,30})[\:\-\–]\s+", rest_of_text)
    if m_title:
        candidate = m_title.group(1).strip()
        if len(candidate) >= 3:
            return candidate
    return None


def segment_clauses(pages: List[PageData]) -> List[Clause]:
    """Segment layout text blocks into discrete, provenance-preserving Clause structures.

    Preserves source geometry and supports multi-page clause continuity.
    """
    clauses: List[Clause] = []
    active_clause: Optional[Clause] = None
    clause_counter = 0

    # Map of clause_number -> clause_id for resolving parent references (e.g. '1.1' -> '1')
    clause_registry = {}

    for page in pages:
        for block in page.blocks:
            clean_text = block.text.strip()
            if not clean_text:
                continue

            # Header / footer blocks are retained without interrupting clause flow
            if block.is_header_footer:
                hf_spans = [
                    s.model_copy(update={"clause_char_start": s.char_start, "clause_char_end": s.char_end})
                    for s in block.spans
                ]
                hf_clause = Clause(
                    clause_id=f"hf_p{page.page_number}_b{block.block_number}",
                    clause_number="HEADER/FOOTER",
                    title="Running Header/Footer",
                    text=clean_text,
                    page_number=page.page_number,
                    pages=[page.page_number],
                    bounding_boxes=[block.bbox],
                    spans=hf_spans,
                    source_block_ids=[block.block_id],
                    hierarchy_level=9,
                    is_header_footer=True,
                )
                clauses.append(hf_clause)
                continue

            header_match = _match_clause_header(clean_text)

            if header_match:
                # Close out active clause if any
                if active_clause:
                    clauses.append(active_clause)
                    active_clause = None

                clause_counter += 1
                num, title, level, is_heading = header_match
                clause_id = f"clause_p{page.page_number}_c{clause_counter}"

                # Resolve parent clause ID for hierarchical numbering e.g., '1.1' -> '1'
                parent_id = None
                if "." in num:
                    parent_num = ".".join(num.split(".")[:-1])
                    parent_id = clause_registry.get(parent_num)
                elif num.startswith("(") and active_clause is None and len(clauses) > 0:
                    # Look back for most recent numbered clause
                    for prev in reversed(clauses):
                        if not prev.is_header_footer and not prev.is_heading:
                            parent_id = prev.clause_id
                            break

                clause_registry[num] = clause_id

                init_spans = [
                    s.model_copy(update={"clause_char_start": s.char_start, "clause_char_end": s.char_end})
                    for s in block.spans
                ]

                active_clause = Clause(
                    clause_id=clause_id,
                    clause_number=num,
                    title=title,
                    text=clean_text,
                    page_number=page.page_number,
                    pages=[page.page_number],
                    bounding_boxes=[block.bbox],
                    spans=init_spans,
                    source_block_ids=[block.block_id],
                    parent_clause_id=parent_id,
                    hierarchy_level=level,
                    is_heading=is_heading,
                    is_uncertain=False,
                )
            else:
                # Continuation of current clause across lines or page boundary
                if active_clause:
                    offset = len(active_clause.text) + 1
                    active_clause.text += " " + clean_text
                    active_clause.bounding_boxes.append(block.bbox)
                    active_clause.source_block_ids.append(block.block_id)
                    if page.page_number not in active_clause.pages:
                        active_clause.pages.append(page.page_number)
                    for s in block.spans:
                        active_clause.spans.append(
                            s.model_copy(update={
                                "clause_char_start": offset + s.char_start,
                                "clause_char_end": offset + s.char_end,
                            })
                        )
                else:
                    # Preamble or opening paragraphs before Clause 1
                    clause_counter += 1
                    clause_id = f"clause_p{page.page_number}_c{clause_counter}"
                    preamble_spans = [
                        s.model_copy(update={"clause_char_start": s.char_start, "clause_char_end": s.char_end})
                        for s in block.spans
                    ]
                    active_clause = Clause(
                        clause_id=clause_id,
                        clause_number="PREAMBLE",
                        title="Preamble / Recitals",
                        text=clean_text,
                        page_number=page.page_number,
                        pages=[page.page_number],
                        bounding_boxes=[block.bbox],
                        spans=preamble_spans,
                        source_block_ids=[block.block_id],
                        hierarchy_level=1,
                        is_uncertain=True,
                    )

    # Append trailing active clause
    if active_clause:
        clauses.append(active_clause)

    return clauses
