import io
import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.models.verification import ClaimTag
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_pdf_path():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    return path


@pytest.mark.asyncio
async def test_api_post_documents_extract(golden_pdf_path):
    """End-to-end test of POST /documents/extract endpoint returning StructuredAgreementResult."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/extract",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()

        # 1. Verify DocumentTree is returned
        assert "document_tree" in data
        assert data["document_tree"]["filename"] == "golden_agreement.pdf"
        assert len(data["document_tree"]["clauses"]) >= 4

        # 2. Verify StructuredAgreement is returned
        assert "structured_agreement" in data
        sa = data["structured_agreement"]
        assert "summary" in sa
        summary = sa["summary"]
        assert summary["fields_total"] == 16
        assert summary["fields_found"] >= 9
        assert summary["fields_provenance_resolved"] == summary["fields_found"]

        # 3. Verify monthly rent has physical provenance
        rent = sa["monthly_rent"]
        assert rent["status"] == "FOUND"
        assert rent["claim_tag"] == ClaimTag.EXPLICIT.value
        assert rent["page"] == 1
        assert rent["bbox"] is not None
        assert "Rs. 35,000" in rent["exact_quote"]

        # 4. Verify negative fields
        lock_in = sa["lock_in_months"]
        assert lock_in["status"] == "NOT_FOUND"
        assert lock_in["claim_tag"] == ClaimTag.NOT_FOUND.value
        assert lock_in["bbox"] is None
