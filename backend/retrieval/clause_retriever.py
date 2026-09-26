import re
from typing import Dict, List, Optional
from pydantic import BaseModel
from backend.models.document import BoundingBox, Clause, DocumentTree
from backend.models.qa import AnswerStatus, EvidenceCitation


class ClauseLookupResult(BaseModel):
    """Result of searching for a specific clause by number or heading."""

    is_found: bool
    clause: Optional[Clause] = None
    target_clause_str: Optional[str] = None
    status: AnswerStatus
    answer: Optional[str] = None
    evidence: List[EvidenceCitation] = []


class ClauseRetriever:
    """Deterministic exact clause lookup over DocumentTree.clauses.

    Enforces Phase 5 Corrections:
    - Exact clause lookup remains deterministic (Correction 17).
    - If clause is absent: return NOT_FOUND cleanly without hallucinating (Correction 17 & 26).
    - Multi-page evidence: returns citations for each physical page spanned (Correction 19).
    - All coordinates and quotes sliced directly from DocumentTree (Correction 9 & 10).
    """

    def extract_target_clause_number(self, query: str) -> Optional[str]:
        """Extract clause or section number from natural language question."""
        m = re.search(
            r"\b(?:clause|section|article|point|cl\.?)\s*([0-9]+(?:\.[0-9]+)*|[a-zA-Z])\b",
            query,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()

        # Handle preamble
        if re.search(r"\bpreamble\b", query, re.IGNORECASE):
            return "Preamble"

        return None

    def retrieve_clause(
        self,
        query: str,
        document_tree: DocumentTree,
        target_number: Optional[str] = None,
    ) -> ClauseLookupResult:
        """Find the matching clause in DocumentTree and build coordinate citations."""
        target = target_number or self.extract_target_clause_number(query)
        if not target:
            return ClauseLookupResult(
                is_found=False,
                status=AnswerStatus.NOT_FOUND,
                answer="No specific clause reference was found in the question.",
                evidence=[],
            )

        norm_target = target.strip().lower()

        # Find matching clause in DocumentTree
        matched_clause: Optional[Clause] = None
        for c in document_tree.clauses:
            if c.is_header_footer:
                continue
            c_num = (c.clause_number or "").strip().lower()
            # Direct match e.g. "3" == "3", "2.1" == "2.1", "preamble" in title or num
            if c_num == norm_target or f"clause {norm_target}" == c_num:
                matched_clause = c
                break
            if norm_target == "preamble" and ("preamble" in (c.title or "").lower() or c_num == "preamble"):
                matched_clause = c
                break

        # If not found yet, try prefix match or title search
        if not matched_clause:
            for c in document_tree.clauses:
                if c.is_header_footer:
                    continue
                c_num = (c.clause_number or "").strip().lower()
                if c_num.startswith(norm_target) and len(c_num) - len(norm_target) <= 2:
                    matched_clause = c
                    break

        # If clause still not found -> NOT_FOUND (Correction 17)
        if not matched_clause:
            return ClauseLookupResult(
                is_found=False,
                target_clause_str=target,
                status=AnswerStatus.NOT_FOUND,
                answer=f"The agreement does not contain Clause {target}.",
                evidence=[],
            )

        # Build citations for the clause (supporting multi-page clauses, Correction 19)
        citations = self._build_clause_citations(matched_clause, document_tree)

        clause_label = f"Clause {matched_clause.clause_number}" if matched_clause.clause_number else "Clause"
        if matched_clause.title:
            clause_label += f" ({matched_clause.title})"

        answer_text = f"{clause_label}: {matched_clause.text}"

        return ClauseLookupResult(
            is_found=True,
            clause=matched_clause,
            target_clause_str=target,
            status=AnswerStatus.ANSWERED,
            answer=answer_text,
            evidence=citations,
        )

    def _build_clause_citations(
        self,
        clause: Clause,
        document_tree: DocumentTree,
    ) -> List[EvidenceCitation]:
        """Build precise, page-specific citations for a clause, accounting for multi-page clauses."""
        pages_spanned = clause.pages if clause.pages else [clause.page_number]

        # Map block IDs to actual text blocks for precise coordinate bounding boxes
        block_id_map = {}
        for p in document_tree.pages:
            for b in p.blocks:
                block_id_map[b.block_id] = b

        citations: List[EvidenceCitation] = []

        if len(pages_spanned) <= 1:
            # Single page clause
            page_num = pages_spanned[0] if pages_spanned else clause.page_number
            bbox = clause.bounding_boxes[0] if clause.bounding_boxes else None
            citations.append(
                EvidenceCitation(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page=page_num,
                    quote=clause.text,
                    bbox=bbox,
                )
            )
            return citations

        # Multi-page clause: emit citation for each physical page spanned (Correction 19)
        for page_num in pages_spanned:
            # Collect blocks on this specific page
            page_blocks = [
                block_id_map[bid]
                for bid in clause.source_block_ids
                if bid in block_id_map and block_id_map[bid].page == page_num
            ]

            if page_blocks:
                page_text = " ".join(b.text for b in page_blocks if b.text)
                min_x = min(b.bbox.x0 for b in page_blocks)
                min_y = min(b.bbox.y0 for b in page_blocks)
                max_x = max(b.bbox.x1 for b in page_blocks)
                max_y = max(b.bbox.y1 for b in page_blocks)
                page_bbox = BoundingBox(page=page_num, x0=min_x, y0=min_y, x1=max_x, y1=max_y)
            else:
                page_text = clause.text
                page_bbox = clause.bounding_boxes[0] if clause.bounding_boxes else None

            citations.append(
                EvidenceCitation(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page=page_num,
                    quote=page_text,
                    bbox=page_bbox,
                )
            )

        return citations
