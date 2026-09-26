import io
import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_pdf_bytes():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    with open(path, "rb") as f:
        return f.read()


@pytest.mark.asyncio
async def test_api_contradictions_endpoint(golden_pdf_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/documents/contradictions",
            files={"file": ("golden_agreement.pdf", io.BytesIO(golden_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "total_conflicts" in data
        assert "evaluation_summary" in data
        assert isinstance(data["total_conflicts"], int)
        assert isinstance(data["findings"], list)


@pytest.mark.asyncio
async def test_api_contradictions_rejects_non_pdf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/documents/contradictions",
            files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
