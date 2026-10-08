# /converter — Markdown Conversion API

FastAPI service that turns any web page into AI-ready Markdown with SSRF protection, size limits, and token truncation.

## Setup & Running

### 1. Create Virtual Environment and Install Dependencies
```bash
cd converter
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run Development Server
```bash
uvicorn main:app --reload --port 8000
```

### 4. Run Tests
```bash
pytest test_main.py -v
```

## API Endpoints

### `GET /health`
Returns `{"ok": true}`.

### `POST /v1/convert`
Header: `X-API-Key: <your_api_key>`
Body:
```json
{
  "url": "https://example.com/blog/sample-post",
  "max_tokens": 1500
}
```

Response:
```json
{
  "url": "https://example.com/blog/sample-post",
  "title": "Sample Post Title",
  "markdown": "# Sample Post Title\n\nPost content in markdown...",
  "token_count": 420,
  "fetched_at": "2026-10-08T12:00:00.000Z"
}
```
