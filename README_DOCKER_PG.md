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
psql "postgresql://finusr:finpass@localhost:55432/findb"
```

3. Verify extension and table:

```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
\d+ embeddings
```

Notes:
- The image `ankane/pgvector:latest` includes the `vector` extension built-in.
- The init SQL creates sample tables with `vector(768)` — adjust dimension to your model if needed.

Python session example:

```python
from DBO.database import SessionLocal

db = SessionLocal()
try:
	print(db.execute("SELECT 1").scalar())
finally:
	db.close()
```
