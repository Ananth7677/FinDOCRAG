# FinDocRAG

FinDocRAG is a work-in-progress retrieval-augmented generation (RAG) API for financial reports. It extracts PDF text, removes detected headers and footers, creates overlapping chunks, and stores Gemini embeddings in PostgreSQL with pgvector.

FastAPI exposes each processing stage and a question-answering endpoint that retrieves relevant chunks and generates Gemini answers with citations. See the current limitations before rerunning embeddings or processing changed reports.

## Project structure

```text
FinDocRAG/
├── AnnualReports/
│   └── Mastercard/Report.pdf     # Included input report
├── Extract/
│   ├── extract.py               # PDF extraction and text cleaning
│   └── text_analysis.py         # Header/footer detection
├── Chunking/
│   └── chunk.py                 # Paragraph-aware character chunking
├── Embedding/
│   └── embedding.py             # Document/query embeddings and database persistence
├── Parser/
│   └── structure_parser.py      # Placeholder
├── DBO/
│   ├── __init__.py              # Database package exports
│   ├── database.py             # SQLAlchemy sessions + pgvector connection test
│   ├── Models/embedding.py     # Embeddings ORM model
│   └── Services/embedding_db_services.py # Inserts and similarity retrieval
├── DTO/
│   └── embedding_dto.py        # Embedding validation and insert mapping
├── Integration/
│   └── llm_integration.py      # Gemini answers and citation schema
├── Validations/
│   └── validations.py          # Input guardrails and citation validation
├── Controllers/
│   └── pipeline_controller.py   # HTTP routes and request validation
├── results/                      # Generated output files
│   ├── extract/                 # Extraction outputs
│   │   ├── extracted_data.jsonl # Raw page text and positioned blocks
│   │   └── metadata.json        # Source hash and extraction metadata
│   ├── analysis/                # Analysis outputs
│   │   └── chrome_patterns.json # Detected header/footer patterns
│   ├── clean/                   # Cleaning outputs
│   │   └── pages.jsonl          # Cleaned page records
│   ├── chunking/                # Chunking outputs
│   │   └── chunk.jsonl          # Chunk records
│   └── embedding/               # Embedding outputs
│       └── embeddings.jsonl     # Legacy output; not written by /api/embed
├── main.py                      # FastAPI application
├── config.py                    # Environment configuration
├── requirements.txt             # Runtime dependencies
└── README.md
```

Extraction, analysis, cleaning, and chunking write files under `results/`, organized by stage. The active embedding pipeline writes to the PostgreSQL `embeddings` table.

## Database / pgvector

The `DBO` package provides PostgreSQL persistence and retrieval:

- `DBO/database.py` builds SQLAlchemy sessions using `DATABASE_URL` or individual `DB_*` environment variables
- `DBO/database.py` also registers the `pgvector` adapter when available
- `DBO/Models/embedding.py` maps 768-dimensional vectors, source chunk IDs, text, and document/page references
- `DBO/Services/embedding_db_services.py` inserts validated records and retrieves chunks by cosine similarity
- Running `python DBO/database.py` performs a connection test with `SELECT version()` using exported environment variables or local defaults; that script does not load `.env` itself

Default local connection settings are defined in [`.env.example`](.env.example):

- `DB_HOST=localhost`
- `DB_PORT=55432`
- `DB_NAME=findb`
- `DB_USER=finusr`
- `DB_PASSWORD=finpass`

If you change the Docker port mapping or database credentials, update the configuration to match. `DATABASE_URL` takes precedence over individual `DB_*` variables. The database module reads configuration at import time, so export custom database settings before starting the application.

## Setup

Use Python 3.11 or newer. From the project root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. Dependencies have version ranges in `requirements.txt`; there is no lockfile.

Copy the environment template if you do not already have a `.env` file:

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env` before starting the API. The embedding and
answer-generation modules create Gemini clients at import time. The configured
models are `gemini-embedding-2` and `gemini-2.5-flash`; your account must have
access to them.

Start PostgreSQL and verify the schema:

```bash
docker compose up -d db
docker compose exec db pg_isready -U finusr -d findb
docker compose exec db psql -U finusr -d findb -c '\d+ embeddings'
```

Wait for PostgreSQL to accept connections before checking the schema. On a new
Docker data volume, `docker/initdb/init.sql` creates the `vector` extension and
`embeddings` table. Existing volumes do not rerun initialization scripts; compare
their schema with the SQL file when upgrading. See [Docker setup](README_DOCKER_PG.md)
for more details.

## FastAPI controllers

Start the server from the project root after activating the virtual environment:

```bash
python -m uvicorn main:app --reload
```

You can also run `main.py` from your IDE. Open [Swagger UI](http://127.0.0.1:8000/docs)
to try the endpoints. Each POST waits for its work to complete. Processing stages
return a stage/status/output-path object; `/api/userquery` returns an answer and
citations. `/health` checks API availability only, not database or Gemini access.

| Method | Endpoint | Action / prerequisite |
| --- | --- | --- |
| GET | `/health` | Check server health |
| POST | `/api/extract` | Extract the specified local PDF |
| POST | `/api/analyze` | Detect headers/footers after extraction |
| POST | `/api/clean` | Clean text after extraction and analysis |
| POST | `/api/chunk` | Chunk cleaned pages |
| POST | `/api/embed` | Embed chunks using Gemini and persist them in PostgreSQL |
| POST | `/api/retrieve` | Retrieve stored chunks without generating an answer |
| POST | `/api/userquery` | Validate the question, retrieve chunks, and generate an answer with checked citation IDs |

For extraction, send a JSON body:

```bash
curl -X POST http://127.0.0.1:8000/api/extract \
  -H 'Content-Type: application/json' \
  -d '{"pdf":"AnnualReports/Mastercard/Report.pdf","start_page":1,"end_page":132,"page_offset":-1}'
```

Sending `{}` to `/api/extract` uses the included report's default range.
PDF paths refer to files on the server; relative API paths resolve from the project
root. There is no file-upload endpoint.

`/api/analyze` accepts an optional body such as
`{"top_fraction":0.05,"bottom_fraction":0.05}`. `/api/clean`, `/api/chunk`, and
`/api/embed` need no request body:

```bash
curl -X POST http://127.0.0.1:8000/api/chunk
```

Embedding uses batches of up to 50 chunks and 768-dimensional vectors. Document
embedding requests retry Gemini HTTP 429 errors after 60 seconds, without a retry
limit. Each embedding is committed separately to PostgreSQL.

The `/api/embed` response still lists `results/embedding/embeddings.jsonl` in
`outputs`, but the active implementation does not write that file. Inspect the
PostgreSQL table to verify persisted embeddings.

## Ask a question

After processing and embedding a report, send a question:

```bash
curl -X POST http://127.0.0.1:8000/api/userquery \
  -H 'Content-Type: application/json' \
  -d '{"question":"What risks does the report identify?"}'
```

Both `/api/userquery` and `/api/retrieve` require a `question` string of 5–200
characters after trimming leading and trailing whitespace. Invalid requests return
`422`.

Before retrieval, `/api/userquery` checks regex patterns for instruction overrides,
prompt extraction, and role overrides, then uses `gemini-2.5-flash` to classify
the question as `ALLOW` or `BLOCK`. Blocked questions return `400` with a reason.
Ordinary questions unrelated to the report are allowed by the classifier.

The endpoint embeds the question, retrieves up to 10 chunks with cosine similarity
strictly greater than `0.65`, and passes them to `gemini-2.5-flash`. Retrieval
defaults are defined in `DBO/Services/embedding_db_services.py`. Retrieval searches
all stored documents; the request has no document filter.

The response contains `llm_response` (answer text) and `citations` (objects with
`id`, `page_number`, and `similarity`). Citation IDs refer to database embedding
rows, not source chunk IDs. The model is instructed to answer only from retrieved
context and return supporting chunk IDs. The server checks each citation ID
against the retrieved chunks and fills `page_number` and `similarity` from their
stored metadata. An unknown citation ID triggers one answer-generation retry;
an unknown ID in the retried answer returns `502`. Answers without citations
return `502` immediately unless their text matches the accepted no-answer fallback.
These checks validate citation membership and metadata, not whether the cited
text supports every claim in the answer.

When retrieval returns no qualifying chunks, `llm_call()` produces the following
fallback. The current validation mismatch described below causes the endpoint to
return `502` instead of passing this response through:

```json
{
  "llm_response": "No relevant answer was found.",
  "citations": []
}
```

## Retrieve chunks

To inspect retrieval results without generating an answer:

```bash
curl -X POST http://127.0.0.1:8000/api/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"question":"What risks does the report identify?"}'
```

This endpoint returns up to 10 chunks with cosine similarity strictly greater than
`0.5`, ordered from highest similarity to lowest. Each result contains `id`,
`text`, `page_number`, `section_text` (which may be `null`), and `similarity`.
No matches returns an empty list. Retrieval searches all stored documents.

`/api/retrieve` applies the shared question length validation, but does not run the
regex guardrail, prompt classifier, or answer validation used by `/api/userquery`.

## Operation and errors

Errors return a JSON `detail`: `400` for blocked questions, `404` for a missing
PDF, `409` for missing stage inputs, `422` for invalid inputs, `502` for answer
validation failures, and `503` for a missing Gemini key detected by `/api/embed`.
Other unhandled failures return `500`. `/api/userquery` forwards Gemini API errors using the provider's
status code and message.

The endpoints write to shared output files. Run one operation at a time, in stage
order. There is no orchestration or locking layer. When changing reports, rerun
all downstream stages; existing downstream files are not automatically invalidated.
The server has no authentication and binds to localhost in the commands above.

The controller structure follows FastAPI's
[APIRouter documentation](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
Embedding calls use the
[Google Gen AI SDK](https://googleapis.github.io/python-genai/#embed-content).
Database sessions use SQLAlchemy with PostgreSQL and `pgvector` support.

## Pipeline order

Call the individual endpoints in Swagger UI in this order:
extraction → header/footer analysis → cleaning → chunking → embedding → user query.
After embedding, ask additional questions without repeating preparation.

The printed page range is inclusive. PDF page indexing follows:

```text
zero-based PDF page index = printed page number + page_offset
```

Use `-1` when printed page 1 is the first PDF page, or `4` when printed page 1
is the sixth PDF page. Header/footer analysis uses the top and bottom 5% of each
page by default. Review `results/analysis/chrome_patterns.json` before cleaning a new
report if you need to check which text will be removed.

## Chunking behavior

Configure these constants in `Chunking/chunk.py`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `CHUNK_SIZE` | `700` | Maximum chunk length in characters |
| `OVERLAP_SIZE` | `100` | Character overlap for long-paragraph splits and eligible paragraph transitions |
| `MIN_CHUNK_SIZE` | `300` | A completed chunk must exceed this length to carry overlap into the next paragraph |

The chunker packs paragraphs where possible and splits oversized paragraphs using a sliding window. Overlap between packed chunks is included only when it fits alongside the next paragraph. Overlap from a preceding packed chunk is not carried into an oversized paragraph's hard split. `MIN_CHUNK_SIZE` does not enforce a minimum output length, and these settings count characters, not tokens.

Each output line is a JSON object with the following fields:

| Field | Description |
| --- | --- |
| `doc_id` | Source PDF filename |
| `pg_number` | Printed page number |
| `chunk_id` | Sequential ID starting at 1 for each run |
| `char_count` | Length of the chunk text |
| `txt` | Chunk text |
| `section_text` | Heading inferred from the page's top region, or `null` |

## Current limitations

- Extraction uses embedded PDF text; there is no OCR step for scanned pages.
- Header/footer and section detection depend on page layout. Cleaning removes matching patterns throughout text blocks, so inspect results for each new report.
- Tables are handled as PDF text blocks, without dedicated table reconstruction.
- The extraction endpoint accepts an input PDF and page range, but stage output locations are fixed; processing another report replaces the previous stage outputs unless they are saved separately.
- Document IDs use filenames, so identically named PDFs are not distinguished in chunk records.
- Embedding resume logic reads `chunk_metadata["chunk_id"]` from an ORM record, but the model stores a `chunk_id` column and has no `chunk_metadata` attribute. Repeating embedding for a document with stored rows currently fails; changed page ranges and chunk contents are not safely reconciled.
- Retrieval spans all stored documents, and retrieval and citation responses do not include document IDs. Citation validation checks IDs and populates metadata; it does not verify factual support for the answer.
- The no-answer fallback is currently inconsistent: `llm_call()` and its prompt include a trailing period, but output validation accepts only `"no relevant answer was found"` without a period (ignoring case). Consequently, the empty-context fallback returns `502`.
- Missing citations fail immediately; only unknown citation IDs trigger an answer-generation retry.
- The interface is an HTTP API with Swagger UI; there is no dedicated chat frontend.
