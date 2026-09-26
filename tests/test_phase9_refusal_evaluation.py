"""Phase 9 Refusal Engine Rigor and Fallback Refusal Evaluation.

Tests:
- Scanned PDF triggers UNREADABLE_DOCUMENT refusal.
- Legal advice questions trigger LEGAL_ADVICE refusal.
- Out of scope questions trigger OUT_OF_SCOPE refusal.
- Absent agreement terms trigger NOT_FOUND / NO_SUPPORTING_PASSAGE.
- Zero conversion of refusal states into confident factual assertions.
"""

import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.models.document import DocumentTree
from backend.models.qa import AnswerStatus, QuestionType
from backend.models.verification import ClaimTag, RefusalCategory, VerificationStatus
from backend.verification.refusal_engine import RefusalEngine
from backend.retrieval.qa_service import QAService
from backend.verification.verification_gate import VerificationGate


@pytest.fixture(scope="session")
def scanned_doc_tree():
    path = "tests/fixtures/sparse_scanned.pdf"
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    return DocumentTree(
        document_id="doc_scanned",
        filename="sparse_scanned.pdf",
        sha256_hash="hash",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=[],
        warnings=warnings,
    )


def test_refusal_engine_scanned_pdf(scanned_doc_tree):
    """Document with zero readable text triggers UNREADABLE_DOCUMENT refusal."""
    refusal_engine = RefusalEngine()
    result = refusal_engine.check_document_refusal(scanned_doc_tree)
    assert result == RefusalCategory.UNREADABLE_DOCUMENT


@pytest.mark.asyncio
async def test_refusal_engine_legal_advice():
    """Legal advice queries must be refused with LEGAL_ADVICE refusal."""
    qa_service = QAService()
    doc_tree = DocumentTree(
        document_id="test",
        filename="test.pdf",
        sha256_hash="h",
        file_size_bytes=100,
        page_count=1,
        pages=[],
        clauses=[],
    )
    legal_advice_queries = [
        "Is the termination clause legally enforceable?",
        "Can I sue the landlord?",
        "What should the tenant do if the landlord refuses the deposit?",
    ]
    for q in legal_advice_queries:
        response = await qa_service.answer_question(
            document_tree=doc_tree,
            question=q,
        )
        assert response.status == AnswerStatus.REFUSED
        assert response.question_type == QuestionType.LEGAL_ADVICE
        # Must not fabricate legal conclusions
        assert "legal advice" in response.answer.lower() or "cannot provide legal advice" in response.answer.lower()


@pytest.mark.asyncio
async def test_refusal_engine_out_of_scope():
    """Unrelated questions must be refused with OUT_OF_SCOPE refusal."""
    qa_service = QAService()
    doc_tree = DocumentTree(
        document_id="test",
        filename="test.pdf",
        sha256_hash="h",
        file_size_bytes=100,
        page_count=1,
        pages=[],
        clauses=[],
    )
    out_of_scope_queries = [
        "What is the capital of India?",
        "Explain Section 106 of Transfer of Property Act",
        "What does the law say about this agreement?",
    ]
    for q in out_of_scope_queries:
        response = await qa_service.answer_question(
            document_tree=doc_tree,
            question=q,
        )
        assert response.status == AnswerStatus.REFUSED
        assert response.question_type == QuestionType.OUT_OF_SCOPE
