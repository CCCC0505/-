from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import get_settings


settings = get_settings()

engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_mysql_database_exists() -> None:
    url = make_url(settings.database_url)
    if url.get_backend_name() != "mysql" or not url.database:
        return

    database_name = url.database
    server_url = url.set(database="")
    charset = url.query.get("charset", "utf8mb4")
    server_engine = create_engine(server_url, future=True, pool_pre_ping=True)
    try:
        with server_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET {charset}")
            )
    finally:
        server_engine.dispose()


def init_database() -> None:
    from backend import models  # noqa: F401

    ensure_mysql_database_exists()
    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns()


def ensure_runtime_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        if "students" in inspector.get_table_names():
            student_columns = {col["name"] for col in inspector.get_columns("students")}
            if "weekly_target_questions" not in student_columns:
                conn.execute(text("ALTER TABLE students ADD COLUMN weekly_target_questions INTEGER NOT NULL DEFAULT 12"))

        if "recommendation_batches" in inspector.get_table_names():
            batch_columns = {col["name"] for col in inspector.get_columns("recommendation_batches")}
            if "training_mode" not in batch_columns:
                conn.execute(text("ALTER TABLE recommendation_batches ADD COLUMN training_mode VARCHAR(32) NOT NULL DEFAULT 'balanced'"))
