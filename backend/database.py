from typing import Generator

from sqlalchemy import create_engine, inspect, text
try:
    from sqlalchemy.engine import make_url
except ImportError:  # pragma: no cover - compatibility with newer SQLAlchemy builds
    from sqlalchemy.engine.url import make_url
try:
    from sqlalchemy.orm import declarative_base, sessionmaker
except ImportError:  # pragma: no cover - compatibility with older SQLAlchemy builds
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

from backend.config import get_settings


settings = get_settings()


def create_engine_compat(database_url: str, **kwargs):
    try:
        return create_engine(database_url, future=True, pool_pre_ping=True, **kwargs)
    except TypeError:
        return create_engine(database_url, pool_pre_ping=True, **kwargs)


engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine_compat(settings.database_url, **engine_kwargs)
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
    charset = url.query.get("charset", "utf8mb4")
    try:
        server_url = url.set(database="")
    except AttributeError:
        auth = ""
        if url.username:
            auth = url.username
            if url.password:
                auth = f"{auth}:{url.password}"
            auth = f"{auth}@"
        host = url.host or "127.0.0.1"
        port = f":{url.port}" if url.port else ""
        query = f"?charset={charset}" if charset else ""
        server_url = f"{url.drivername}://{auth}{host}{port}/{query}"
    server_engine = create_engine_compat(server_url)
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
