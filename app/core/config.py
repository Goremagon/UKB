from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
INDEX_DIR = DATA_DIR / "index"
STORAGE_DIR = BASE_DIR / "storage"

DB_PATH = DB_DIR / "ukb.sqlite3"
SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def ensure_directories() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
