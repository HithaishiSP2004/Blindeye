import io
import os
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.extraction.structured_extractor import _mock_extract_candidates
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_pdf_bytes():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        return f.read()


@pytest.mark.asyncio
async def test_api_advocate_pack_endpoint(golden_pdf_bytes):
    """Test generating Advocate Pack from golden agreement PDF."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("backend.main.extract_candidate_facts", side_effect=lambda tree: _mock_extract_candidates(tree)):
            response = await client.post(
                "/documents/advocate-pack",
                files={"file": ("golden_agreement.pdf", io.BytesIO(golden_pdf_bytes), "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()

        # Structural assertions
        assert data["document_name"] == "golden_agreement.pdf"
        assert data["total_pages"] >= 1
        assert "executive_summary" in data
        assert "financial_covenants" in data
        assert "textual_divergence_schedule" in data
        assert "coverage_gaps" in data
        assert "footnotes" in data
        assert "legal_disclaimer" in data

        # Product language assertion (Amendment 3)
        assert "Evidentiary Agreement Review Dossier" in data["legal_disclaimer"]

        # Executive summary provenance assertions (Amendment 4)
        exec_sum = data["executive_summary"]
        assert exec_sum["parties_licensor"]["classification"] in ["EXPLICIT_IN_DOCUMENT", "NO_SUPPORTING_PASSAGE"]
        assert exec_sum["monthly_rent"]["classification"] in ["EXPLICIT_IN_DOCUMENT", "NO_SUPPORTING_PASSAGE"]

        # Coverage gaps assertions (Amendment 2)
        for gap in data["coverage_gaps"]:
            assert gap["status_display"] == "UNADDRESSED"
            assert gap["coverage_note"] == "No supporting provision found for this field."
            assert "deficient" not in gap["coverage_note"].lower()


@pytest.mark.asyncio
async def test_api_advocate_pack_rejects_non_pdf():
    """Verify non-PDF uploads are rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/documents/advocate-pack",
            files={"file": ("notes.txt", io.BytesIO(b"Plain text agreement"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
