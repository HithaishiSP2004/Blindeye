import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify backend health endpoint returns 200 and valid metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert any(p in data["phase"] for p in ["Showcase", "Advocate", "Contradiction", "Q&A", "Evidence-First", "Verification", "Extraction", "Document Engine", "Foundation"])
        assert "gemini_fallback_models" in data
        assert "gemini-3.7-flash" in data["gemini_fallback_models"]
        assert "gemini-3.6-flash" in data["gemini_fallback_models"]

        assert "limits" in data
        assert data["limits"]["max_file_size_mb"] == 15


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify API root endpoint responds with basic service info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "version" in data
