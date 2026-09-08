# PostgreSQL + pgvector (Docker)

This adds a local PostgreSQL with the `pgvector` extension for embeddings.

Files added:
- [docker-compose.yml](docker-compose.yml)
- [docker/initdb/init.sql](docker/initdb/init.sql)

Quick start:

1. Start the DB:

```bash
docker compose up -d
```

2. Connect with `psql` (example):

```bash
psql "postgresql://finusr:finpass@localhost:5432/findb"
```

3. Verify extension and table:

```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
\d+ embeddings
```

Notes:
- The image `ankane/pgvector:postgres-15` includes the `vector` extension built-in.
- The init SQL creates a sample `embeddings` table with `vector(1536)` — adjust dimension to your model.
