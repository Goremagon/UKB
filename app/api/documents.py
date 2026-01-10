from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.search import search_documents
from app.core.security import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.ingestion import ingest_file, parse_date
from app.services.storage import ensure_temp_dir

router = APIRouter()


class SearchResponse(BaseModel):
    doc_id: str
    title: str
    tags: str
    highlight: str


@router.post("/upload")
def upload_document(
    doc_type: str = Query(...),
    department: Optional[str] = Query(None),
    date_published: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    temp_dir = ensure_temp_dir()
    temp_path = temp_dir / file.filename
    with temp_path.open("wb") as out_file:
        out_file.write(file.file.read())

    metadata = {
        "doc_type": doc_type,
        "department": department,
        "date_published": parse_date(date_published),
        "tags": tags.split(",") if tags else None,
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
    results = search_documents(q)
    if not results:
        return []

    ids = [int(item["doc_id"]) for item in results]
    query = db.query(Document).filter(Document.id.in_(ids))
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if start_date:
        query = query.filter(Document.date_published >= parse_date(start_date))
    if end_date:
        query = query.filter(Document.date_published <= parse_date(end_date))

    allowed_ids = {doc.id for doc in query.all()}
    return [item for item in results if int(item["doc_id"]) in allowed_ids]


@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FileResponse(path=file_path, media_type="application/pdf", filename=document.filename)
