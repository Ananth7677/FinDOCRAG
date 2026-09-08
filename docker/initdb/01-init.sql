-- Init script for Postgres with pgvector
-- Creates the pgvector extension and an example table with an embedding column.

-- Adjust vector dimension to match your embeddings (e.g. 1536).
-- Adjust vector dimension to match your embeddings (use 768 for some models).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding VECTOR(768)
);

-- Example: create an index for ANN searches using ivfflat
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
