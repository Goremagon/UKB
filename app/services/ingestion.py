from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.search import index_document
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.services.pdf import extract_text
from app.services.storage import compute_sha256, move_to_storage


def ingest_file(
    db: Session,
    file_path: str,
    filename: str,
    metadata: Dict[str, Any],
    user_id: Optional[int] = None,
) -> Document:
    file_hash = compute_sha256(file_path)
    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        raise ValueError("Duplicate document detected")

    text = extract_text(file_path)
    stored_path = move_to_storage(file_path, file_hash)

    document = Document(
        filename=filename,
        file_path=stored_path,
        file_hash=file_hash,
        doc_type=metadata.get("doc_type", "Unknown"),
        department=metadata.get("department"),
        date_published=metadata.get("date_published"),
        tags=metadata.get("tags"),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    index_document(
        doc_id=str(document.id),
        title=document.filename,
        content=text,
        tags=",".join(document.tags) if isinstance(document.tags, list) else (document.tags or ""),
    )

    if user_id is not None:
        audit = AuditLog(user_id=user_id, action="upload", target_id=document.id)
        db.add(audit)
        db.commit()

    return document


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)
