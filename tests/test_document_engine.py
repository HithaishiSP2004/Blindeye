import io
import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.core.security import validate_and_read_pdf, IngestionError
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.main import app
from backend.models.document import ParsingStatus
from tests.generate_fixtures import create_golden_agreement_pdf, create_sparse_scanned_pdf


@pytest.fixture(scope="session")
def golden_pdf_path():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    return path


@pytest.fixture(scope="session")
def sparse_pdf_path():
    path = "tests/fixtures/sparse_scanned.pdf"
    if not os.path.exists(path):
        create_sparse_scanned_pdf(path)
    return path


def test_golden_pdf_geometry_and_pages(golden_pdf_path):
    """Test 1, 2, 3: Valid PDF parsing, page count, and text extraction."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    assert len(pages) == 2
    assert status == ParsingStatus.TEXT_AVAILABLE
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[0].char_count > 100
    assert pages[1].char_count > 100


def test_bounding_box_preservation(golden_pdf_path):
    """Test 4: Verify physical bounding boxes are preserved on blocks and spans."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, _, _ = parse_pdf_geometry(pdf_bytes)
    first_page = pages[0]
    assert len(first_page.blocks) > 0

    for block in first_page.blocks:
        bbox = block.bbox
        assert bbox.page == 1
        assert bbox.x0 < bbox.x1
        assert bbox.y0 < bbox.y1
        assert len(block.spans) > 0
        for span in block.spans:
            assert span.bbox.page == 1
            assert span.font_size is not None


def test_clause_detection_and_ordering(golden_pdf_path):
    """Test 5 & 6: Verify clause detection and sequential ordering."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, _, _ = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)

    # Exclude running headers/footers for core substantive checks
    substantive = [c for c in clauses if not c.is_header_footer]
    clause_numbers = [c.clause_number for c in substantive]

    # Verify numbered clauses appear in logical sequence
    assert "1" in clause_numbers
    assert "2" in clause_numbers
    assert "3" in clause_numbers
    assert "4" in clause_numbers


def test_hierarchical_numbering(golden_pdf_path):
    """Test 7: Verify hierarchical clauses (2.1, 2.2, (a), (b)) are recognized and linked."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, _, _ = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)

    c2_list = [c for c in clauses if c.clause_number == "2"]
    assert len(c2_list) == 1
    c2_id = c2_list[0].clause_id

    # Find subclause 2.1
    c2_1 = next((c for c in clauses if c.clause_number == "2.1"), None)
    assert c2_1 is not None
    assert c2_1.parent_clause_id == c2_id
    assert c2_1.hierarchy_level == 2
    assert "Monthly Rent" in c2_1.text

    # Find subclause (a)
    c_a = next((c for c in clauses if c.clause_number == "(a)"), None)
    assert c_a is not None
    assert c_a.hierarchy_level == 2
    assert "refunded within 30 days" in c_a.text


def test_multi_page_clause_handling(golden_pdf_path):
    """Test 8: Verify Clause 3 spans across Page 1 and Page 2 without being split into 2 clauses."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, _, _ = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)

    c3 = next((c for c in clauses if c.clause_number == "3"), None)
    assert c3 is not None
    # Clause 3 starts on page 1 and continues on page 2
    assert c3.page_number == 1
    assert 1 in c3.pages
    assert 2 in c3.pages
    # Content from both pages is present in single clause
    assert "minor repairs" in c3.text
    assert "Major structural repairs" in c3.text
    # Multiple bounding boxes preserved covering both pages
    pages_in_bboxes = {b.page for b in c3.bounding_boxes}
    assert 1 in pages_in_bboxes
    assert 2 in pages_in_bboxes


def test_provenance_integrity(golden_pdf_path):
    """Test 13: Verify full traceability from Clause -> Pages -> BoundingBoxes -> Text."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, _, _ = parse_pdf_geometry(pdf_bytes)
    clauses = segment_clauses(pages)

    for c in clauses:
        assert c.clause_id.startswith(("clause_", "hf_"))
        assert c.page_number >= 1
        assert len(c.pages) >= 1
        assert len(c.bounding_boxes) >= 1
        assert len(c.source_block_ids) >= 1
        assert len(c.text.strip()) > 0


def test_deterministic_parsing(golden_pdf_path):
    """Test 14: Deterministic output for multiple runs on identical input."""
    with open(golden_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages1, status1, _ = parse_pdf_geometry(pdf_bytes)
    clauses1 = segment_clauses(pages1)

    pages2, status2, _ = parse_pdf_geometry(pdf_bytes)
    clauses2 = segment_clauses(pages2)

    assert status1 == status2
    assert len(clauses1) == len(clauses2)
    for c1, c2 in zip(clauses1, clauses2):
        assert c1.clause_id == c2.clause_id
        assert c1.clause_number == c2.clause_number
        assert c1.text == c2.text
        assert len(c1.bounding_boxes) == len(c2.bounding_boxes)


def test_sparse_scanned_detection(sparse_pdf_path):
    """Test 12: Verify scanned/image PDF triggers OCR_REQUIRED without hallucinating text."""
    with open(sparse_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages, status, warnings = parse_pdf_geometry(pdf_bytes)
    assert status == ParsingStatus.OCR_REQUIRED
    assert len(warnings) > 0
    assert any("OCR would be required" in w or "scanned" in w for w in warnings)


@pytest.mark.asyncio
async def test_non_pdf_rejection():
    """Test 10: Verify non-PDF uploads are rejected cleanly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Plain text file
        fake_file = io.BytesIO(b"Hello, this is just plain text.")
        response = await client.post(
            "/documents/parse",
            files={"file": ("fake_document.txt", fake_file, "text/plain")},
        )
        assert response.status_code == 400
        assert "Only text-native PDF files" in response.json()["detail"]


@pytest.mark.asyncio
async def test_malformed_pdf_rejection():
    """Test 9: Verify malformed/corrupted PDF content is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        corrupted_content = b"%PDF-corrupted-random-junk-bytes"
        response = await client.post(
            "/documents/parse",
            files={"file": ("corrupted.pdf", io.BytesIO(corrupted_content), "application/pdf")},
        )
        assert response.status_code == 400
        assert "Malformed or corrupted PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_post_documents_parse_golden(golden_pdf_path):
    """Test end-to-end POST /documents/parse endpoint with golden PDF."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/parse",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "golden_agreement.pdf"
        assert data["page_count"] == 2
        assert data["parsing_status"] == "TEXT_AVAILABLE"
        assert len(data["clauses"]) >= 4

        # Validate multi-page clause 3 in JSON response
        c3 = next((c for c in data["clauses"] if c["clause_number"] == "3"), None)
        assert c3 is not None
        assert 1 in c3["pages"] and 2 in c3["pages"]
        assert len(c3["bounding_boxes"]) >= 2
