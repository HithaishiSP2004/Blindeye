import io
import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.models.verification import ClaimTag, VerificationStatus
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_pdf_path():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    return path


@pytest.mark.asyncio
async def test_api_post_documents_verify(golden_pdf_path):
    """End-to-end test of POST /documents/verify endpoint returning DocumentVerificationResult."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/verify",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()

        # 1. Verification Result top-level contract check (Correction 5: DocumentTree not returned)
        assert "document_tree" not in data
        assert "summary" in data
        assert "claims" in data
        assert "refusal_reason" in data
        assert data["refusal_reason"] is None

        # 2. Check summary metrics (Correction 10: factual counters)
        summary = data["summary"]
        assert summary["total"] == 16
        assert summary["verified"] >= 9
        assert summary["not_found"] >= 5
        assert summary["contradictory"] == 0

        # 3. Check individual verified claims
        claims_list = data["claims"]
        claims_by_field = {c["field_name"]: c for c in claims_list}

        rent_claim = claims_by_field["monthly_rent"]
        assert rent_claim["status"] == VerificationStatus.VERIFIED.value
        assert rent_claim["claim_tag"] == ClaimTag.EXPLICIT.value
        assert rent_claim["source"] is not None
        assert rent_claim["source"]["bbox"] is not None
        assert rent_claim["verification"]["deterministic_result"] is not None

        # 4. Check negative claim
        lock_in_claim = claims_by_field["lock_in_months"]
        assert lock_in_claim["status"] == VerificationStatus.NOT_FOUND.value
        assert lock_in_claim["claim_tag"] == ClaimTag.NOT_FOUND.value
        assert lock_in_claim["source"] is None
