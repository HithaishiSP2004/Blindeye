import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.models.document import DocumentTree
from backend.retrieval.lexical_retriever import LexicalRetriever
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


def test_bm25_termination_retrieval(golden_doc_tree):
    retriever = LexicalRetriever()
    candidates = retriever.retrieve("What does the agreement say about termination?", golden_doc_tree)
    assert len(candidates) > 0
    top = candidates[0]
    # Clause 4 is termination
    assert top.clause.clause_number == "4"
    assert top.retrieval_score > 0
    assert "termination" in top.matched_terms or "say" in top.matched_terms or "agreement" in top.matched_terms


def test_bm25_repairs_retrieval(golden_doc_tree):
    retriever = LexicalRetriever()
    candidates = retriever.retrieve("Who is responsible for minor leakages?", golden_doc_tree)
    assert len(candidates) > 0
    top = candidates[0]
    # Clause 3 is maintenance and repairs
    assert top.clause.clause_number == "3"
    assert top.retrieval_score > 0


def test_bm25_irrelevant_query_empty(golden_doc_tree):
    retriever = LexicalRetriever()
    candidates = retriever.retrieve("quantum physics rocket propulsion interstellar spacecraft", golden_doc_tree)
    assert len(candidates) == 0
