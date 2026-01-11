from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.ingestion import ingest_file
from app.services.storage import compute_sha256


@dataclass
class SyncSummary:
    new_documents: int
    duplicate_documents: int
    total_files: int


def iter_pdf_files(root_dir: str) -> Iterable[Path]:
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    for path in root_path.rglob("*.pdf"):
        if path.is_file():
            yield path


def dry_run_summary(db: Session, root_dir: str) -> SyncSummary:
    new_docs = 0
    duplicates = 0
    total = 0
    for pdf_path in iter_pdf_files(root_dir):
        total += 1
        file_hash = compute_sha256(pdf_path.as_posix())
        existing = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing:
            duplicates += 1
        else:
            new_docs += 1

    return SyncSummary(new_documents=new_docs, duplicate_documents=duplicates, total_files=total)


def sync_directory(
    root_dir: str,
    metadata: Dict[str, object],
    user_id: int | None = None,
) -> SyncSummary:
    db = SessionLocal()
    try:
        summary = dry_run_summary(db, root_dir)
        for pdf_path in iter_pdf_files(root_dir):
            try:
                ingest_file(
                    db=db,
                    file_path=pdf_path.as_posix(),
                    filename=pdf_path.name,
                    metadata=metadata,
                    user_id=user_id,
                )
            except ValueError:
                continue
        return summary
    finally:
        db.close()
