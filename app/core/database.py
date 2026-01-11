from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DB_PATH, ensure_directories
from app.models.base import Base


def get_database_url() -> str:
    return f"sqlite:///{DB_PATH.as_posix()}"


engine = create_engine(get_database_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    ensure_directories()
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
