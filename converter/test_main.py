import socket
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import httpx
from main import app, API_KEY

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": API_KEY}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unauthorized_request():
    response = client.post(
        "/v1/convert",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_invalid_scheme():
    response = client.post(
        "/v1/convert",
        json={"url": "ftp://example.com/file.txt"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 400


def test_private_ip_blocked():
    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://localhost:8000",
        "http://192.168.1.1/router",
        "http://10.0.0.5/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/status",
    ]
    for url in blocked_urls:
        response = client.post(
            "/v1/convert",
            json={"url": url},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422
        assert "Blocked target" in response.json()["detail"] or "Invalid URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_redirect_to_private_ip_blocked():
    # Simulate first response redirecting to 127.0.0.1
    mock_redirect_response = httpx.Response(
        status_code=302,
        headers={"Location": "http://127.0.0.1:8000/internal"},
        request=httpx.Request("GET", "https://public-site.com/redirect"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # First call is public site, second hop would attempt to hit 127.0.0.1
        mock_get.return_value = mock_redirect_response
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]):
            response = client.post(
                "/v1/convert",
                json={"url": "https://public-site.com/redirect"},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 422
            assert "Blocked target" in response.json()["detail"]


@pytest.mark.asyncio
async def test_non_html_rejected():
    mock_response = httpx.Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"key": "value"}',
        request=httpx.Request("GET", "https://public-site.com/data.json"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            response = client.post(
                "/v1/convert",
                json={"url": "https://public-site.com/data.json"},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 422
            assert "Only HTML content is supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_oversized_response_rejected():
    large_content = b"A" * (2 * 1024 * 1024 + 100)  # > 2MB
    mock_response = httpx.Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        content=large_content,
        request=httpx.Request("GET", "https://public-site.com/big.html"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            response = client.post(
                "/v1/convert",
                json={"url": "https://public-site.com/big.html"},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 422
            assert "exceeds limit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_valid_html_conversion_and_truncation():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article Title</title></head>
    <body>
        <main>
            <h1>Main Article Heading</h1>
            <p>This is the first paragraph describing the micro-SaaS architecture and API design.</p>
            <p>This is the second paragraph with more extensive details about Markdown conversion.</p>
        </main>
    </body>
    </html>
    """
    mock_response = httpx.Response(
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        text=sample_html,
        request=httpx.Request("GET", "https://example.com/blog/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            response = client.post(
                "/v1/convert",
                json={"url": "https://example.com/blog/test", "max_tokens": 15},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["url"] == "https://example.com/blog/test"
            assert "markdown" in data
            assert data["token_count"] <= 15
            assert "fetched_at" in data
