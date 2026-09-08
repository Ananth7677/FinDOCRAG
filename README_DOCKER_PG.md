# PostgreSQL + pgvector (Docker)

This adds a local PostgreSQL with the `pgvector` extension for embeddings.

Files used:
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
- The init SQL creates the `embeddings` table with `vector(768)` — adjust dimension to your model if needed.

Python session example:

```python
from DBO.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print(db.execute(text("SELECT 1")).scalar_one())
finally:
    db.close()
```

If you run the connection test directly:

```bash
python DBO/database.py
```
