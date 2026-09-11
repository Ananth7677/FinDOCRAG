from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator


class EmbeddingDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)  # Chunk ID from your JSON
    doc_id: str = Field(default="Mastercardreport", min_length=1)
    page_number: int = Field(gt=0)
    section_text: str | None = None
    text: str = Field(min_length=1)
    embedding: list[FiniteFloat] = Field(
        min_length=768,
        max_length=768,
    )

    @field_validator("doc_id", mode="before")
    @classmethod
    def default_doc_id(cls, value: object) -> object:
        return "Mastercardreport" if value is None else value
    
def to_insert_values(dto: EmbeddingDTO) -> dict:
    """Map validated input to Embedding ORM constructor arguments."""
    return {
        "doc_id": dto.doc_id,
        "embedding": dto.embedding,
        "chunk_id": dto.id,
        "page_number": dto.page_number,
        "section_text": dto.section_text,
        "text": dto.text,        
    }