from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from pgvector.psycopg2 import register_vector
except ImportError:  # pragma: no cover - optional until dependencies are installed
    register_vector = None


Base = declarative_base()


def create_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    user = os.getenv("DB_USER", "finusr")
    password = os.getenv("DB_PASSWORD", "finpass")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "55432")
    database = os.getenv("DB_NAME", "findb")
    driver = os.getenv("DB_DRIVER", "postgresql+psycopg2")
    return f"{driver}://{user}:{password}@{host}:{port}/{database}"


DATABASE_URL = create_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

if register_vector is not None:
    event.listen(engine, "connect", lambda dbapi_connection, connection_record: register_vector(dbapi_connection))

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    with session_scope() as db:
        result = db.execute(text("SELECT version()"))
        print("Connection successful")
        print(result.scalar_one())
