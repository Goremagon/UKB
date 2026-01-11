import hashlib
import shutil
from pathlib import Path

from app.core.config import STORAGE_DIR, ensure_directories


def compute_sha256(file_path: str) -> str:
    hash_obj = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def move_to_storage(source_path: str, file_hash: str) -> str:
    ensure_directories()
    target_name = f"{file_hash}.pdf"
    target_path = STORAGE_DIR / target_name
    shutil.move(source_path, target_path)
    return target_path.as_posix()


def ensure_temp_dir() -> Path:
    temp_dir = STORAGE_DIR / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
