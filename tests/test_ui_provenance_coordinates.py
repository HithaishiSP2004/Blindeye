import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.engine.clause_segmenter import segment_clauses
from backend.extraction.structured_extractor import extract_candidate_facts
from backend.extraction.provenance_resolver import resolve_provenance
from backend.models.document import DocumentTree
from tests.generate_fixtures import create_golden_agreement_pdf
import os


@pytest.fixture(scope="session")
def golden_pdf_tree():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        content = f.read()
    pages, status, warnings = parse_pdf_geometry(content)
    clauses = segment_clauses(pages)
    return DocumentTree(
        document_id="doc_test_coords",
        filename="golden_agreement.pdf",
        sha256_hash="hash",
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


@pytest.mark.asyncio
async def test_provenance_bounding_boxes_alignment(golden_pdf_tree):
    """Verify that backend bounding boxes for verified facts strictly align with actual clause geometry."""
    candidates = await extract_candidate_facts(golden_pdf_tree)
    sa = resolve_provenance(candidates, golden_pdf_tree)

    # 1. Monthly Rent -> Page 1, Clause 2.1 (y0 ~ 270)
    rent = sa.monthly_rent
    assert rent.bbox is not None
    assert rent.page == 1
    assert 260.0 <= rent.bbox.y0 <= 280.0
    assert 275.0 <= rent.bbox.y1 <= 295.0
    p1 = golden_pdf_tree.pages[0]
    # Check normalized coordinate validity
    assert 0.0 <= rent.bbox.x0 / p1.width <= 1.0
    assert 0.0 <= rent.bbox.y0 / p1.height <= 1.0
    assert rent.source_clause_number == "2.1"

    # 2. Security Deposit -> Page 1, Clause 2.2 (y0 ~ 315)
    deposit = sa.security_deposit
    assert deposit.bbox is not None
    assert deposit.page == 1
    assert 305.0 <= deposit.bbox.y0 <= 325.0
    assert deposit.source_clause_number == "2.2"

    # 3. Agreement Tenure -> Page 1, Clause 1 (y0 ~ 180-210)
    tenure = sa.tenure_months
    assert tenure.bbox is not None
    assert tenure.page == 1
    assert 180.0 <= tenure.bbox.y0 <= 215.0
    assert tenure.source_clause_number == "1"

    # 4. Commencement Date -> Page 1, Clause 1 (y0 ~ 180-210)
    commence = sa.commencement_date
    assert commence.bbox is not None
    assert commence.page == 1
    assert 180.0 <= commence.bbox.y0 <= 215.0
    assert commence.source_clause_number == "1"

    # 5. Notice Period -> Page 2, Clause 4 (y0 ~ 140)
    notice = sa.notice_period_days
    assert notice.bbox is not None
    assert notice.page == 2
    assert 130.0 <= notice.bbox.y0 <= 155.0
    p2 = golden_pdf_tree.pages[1]
    assert 0.0 <= notice.bbox.x0 / p2.width <= 1.0
    assert 0.0 <= notice.bbox.y0 / p2.height <= 1.0
    assert notice.source_clause_number == "4"

    # 6. Maintenance Responsibility -> Clause 3 (Spanning Pages 1 & 2)
    maint = sa.maintenance_responsibility
    assert maint.bbox is not None
    assert maint.source_clause_number == "3"
    # Find Clause 3 in DocumentTree
    c3 = next(c for c in golden_pdf_tree.clauses if c.clause_number == "3")
    assert 1 in c3.pages
    assert 2 in c3.pages
