import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.models.document import DocumentTree
from backend.models.qa import AnswerStatus
from backend.retrieval.clause_retriever import ClauseRetriever
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


def test_clause_3_multi_page_retrieval(golden_doc_tree):
    # Clause 3 spans page 1 and page 2 in the golden agreement fixture
    retriever = ClauseRetriever()
    res = retriever.retrieve_clause("What does Clause 3 say about repairs?", golden_doc_tree)
    assert res.is_found is True
    assert res.status == AnswerStatus.ANSWERED
    assert res.clause is not None
    assert res.clause.clause_number == "3"

    # Multi-page citations (Correction 19)
    assert len(res.evidence) >= 1
    pages = [cit.page for cit in res.evidence]
    # Clause 3 in golden agreement spans across pages 1 and 2
    if len(res.clause.pages) > 1:
        assert 1 in pages
        assert 2 in pages


def test_clause_4_retrieval(golden_doc_tree):
    retriever = ClauseRetriever()
    res = retriever.retrieve_clause("What does Clause 4 say?", golden_doc_tree)
    assert res.is_found is True
    assert res.status == AnswerStatus.ANSWERED
    assert res.clause.clause_number == "4"
    assert len(res.evidence) == 1
    assert res.evidence[0].page == 2


def test_absent_clause_not_found(golden_doc_tree):
    # Missing clause must return NOT_FOUND (Correction 17)
    retriever = ClauseRetriever()
    res = retriever.retrieve_clause("What does Clause 99 say?", golden_doc_tree)
    assert res.is_found is False
    assert res.status == AnswerStatus.NOT_FOUND
    assert len(res.evidence) == 0
    assert "does not contain Clause 99" in res.answer
