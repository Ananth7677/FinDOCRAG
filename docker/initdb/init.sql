-- Initialize pgvector extension and sample table
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS embeddings (
  id serial PRIMARY KEY,
  doc_id text,
  embedding vector(768),
  metadata jsonb,
  created_at timestamptz DEFAULT now()
);
