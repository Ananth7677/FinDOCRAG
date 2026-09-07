# FinDocRAG

FinDocRAG is a work-in-progress document preparation pipeline for retrieval-augmented generation (RAG) over financial reports. It extracts text from PDFs, removes detected headers and footers, and creates overlapping text chunks with document and page references.

The current implementation covers extraction, cleaning, chunking, and Gemini embedding generation, with FastAPI controllers for each stage. Vector search and question answering are not implemented yet.

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
│   └── embedding.py             # Batched Gemini embeddings
├── Parser/
│   └── structure_parser.py      # Placeholder
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
│       └── embeddings.jsonl     # Gemini embeddings
├── main.py                      # FastAPI application
├── config.py                    # Environment configuration
├── requirements.txt             # Runtime dependencies
└── README.md
```

All pipeline output files are written to the `results/` directory organized by stage.

## Setup

Use Python 3.11 or newer. From the project root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. Dependencies have version ranges in `requirements.txt`; there is no lockfile.

## FastAPI controllers

Start the server from the project root after activating the virtual environment:

```bash
python -m uvicorn main:app --reload
```

You can also run `main.py` from your IDE. Open [Swagger UI](http://127.0.0.1:8000/docs)
to try the endpoints. Each POST waits for its work to complete and returns output
file paths relative to the project root.

| Method | Endpoint | Action / prerequisite |
| --- | --- | --- |
| GET | `/health` | Check server health |
| POST | `/api/extract` | Extract the specified local PDF |
| POST | `/api/analyze` | Detect headers/footers after extraction |
| POST | `/api/clean` | Clean text after extraction and analysis |
| POST | `/api/chunk` | Chunk cleaned pages |
| POST | `/api/embed` | Embed chunks using Gemini |

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

For embedding, set `GEMINI_API_KEY` in the root `.env` file (see `.env.example`).
The API starts and local stages work without a key. `/api/embed` sends chunk text
to Gemini using the existing `gemini-embedding-2` model; your account must have
access to it. The existing embedding implementation appends to `embeddings.jsonl`,
so repeated calls can add duplicate records.

Errors return a JSON `detail`: `404` for a missing PDF, `409` for missing stage
inputs, `422` for invalid inputs, and `503` for a missing Gemini key. Other failures
return `500`.

The endpoints write to shared output files. Run one operation at a time, in stage
order. There is no orchestration or locking layer. When changing reports, rerun
all downstream stages; existing downstream files are not automatically invalidated.
The server has no authentication and binds to localhost in the commands above.

The controller structure follows FastAPI's
[APIRouter documentation](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
Embedding calls use the
[Google Gen AI SDK](https://googleapis.github.io/python-genai/#embed-content).

## Pipeline order

Call the individual endpoints in Swagger UI in this order:
extraction → header/footer analysis → cleaning → chunking → embedding.

The printed page range is inclusive. PDF page indexing follows:

```text
zero-based PDF page index = printed page number + page_offset
```

Use `-1` when printed page 1 is the first PDF page, or `4` when printed page 1
is the sixth PDF page. Header/footer analysis uses the top and bottom 5% of each
page by default. Review `Extract/chrome_patterns.json` before cleaning a new
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
- There is no end-to-end RAG question-answering interface yet.
