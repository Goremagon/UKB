from datetime import date
import csv
import io
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
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
    doc_type: str
    tags: str
    highlight: str
    is_sensitive: bool
    ai_summary: Optional[List[str]] = None


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
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if department:
        query = query.filter(Document.department == department)
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
        payload.append(
            {
                **item,
                "doc_type": document.doc_type,
                "is_sensitive": document.is_sensitive,
                "ai_summary": document.ai_summary,
            }
        )

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


@router.get("/export")
def export_search_results(
    q: str = Query(..., min_length=1),
    doc_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if department:
        query = query.filter(Document.department == department)
    if start_date:
        query = query.filter(Document.date_published >= parse_date(start_date))
    if end_date:
        query = query.filter(Document.date_published <= parse_date(end_date))
    if current_user.role != "Admin":
        query = query.filter(Document.is_sensitive.is_(False))

    documents = {doc.id: doc for doc in query.all()}
    allowed_ids = list(documents.keys())
    if not allowed_ids:
        return StreamingResponse(iter(()), media_type="text/csv")

    results = search_documents(q, allowed_ids=allowed_ids, limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Filename", "Date", "Department", "Tags"])
    for item in results:
        doc_id = int(item["doc_id"])
        document = documents.get(doc_id)
        if not document:
            continue
        tags = ",".join(document.tags) if isinstance(document.tags, list) else (document.tags or "")
        writer.writerow(
            [
                document.filename,
                document.date_published.isoformat() if document.date_published else "",
                document.department or "",
                tags,
            ]
        )

    db.add(AuditLog(user_id=current_user.id, action="export", target_id=None))
    db.commit()

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=ukb_search_export.csv"
    return response


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
