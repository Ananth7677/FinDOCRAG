# FinDocRAG

FinDocRAG is a work-in-progress document preparation pipeline for retrieval-augmented generation (RAG) over financial reports. It extracts text from PDFs, removes detected headers and footers, and creates overlapping text chunks with document and page references.

The current implementation covers extraction, cleaning, and chunking. Embedding generation, vector search, and question answering are not implemented yet.

## Project structure

```text
FinDocRAG/
├── AnnualReports/
│   └── Mastercard/Report.pdf     # Included input report
├── Extract/
│   ├── extract.py               # PDF extraction and text cleaning
│   ├── text_analysis.py         # Header/footer detection
│   ├── extracted_data.jsonl     # Raw page text and positioned blocks
│   ├── metadata.json            # Source hash and extraction metadata
│   ├── chrome_patterns.json     # Detected header/footer patterns
│   └── pages.jsonl              # Cleaned page records
├── Chunking/
│   ├── chunk.py                 # Paragraph-aware character chunking
│   └── chunk.jsonl              # Chunk output
├── Embedding/
│   └── embedding.py             # Empty placeholder
├── Parser/
│   └── structure_parser.py      # Placeholder
├── main.py                      # Runs all implemented stages in order
└── README.md
```

An additional `chunk.jsonl` exists at the project root. The commands below generate `Chunking/chunk.jsonl`.

## Setup

Use Python 3 and install PyMuPDF, the only third-party dependency currently imported by the pipeline. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pymupdf
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. There is no dependency lockfile; the existing extraction metadata records PyMuPDF `1.28.2`.

## Run the pipeline

From the project root, run all four stages with one command:

```bash
python main.py
```

The default processes printed pages 1–132 of the included Mastercard report.
You can also run `main.py` using your IDE's Run action; it locates the stage
directories relative to its own file.

For a different report or page range:

```bash
python main.py --pdf "path/to/report.pdf" --start-page 1 --end-page 50 --page-offset -1
```

The runner executes extraction → header/footer detection → cleaning → chunking,
stops if a stage raises an error, and writes the final output to
`Chunking/chunk.jsonl`. It replaces existing stage outputs. Embedding and parsing
are placeholders and are not run. Use the individual steps below if you want to
review detected patterns before cleaning.

### Run stages individually

The scripts resolve paths relative to the current working directory. Run the following steps in order, starting at the project root. Rerunning stages replaces their generated output files.

### 1. Extract PDF pages

```bash
cd Extract
python -c "from extract import extract_data; extract_data(1, 132, page_offset=-1, file_path='../AnnualReports/Mastercard/Report.pdf')"
```

This extracts the included report's printed pages 1 through 132, inclusive, and writes `extracted_data.jsonl` and `metadata.json`.

To use another PDF, change the file path, page range, and offset. The mapping is:

```text
zero-based PDF page index = printed page number + page_offset
```

For example, use `-1` when printed page 1 is the first PDF page, or `4` when printed page 1 is the sixth PDF page.

Each extracted page includes raw text, block coordinates, dimensions, a printed page number, and a possible section heading taken from the top of the page. Metadata includes the PDF's SHA-256 hash and extraction timestamp.

### 2. Detect headers and footers

While still in `Extract/`:

```bash
python text_analysis.py
```

This reads `extracted_data.jsonl` and writes `chrome_patterns.json`. By default, it detects blocks entirely within the top or bottom 5% of each page and replaces digits with `<N>` in the recorded patterns.

Review the patterns before cleaning a new report: content near page edges may be detected as a header or footer.

### 3. Clean extracted text

```bash
python extract.py
```

The script's current entry point runs **cleaning only**; extraction must be invoked separately as shown in step 1. Cleaning reads `extracted_data.jsonl` and `chrome_patterns.json`, then writes `pages.jsonl`. It normalizes Unicode and whitespace, removes matching header/footer text, and separates retained text blocks with blank lines.

### 4. Create chunks

```bash
cd ../Chunking
python chunk.py
cd ..
```

This reads `Extract/pages.jsonl` and writes `Chunking/chunk.jsonl`. Pages are chunked independently, so chunks do not span page boundaries.

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
- The runner accepts an input PDF and page range, but stage output locations are fixed; processing another report replaces the previous stage outputs unless they are saved separately.
- Document IDs use filenames, so identically named PDFs are not distinguished in chunk records.
- There is no automated test suite or end-to-end RAG interface yet.
