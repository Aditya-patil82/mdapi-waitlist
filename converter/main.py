import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tiktoken
import trafilatura
from dotenv import load_dotenv

from ssrf import (
    safe_fetch_html,
    SSRFValidationError,
    OversizedResponseError,
    InvalidContentTypeError,
    MaxRedirectsExceededError,
)
import httpx

load_dotenv()

API_KEY = os.getenv("API_KEY", "dev-secret-key")

app = FastAPI(
    title="Markdown Converter API",
    description="Convert any web page into AI-ready clean Markdown",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tiktoken encoder
encoder = tiktoken.get_encoding("cl100k_base")


class ConvertRequest(BaseModel):
    url: str
    max_tokens: Optional[int] = None


class ConvertResponse(BaseModel):
    url: str
    title: Optional[str]
    markdown: str
    token_count: int
    fetched_at: str


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Validate incoming X-API-Key header against configured API_KEY."""
    if not API_KEY:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )


def truncate_at_paragraph_boundary(text: str, max_tokens: int) -> tuple[str, int]:
    """
    Truncates markdown at paragraph boundaries to stay within max_tokens.
    Falls back to token truncation if the first paragraph exceeds max_tokens.
    """
    tokens = encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text, len(tokens)

    paragraphs = text.split("\n\n")
    current_paragraphs: list[str] = []

    for p in paragraphs:
        candidate = "\n\n".join(current_paragraphs + [p]) if current_paragraphs else p
        cand_tokens = len(encoder.encode(candidate))
        if cand_tokens <= max_tokens:
            current_paragraphs.append(p)
        else:
            break

    if current_paragraphs:
        truncated_text = "\n\n".join(current_paragraphs)
        return truncated_text, len(encoder.encode(truncated_text))

    # Single paragraph was larger than max_tokens: decode slice of tokens
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoder.decode(truncated_tokens)
    return truncated_text, len(truncated_tokens)


@app.get("/health")
def health_check():
    return {"ok": True}


@app.post("/v1/convert", response_model=ConvertResponse)
async def convert_url(
    req: ConvertRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    verify_api_key(x_api_key)

    url_str = req.url.strip()
    if not url_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL cannot be empty.",
        )

    # 1. Fetch HTML safely with SSRF protection
    try:
        final_url, html_content = await safe_fetch_html(url_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {e}",
        )
    except (SSRFValidationError, InvalidContentTypeError, OversizedResponseError, MaxRedirectsExceededError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Blocked target: {e}",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to target URL timed out.",
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch target URL: {e}",
        )

    # 2. Extract content & metadata using trafilatura
    markdown_text = trafilatura.extract(
        html_content,
        url=final_url,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        include_comments=False,
    )

    if not markdown_text or not markdown_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text content found on the page.",
        )

    meta = trafilatura.extract_metadata(html_content, default_url=final_url)
    title = meta.title if meta else None

    # 3. Handle token limit & truncation
    token_count = len(encoder.encode(markdown_text))
    if req.max_tokens and req.max_tokens > 0 and token_count > req.max_tokens:
        markdown_text, token_count = truncate_at_paragraph_boundary(markdown_text, req.max_tokens)

    fetched_at = datetime.now(timezone.utc).isoformat()

    return ConvertResponse(
        url=final_url,
        title=title,
        markdown=markdown_text,
        token_count=token_count,
        fetched_at=fetched_at,
    )
