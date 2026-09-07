"""Run the financial-report preparation pipeline in order."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path

from Chunking.chunk import chunk_process
from Extract.extract import clean_raw_text, extract_data
from Extract.text_analysis import header_footer_separation


PROJECT_ROOT = Path(__file__).resolve().parent


@contextmanager
def working_directory(path):
    """Support the existing stages' relative paths and restore the caller's cwd."""
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf", type=Path,
        default=PROJECT_ROOT / "AnnualReports" / "Mastercard" / "Report.pdf",
        help="Input PDF (relative paths are resolved from your current directory).",
    )
    parser.add_argument("--start-page", type=int, default=1, help="First printed page (inclusive).")
    parser.add_argument("--end-page", type=int, default=132, help="Last printed page (inclusive).")
    parser.add_argument("--page-offset", type=int, default=-1, help="PDF index minus printed page number.")
    args = parser.parse_args()
    pdf_path = args.pdf.resolve()

    with working_directory(PROJECT_ROOT / "Extract"):
        print("[1/4] Extracting PDF pages...", flush=True)
        extract_data(args.start_page, args.end_page, args.page_offset, str(pdf_path))

        print("[2/4] Detecting headers and footers...", flush=True)
        header_footer_separation()

        print("[3/4] Cleaning text...", flush=True)
        clean_raw_text()

    with working_directory(PROJECT_ROOT / "Chunking"):
        print("[4/4] Creating chunks...", flush=True)
        chunk_process()

    print(f"Done. Chunks saved to {PROJECT_ROOT / 'Chunking' / 'chunk.jsonl'}")


if __name__ == "__main__":
    main()
