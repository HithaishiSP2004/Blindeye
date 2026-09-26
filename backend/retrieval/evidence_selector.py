import re
from typing import List
from backend.models.document import BoundingBox, Clause, DocumentTree, TextBlock
from backend.models.qa import EvidenceCitation


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while preserving original punctuation and whitespace."""
    if not text:
        return []
    # Do not split on clause numbering like "3." or "2.1."
    raw_sentences = re.split(r"(?<=[a-zA-Z\)])[.!?]\s+|\n+", text)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 5]
    return sentences or [text.strip()]



class EvidenceSelector:
    """Extracts focused, sentence-level verbatim evidence quotes and coordinates from DocumentTree.

    Enforces Phase 5 Corrections:
    - Exact Quote Rule: Quote is sliced directly from DocumentTree text, NEVER LLM-generated (Correction 10).
    - Prefer exact sentence / relevant span over whole pages (Correction 18).
    - Multi-page evidence: emit citations for each physical page spanned (Correction 19).
    - Coordinates are locked to Phase 4 PDF points format (Correction 20).
    """

    def select_evidence(
        self,
        clause: Clause,
        query: str,
        document_tree: DocumentTree,
    ) -> List[EvidenceCitation]:
        """Select the most relevant sentence or span from the clause and build citations."""
        query_words = set(re.findall(r"\b[a-zA-Z0-9]+\b", query.lower()))
        sentences = _split_into_sentences(clause.text)

        # 1. Score each sentence by query term overlap
        best_sentence = clause.text
        best_score = -1

        if len(sentences) > 1:
            for s in sentences:
                s_words = set(re.findall(r"\b[a-zA-Z0-9]+\b", s.lower()))
                overlap = len(query_words.intersection(s_words))
                if overlap > best_score:
                    best_score = overlap
                    best_sentence = s

        # If sentence overlap score is positive, use best sentence; otherwise use clause text
        selected_quote = best_sentence if best_score > 0 else clause.text

        # 2. Map blocks to pages for coordinate resolution
        block_id_map = {}
        for p in document_tree.pages:
            for b in p.blocks:
                block_id_map[b.block_id] = b

        pages_spanned = clause.pages if clause.pages else [clause.page_number]

        # Single page case
        if len(pages_spanned) <= 1:
            page_num = pages_spanned[0] if pages_spanned else clause.page_number
            # Find specific block containing the quote, if possible
            best_bbox = clause.bounding_boxes[0] if clause.bounding_boxes else None
            for bid in clause.source_block_ids:
                b = block_id_map.get(bid)
                if b and selected_quote in b.text:
                    best_bbox = b.bbox
                    break

            return [
                EvidenceCitation(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page=page_num,
                    quote=selected_quote,
                    bbox=best_bbox,
                )
            ]

        # Multi-page case: emit citation for each page touched (Correction 19)
        citations: List[EvidenceCitation] = []
        for page_num in pages_spanned:
            page_blocks: List[TextBlock] = [
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
                # Check if selected sentence is entirely within this page
                quote_for_page = selected_quote if selected_quote in page_text else page_text
            else:
                quote_for_page = selected_quote
                page_bbox = clause.bounding_boxes[0] if clause.bounding_boxes else None

            citations.append(
                EvidenceCitation(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page=page_num,
                    quote=quote_for_page,
                    bbox=page_bbox,
                )
            )

        return citations
