from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import BACKUP_SCHEMA_VERSION, DATA_DIR, DB_PATH, INDEX_DIR, STORAGE_DIR, ensure_directories


@dataclass
class SystemStats:
    total_documents: int
    storage_mb: float
    last_backup: Optional[str]


def _metadata_payload() -> dict:
    return {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_last_backup(backup_path: Path) -> None:
    payload = {
        "last_backup": datetime.now(timezone.utc).isoformat(),
        "path": backup_path.as_posix(),
    }
    last_backup_file = DATA_DIR / "last_backup.json"
    last_backup_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_last_backup() -> Optional[str]:
    last_backup_file = DATA_DIR / "last_backup.json"
    if not last_backup_file.exists():
        return None
    try:
        payload = json.loads(last_backup_file.read_text(encoding="utf-8"))
        return payload.get("last_backup")
    except json.JSONDecodeError:
        return None


def get_storage_size_mb() -> float:
    total_bytes = 0
    if STORAGE_DIR.exists():
        for path in STORAGE_DIR.rglob("*"):
            if path.is_file():
                total_bytes += path.stat().st_size
    return round(total_bytes / (1024 * 1024), 2)


def create_backup(destination: Optional[Path] = None) -> Path:
    ensure_directories()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = destination or (DATA_DIR / f"ukb_backup_{timestamp}.zip")

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("metadata.json", json.dumps(_metadata_payload(), indent=2))
        if DB_PATH.exists():
            archive.write(DB_PATH, arcname=f"db/{DB_PATH.name}")
        if INDEX_DIR.exists():
            for path in INDEX_DIR.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=f"index/{path.relative_to(INDEX_DIR)}")
        if STORAGE_DIR.exists():
            for path in STORAGE_DIR.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=f"storage/{path.relative_to(STORAGE_DIR)}")

    _write_last_backup(backup_path)
    return backup_path


def restore_backup(backup_path: Path) -> None:
    ensure_directories()
    if not backup_path.exists():
        raise FileNotFoundError("Backup file not found")

    temp_dir = DATA_DIR / "restore_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path, "r") as archive:
        archive.extractall(temp_dir)

    metadata_file = temp_dir / "metadata.json"
    if not metadata_file.exists():
        raise ValueError("Backup metadata missing")

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    if metadata.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise ValueError("Unsupported backup schema version")

    extracted_db = next((temp_dir / "db").glob("*.sqlite3"), None)
    if extracted_db:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(extracted_db, DB_PATH)

    extracted_index = temp_dir / "index"
    if extracted_index.exists():
        if INDEX_DIR.exists():
            shutil.rmtree(INDEX_DIR)
        shutil.copytree(extracted_index, INDEX_DIR)

    extracted_storage = temp_dir / "storage"
    if extracted_storage.exists():
        if STORAGE_DIR.exists():
            shutil.rmtree(STORAGE_DIR)
        shutil.copytree(extracted_storage, STORAGE_DIR)

    shutil.rmtree(temp_dir)


def system_stats(total_documents: int) -> SystemStats:
    return SystemStats(
        total_documents=total_documents,
        storage_mb=get_storage_size_mb(),
        last_backup=get_last_backup(),
    )
