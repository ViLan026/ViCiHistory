
A FastAPI service for the AI Riser project.

Pipeline:

`input text -> claim extraction (Gemini) -> embedding -> Qdrant retrieval -> Extract pages and highlight evidence`

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


