"""Phase 9 Provenance Integrity and Complete Evidence Chain Audit.

Enforces Amendment 3:
- Complete provenance chain:
  AdvocatePack citation -> verified claim / contradiction -> DocumentTree source span -> exact source quote + page + geometry.
- Every Advocate Pack citation resolves to original physical DocumentTree evidence.
- No reconstructed, generated, paraphrased, or synthesized quote is used as source evidence.
- Mathematical spatial validation: 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height.
"""

import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.engine.clause_segmenter import segment_clauses
from backend.models.document import DocumentTree
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.extraction.provenance_resolver import resolve_provenance
from backend.verification.verification_gate import VerificationGate
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator
from backend.advocate.pack_builder import build_advocate_pack


@pytest.fixture(scope="session")
def golden_doc_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_golden_tree",
        filename="golden_agreement.pdf",
        sha256_hash="dummy_hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


def test_bounding_box_geometry_spatial_bounds(golden_doc_tree):
    """Verify all extracted text block and span bounding boxes stay strictly inside page bounds."""
    for page in golden_doc_tree.pages:
        p_w = page.width
        p_h = page.height
        assert p_w > 0
        assert p_h > 0

        for block in page.blocks:
            bbox = block.bbox
            assert bbox.page == page.page_number
            assert 0 <= bbox.x0 < bbox.x1 <= p_w, f"Block bbox x overflow: {bbox}"
            assert 0 <= bbox.y0 < bbox.y1 <= p_h, f"Block bbox y overflow: {bbox}"

            for span in block.spans:
                s_bbox = span.bbox
                assert 0 <= s_bbox.x0 <= s_bbox.x1 <= p_w, f"Span bbox x overflow: {s_bbox}"
                assert 0 <= s_bbox.y0 <= s_bbox.y1 <= p_h, f"Span bbox y overflow: {s_bbox}"


@pytest.mark.asyncio
async def test_advocate_pack_complete_provenance_chain(golden_doc_tree):
    """Amendment 3: Assert complete provenance chain from Advocate Pack down to DocumentTree."""
    candidates = _mock_extract_candidates(golden_doc_tree)
    structured_agreement = resolve_provenance(candidates, golden_doc_tree)
    gate = VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())
    veri_result = await gate.verify_agreement(structured_agreement, golden_doc_tree)

    pack = build_advocate_pack(
        document_tree=golden_doc_tree,
        verification_result=veri_result,
        document_name="golden_agreement.pdf",
    )

    # Every footnote must resolve to exact verbatim text in DocumentTree
    assert len(pack.footnotes) > 0

    # Build full physical text corpus by page for substring verification
    page_texts = {p.page_number: " ".join(b.text for b in p.blocks) for p in golden_doc_tree.pages}

    for fn in pack.footnotes:
        assert fn.index >= 1
        assert fn.page_number in page_texts, f"Footnote page {fn.page_number} not in document"
        p_text = page_texts[fn.page_number]

        # The footnote's exact_quote MUST exist in DocumentTree text (no paraphrasing)
        # Normalize whitespace for comparison
        clean_quote = " ".join(fn.exact_quote.split())
        clean_page_text = " ".join(p_text.split())
        assert clean_quote in clean_page_text, (
            f"Provenance failure: Quote '{clean_quote}' not found verbatim on Page {fn.page_number}."
        )

        # Footnote must carry valid bounding boxes
        for box in fn.bounding_boxes:
            assert box.page == fn.page_number
            assert box.x0 < box.x1
            assert box.y0 < box.y1
