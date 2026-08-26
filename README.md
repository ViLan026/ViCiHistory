# History Verifier AI

A small FastAPI service for the AI Riser project.

Pipeline:

`input text -> claim extraction (Gemini) -> embedding -> Qdrant retrieval -> claim verification (Gemini)`

## API

### Health

```http
GET /health
```

### Verify historical text

```http
POST /api/v1/verify
Content-Type: application/json
```

```json
{
  "content": "Năm 1285 quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng."
}
```

Example response shape:

```json
{
  "claims": [
    {
      "id": "claim_1",
      "source_text": "Năm 1285 quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng.",
      "claim": "Quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng vào năm 1285.",
      "label": "REFUTED",
      "explanation": "...",
      "evidence": [
        {
          "chunk_id": "...",
          "score": 0.82,
          "book_name": "Đại Việt Sử Ký Toàn Thư",
          "pages": [198],
          "text": "...",
          "footnotes": null
        }
      ]
    }
  ]
}
```

`source_text` is kept separately from the normalized `claim` so a frontend can highlight the exact source sentence while retrieval uses a standalone claim.

## Local development

1. Copy `.env.example` to `.env` and fill in your own secrets.
2. Create a virtual environment.
3. Install CPU PyTorch and the requirements.
4. Start Uvicorn:

```bash
python -m uvicorn app.main:app --reload --port 8080
```

Open Swagger at `http://localhost:8080/docs`.

## Important compatibility rule

`EMBEDDING_MODEL` must be the same model used when the Qdrant collection was created. The default is:

```text
AITeamVN/Vietnamese_Embedding
```

The Qdrant payload reader expects the existing collection fields used by the old project:

- `raw_text` (preferred) or `overlap_text`
- `chunk_id`
- `book_name`
- `pages`
- `footnotes`

## Docker

```bash
docker build -t history-verifier-ai .
docker run --env-file .env -p 8080:8080 history-verifier-ai
```

The Docker image pre-downloads the embedding model at build time. This makes the image larger but avoids downloading the Hugging Face model during each Cloud Run cold start.

## Secrets

Never commit `.env` or real API keys. On Cloud Run, provide `GEMINI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY` through environment variables / Secret Manager.
