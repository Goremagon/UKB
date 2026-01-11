from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.search import search_documents
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User
from app.services.ingestion import ingest_file, parse_date
from app.services.sync import dry_run_summary, sync_directory
from app.services.storage import ensure_temp_dir

router = APIRouter()


class SearchResponse(BaseModel):
    doc_id: str
    title: str
    tags: str
    highlight: str
    is_sensitive: bool


class BulkSyncRequest(BaseModel):
    root_dir: str
    doc_type: str = "Unknown"
    department: Optional[str] = None
    date_published: Optional[date] = None
    tags: Optional[List[str]] = None
    is_sensitive: bool = False
    dry_run: bool = False


@router.post("/upload")
def upload_document(
    doc_type: str = Query(...),
    department: Optional[str] = Query(None),
    date_published: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    is_sensitive: bool = Query(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if is_sensitive and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required for sensitive uploads")
    temp_dir = ensure_temp_dir()
    temp_path = temp_dir / file.filename
    with temp_path.open("wb") as out_file:
        out_file.write(file.file.read())

    metadata = {
        "doc_type": doc_type,
        "department": department,
        "date_published": parse_date(date_published),
        "tags": tags.split(",") if tags else None,
        "is_sensitive": is_sensitive,
    }

    try:
        document = ingest_file(
            db=db,
            file_path=temp_path.as_posix(),
            filename=file.filename,
            metadata=metadata,
            user_id=current_user.id,
        )
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"id": document.id, "file_hash": document.file_hash}


@router.get("/search", response_model=List[SearchResponse])
def search_documents_endpoint(
    q: str = Query(..., min_length=1),
    doc_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if start_date:
        query = query.filter(Document.date_published >= parse_date(start_date))
    if end_date:
        query = query.filter(Document.date_published <= parse_date(end_date))
    if current_user.role != "Admin":
        query = query.filter(Document.is_sensitive.is_(False))

    documents = {doc.id: doc for doc in query.all()}
    allowed_ids = list(documents.keys())
    if not allowed_ids:
        return []

    results = search_documents(q, allowed_ids=allowed_ids)
    if not results:
        return []
    payload = []
    for item in results:
        doc_id = int(item["doc_id"])
        document = documents.get(doc_id)
        if not document:
            continue
        payload.append({**item, "is_sensitive": document.is_sensitive})

    db.add(AuditLog(user_id=current_user.id, action="search", target_id=None))
    db.commit()
    return payload


@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.is_sensitive and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")

    db.add(AuditLog(user_id=current_user.id, action="view", target_id=document.id))
    db.commit()
    return FileResponse(path=file_path, media_type="application/pdf", filename=document.filename)


@router.post("/sync")
def sync_documents(
    payload: BulkSyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    metadata = {
        "doc_type": payload.doc_type,
        "department": payload.department,
        "date_published": payload.date_published,
        "tags": payload.tags,
        "is_sensitive": payload.is_sensitive,
    }

    if payload.dry_run:
        summary = dry_run_summary(db, payload.root_dir)
        return {
            "status": "dry_run",
            "total_files": summary.total_files,
            "new_documents": summary.new_documents,
            "duplicate_documents": summary.duplicate_documents,
        }

    background_tasks.add_task(sync_directory, payload.root_dir, metadata, current_user.id)
    return {"status": "scheduled"}
