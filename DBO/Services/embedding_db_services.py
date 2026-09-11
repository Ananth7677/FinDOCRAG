from DBO.Models.embedding import Embedding
from DBO.database import session_scope
from DTO.embedding_dto import EmbeddingDTO, to_insert_values
from sqlalchemy import select

def insert_embedding(dto: EmbeddingDTO) -> int:
    """Insert a validated embedding and return its generated database ID.

    The transaction commits on success and rolls back if insertion fails.
    The source chunk ID is stored in metadata, separate from the database ID.
    """
    row = Embedding(**to_insert_values(dto))

    with session_scope() as db:
        db.add(row)
        db.flush()  # Execute the INSERT so PostgreSQL generates row.id.
        database_id = row.id

    return database_id

def get_lastest_embedding_record(doc_id: str)-> Embedding | None:
    with session_scope() as db:
        statement = (
            select(Embedding).where(Embedding.doc_id == doc_id).order_by(Embedding.id.desc()).limit(1)
        )
        
        return db.scalars(statement).first()

def topkresults(user_query_embedding: list, limit: int = 10):
    distance = Embedding.embedding.cosine_distance(user_query_embedding)
    similarity = (1 - distance).label("similarity")
    
    statement = select(Embedding, similarity).order_by(distance).limit(limit)
    
    with session_scope() as db:
        rows = db.execute(statement).all()
        print(rows)
        results = []
        for embedding, similarity_score in rows:
            results.append({
                "id": embedding.id,
                "text": embedding.text,
                "page_number": embedding.page_number,
                "section_text": embedding.section_text,
                "similarity": similarity_score
            })
        return results