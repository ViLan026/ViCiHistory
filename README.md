
# ViCiHistory – Vietnamese Historical Evidence Retrieval

ViCiHistory is an AI-powered backend service designed to retrieve historical evidence from Vietnamese historical documents.

The system analyzes user-submitted historical text, extracts independent factual claims, and searches a collection of digitized historical sources to identify relevant evidence.

By combining **Dense Semantic Search** with **Sparse Keyword Search (BM25)**, ViCiHistory aims to improve evidence retrieval across historical documents with different writing styles and vocabulary.

The service also generates PDF excerpts and highlights matching passages, allowing users to inspect the original historical sources.

## Features

- **Historical Claim Extraction:** Uses Google Gemini to extract meaningful historical claims from Vietnamese text.
- **Claim Normalization:** Converts extracted statements into standalone claims while preserving their original source text.
- **Hybrid Retrieval:** Combines semantic vector search and BM25 keyword search to retrieve relevant historical passages.
- **Vietnamese Text Processing:** Uses Underthesea for Vietnamese word segmentation in the BM25 pipeline.


### Hybrid Score Calculation

The system normalizes the scores from both retrieval methods and combines them using a configurable weighted formula:

```text
Hybrid Score = α × Dense Score + (1 - α) × BM25 Score
```

Where:

- `α` controls the contribution of dense retrieval.
- `1 - α` controls the contribution of BM25 retrieval.

The system then sorts the merged candidates and returns the highest-ranked evidence passages.

## Historical Source Collection

The application currently defines mappings for the following historical documents:

- Đại Việt Sử Ký Toàn Thư
- Khâm Định Việt Sử Thông Giám Cương Mục
- Việt Sử Toàn Thư
- Lịch Sử Việt Nam – 15 quyển.

### Run the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Original Source Verification

Retrieved passages should be treated as research references rather than automatic proof of historical correctness.

Users should inspect the original historical document, surrounding context, page references, and footnotes before drawing conclusions.

An empty evidence result does not necessarily mean that a historical claim is false.

## License

No license has currently been specified for this repository.

Please contact the repository owner for permission to use, modify, or distribute the project.
