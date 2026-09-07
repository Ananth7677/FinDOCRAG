# config.py

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
EXTRACT_DIR = RESULTS_DIR / "extract"
ANALYSIS_DIR = RESULTS_DIR / "analysis"
CLEAN_DIR = RESULTS_DIR / "clean"
CHUNK_DIR = RESULTS_DIR / "chunking"
EMBEDDING_DIR = RESULTS_DIR / "embedding"

# Ensure all results directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDING_DIR.mkdir(parents=True, exist_ok=True)

EXTRACTED_DATA_PATH = EXTRACT_DIR / "extracted_data.jsonl"
METADATA_PATH = EXTRACT_DIR / "metadata.json"
PATTERNS_PATH = ANALYSIS_DIR / "chrome_patterns.json"
PAGES_PATH = CLEAN_DIR / "pages.jsonl"
CHUNKS_PATH = CHUNK_DIR / "chunk.jsonl"
EMBEDDINGS_PATH = EMBEDDING_DIR / "embeddings.jsonl"

load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_gemini_api_key():
    key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in .env before embedding.")
    return key
