"""HTTP endpoints for the individual document-processing stages."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from Chunking.chunk import chunk_process
from Embedding.embedding import create_embedding, create_query_embedding
from Extract.extract import clean_raw_text, extract_data
from Extract.text_analysis import header_footer_separation
from DBO.Services.embedding_db_services import topkresults

from config import (
    PROJECT_ROOT, EXTRACT_DIR, CLEAN_DIR, CHUNK_DIR,
    EXTRACTED_DATA_PATH, METADATA_PATH, PATTERNS_PATH,
    PAGES_PATH, CHUNKS_PATH, EMBEDDINGS_PATH,
)

router = APIRouter(prefix="/api", tags=["Pipeline"])


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pdf: str = Field(default="AnnualReports/Mastercard/Report.pdf", min_length=1)
    start_page: int = Field(default=1, ge=1)
    end_page: int = Field(default=132, ge=1)
    page_offset: int = -1

    @model_validator(mode="after")
    def validate_page_range(self):
        if self.end_page < self.start_page:
            raise ValueError("end_page must be greater than or equal to start_page")
        if self.start_page + self.page_offset < 0:
            raise ValueError("start_page + page_offset must not be negative")
        return self


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_fraction: float = Field(default=0.05, ge=0, lt=0.5)
    bottom_fraction: float = Field(default=0.05, ge=0, lt=0.5)


class StageResponse(BaseModel):
    stage: str
    status: str
    outputs: list[str]
    
class UserQueryRequest(BaseModel):
    question: str
    
class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    text: str
    page_number: int
    section_text: str | None = None
    similarity: float


@router.post("/extract", response_model=StageResponse)
def extract(request: ExtractRequest):
    """Extract PDF text and source metadata. Paths are local to the server."""
    pdf = Path(request.pdf)
    if not pdf.is_absolute():
        pdf = PROJECT_ROOT / pdf
    if not pdf.is_file():
        raise HTTPException(status_code=404, detail="Input PDF was not found.")
    extract_data(request.start_page, request.end_page, request.page_offset,
                 str(pdf), output_dir=EXTRACT_DIR)
    return {"stage": "extract", "status": "completed",
            "outputs": [str(EXTRACTED_DATA_PATH.relative_to(PROJECT_ROOT)), str(METADATA_PATH.relative_to(PROJECT_ROOT))]}


@router.post("/analyze", response_model=StageResponse)
def analyze(request: AnalysisRequest = AnalysisRequest()):
    """Detect header and footer patterns from extracted pages."""
    header_footer_separation(request.top_fraction, request.bottom_fraction,
                             file_path=EXTRACTED_DATA_PATH,
                             output_path=PATTERNS_PATH)
    return {"stage": "analyze", "status": "completed",
            "outputs": [str(PATTERNS_PATH.relative_to(PROJECT_ROOT))]}


@router.post("/clean", response_model=StageResponse)
def clean():
    """Clean extracted text using previously detected patterns."""
    clean_raw_text(EXTRACTED_DATA_PATH,
                   patterns_path=PATTERNS_PATH, output_dir=CLEAN_DIR)
    return {"stage": "clean", "status": "completed", "outputs": [str(PAGES_PATH.relative_to(PROJECT_ROOT))]}


@router.post("/chunk", response_model=StageResponse)
def chunk():
    """Create overlapping chunks from cleaned pages."""
    chunk_process(PAGES_PATH, output_dir=CHUNK_DIR)
    return {"stage": "chunk", "status": "completed", "outputs": [str(CHUNKS_PATH.relative_to(PROJECT_ROOT))]}


@router.post("/embed", response_model=StageResponse)
def embed():
    """Generate Gemini embeddings for the current chunks."""
    from config import get_gemini_api_key

    if not (CHUNKS_PATH).is_file():
        raise HTTPException(status_code=409, detail="Run chunking before embedding.")
    try:
        get_gemini_api_key()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    from Embedding.embedding import process_embedding

    process_embedding(CHUNKS_PATH, output_path=EMBEDDINGS_PATH)
    return {"stage": "embed", "status": "completed", "outputs": [str(EMBEDDINGS_PATH.relative_to(PROJECT_ROOT))]}

@router.post("/userquery", response_model=list[EmbeddingResponse])
def user_query(user_query: UserQueryRequest):
    embedding_result = create_query_embedding(user_query.question)
    return topkresults(embedding_result)