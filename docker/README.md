Postgres + pgvector (Docker)

Postgres + pgvector (Docker)

Quick start

 - Bring up the database:

 ```bash
 docker compose up -d
 ```

 - Verify logs:

 ```bash
 docker compose logs -f db
 ```

 - Connect using psql (example from host):

 ```bash
 PGPASSWORD=finpass psql -h localhost -p 55432 -U finusr -d findb
 ```

 Notes

 - `docker-compose.yml` uses the `ankane/pgvector:postgres-15` image which includes the `vector` extension.
 - Init scripts in `docker/initdb` are executed on first container initialization to create the extension and schema.
 - Update the vector dimension in `docker/initdb/01-init.sql` to match your model's embedding size (example uses 1536).

 Environment
 
 The compose file sets these defaults (change as needed):

 - `POSTGRES_USER=finusr`
 - `POSTGRES_PASSWORD=finpass`
 - `POSTGRES_DB=findb`

 Host port: the DB is exposed on host port `55432` (mapped to container `5432`).

- Bring up the database:

```bash
docker compose up -d
```

- Verify logs:

```bash
docker compose logs -f db
```

- Connect using psql (example from host):

```bash
PGPASSWORD=finpass psql -h localhost -U finusr -d findb
```

Notes

- `docker-compose.yml` uses the `ankane/pgvector:postgres-15` image which includes the `vector` extension.
- Init scripts in `docker/initdb` are executed on first container initialization to create the extension and schema.
- Update the vector dimension in `docker/initdb/01-init.sql` to match your model's embedding size (example uses 1536).

Environment

The compose file sets these defaults (change as needed):

- `POSTGRES_USER=finusr`
- `POSTGRES_PASSWORD=finpass`
- `POSTGRES_DB=findb`

If you want the container to use a different init filename or tweak volumes, edit `docker-compose.yml` accordingly.
