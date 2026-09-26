import io
import json
import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from tests.generate_fixtures import create_golden_agreement_pdf


@pytest.fixture(scope="session")
def golden_pdf_path():
    path = "tests/fixtures/golden_agreement.pdf"
    if not os.path.exists(path):
        create_golden_agreement_pdf(path)
    return path


@pytest.mark.asyncio
async def test_endpoint_post_documents_ask_rent(golden_pdf_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/ask",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"question": "What is the monthly rent?"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["question"] == "What is the monthly rent?"
        assert data["status"] == "ANSWERED"
        assert data["question_type"] == "FACT_LOOKUP"
        assert "35,000" in data["answer"]
        assert len(data["evidence"]) >= 1
        assert data["evidence"][0]["page"] == 1
        assert data["evidence"][0]["bbox"] is not None
        assert "retrieval" in data
        assert data["retrieval"]["method"] in ("FIELD_LOOKUP", "BM25")


@pytest.mark.asyncio
async def test_endpoint_post_documents_ask_address_not_found(golden_pdf_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/ask",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"question": "What is the property address?"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "NOT_FOUND"
        assert len(data["evidence"]) == 0
        assert "does not provide a property address" in data["answer"]


@pytest.mark.asyncio
async def test_endpoint_post_documents_ask_legal_advice_refused(golden_pdf_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = await client.post(
            "/documents/ask",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"question": "Can I sue the landlord for early eviction?"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "REFUSED"
        assert data["question_type"] == "LEGAL_ADVICE"
        assert len(data["evidence"]) == 0
        assert data["refusal_reason"] is not None


@pytest.mark.asyncio
async def test_endpoint_post_documents_ask_with_history(golden_pdf_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(golden_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        history_json = json.dumps([
            {"role": "user", "text": "What is the rent?"},
            {"role": "assistant", "text": "The monthly rent is Rs. 35,000/- per month."},
        ])

        response = await client.post(
            "/documents/ask",
            files={"file": ("golden_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "question": "When is it due?",
                "conversation_history": history_json,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "answer" in data
