import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.models.document import DocumentTree
from backend.retrieval.evidence_selector import EvidenceSelector
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_doc_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, parsing_status, warnings = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="test_doc",
        filename="golden_agreement.pdf",
        sha256_hash="dummy",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
    )


def test_select_sentence_level_quote(golden_doc_tree):
    selector = EvidenceSelector()
    clause_3 = next(c for c in golden_doc_tree.clauses if c.clause_number == "3")
    citations = selector.select_evidence(clause_3, "Who pays for minor leakages?", golden_doc_tree)
    assert len(citations) >= 1
    primary = citations[0]
    # Check that quote contains the relevant sentence and is verbatim from clause text
    assert primary.quote in clause_3.text
    assert "minor" in primary.quote.lower() or "repair" in primary.quote.lower()


def test_verbatim_quote_rule(golden_doc_tree):
    # Correction 10: The final quote MUST be sliced from original DocumentTree text
    selector = EvidenceSelector()
    clause_4 = next(c for c in golden_doc_tree.clauses if c.clause_number == "4")
    citations = selector.select_evidence(clause_4, "termination notice", golden_doc_tree)
    assert len(citations) == 1
    assert citations[0].quote in clause_4.text
    assert citations[0].page == 2
    assert citations[0].bbox is not None
