import os
import pytest
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.extraction.provenance_resolver import resolve_provenance
from backend.extraction.structured_extractor import extract_candidate_facts
from backend.models.document import DocumentTree
from backend.models.qa import AnswerStatus
from backend.retrieval.field_lookup import FieldLookup
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


@pytest.fixture
async def golden_structured_agreement(golden_doc_tree):
    candidates = await extract_candidate_facts(golden_doc_tree)
    return resolve_provenance(candidates, golden_doc_tree)


@pytest.mark.asyncio
async def test_canonical_rent_lookup(golden_doc_tree, golden_structured_agreement):
    lookup = FieldLookup()
    res = lookup.lookup("What is the monthly rent?", golden_structured_agreement, golden_doc_tree)
    assert res.is_matched is True
    assert res.field_name == "monthly_rent"
    assert res.status == AnswerStatus.ANSWERED
    assert len(res.evidence) == 1
    assert "35,000" in res.evidence[0].quote
    assert res.evidence[0].page == 1
    assert res.evidence[0].clause_number == "2.1"
    assert res.evidence[0].bbox is not None


@pytest.mark.asyncio
async def test_canonical_deposit_lookup(golden_doc_tree, golden_structured_agreement):
    lookup = FieldLookup()
    res = lookup.lookup("How much is the security deposit?", golden_structured_agreement, golden_doc_tree)
    assert res.is_matched is True
    assert res.field_name == "security_deposit"
    assert res.status == AnswerStatus.ANSWERED
    assert "1,00,000" in res.evidence[0].quote


@pytest.mark.asyncio
async def test_canonical_address_not_found(golden_doc_tree, golden_structured_agreement):
    lookup = FieldLookup()
    res = lookup.lookup("What is the property address?", golden_structured_agreement, golden_doc_tree)
    assert res.is_matched is True
    assert res.field_name == "property_address"
    assert res.status == AnswerStatus.NOT_FOUND
    assert len(res.evidence) == 0
    assert "does not provide a property address" in res.answer


@pytest.mark.asyncio
async def test_canonical_lock_in_not_found(golden_doc_tree, golden_structured_agreement):
    lookup = FieldLookup()
    res = lookup.lookup("Is there a lock-in period?", golden_structured_agreement, golden_doc_tree)
    assert res.is_matched is True
    assert res.field_name == "lock_in_period"
    assert res.status == AnswerStatus.NOT_FOUND
    assert len(res.evidence) == 0
    assert "lock-in" in res.answer.lower()
