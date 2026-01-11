from datetime import datetime
from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User
from app.services.maintenance import create_backup, restore_backup, system_stats

router = APIRouter()


class AuditLogItem(BaseModel):
    timestamp: datetime
    user: str
    action: str
    target_file: Optional[str]


class AuditLogResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AuditLogItem]


class SystemStatsResponse(BaseModel):
    total_documents: int
    storage_mb: float
    last_backup: Optional[str]


@router.get("/audit-logs", response_model=AuditLogResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogResponse:
    if current_user.role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    base_query = db.query(AuditLog)
    total = base_query.count()
    logs = (
        base_query.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: List[AuditLogItem] = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        document = None
        if log.target_id is not None:
            document = db.query(Document).filter(Document.id == log.target_id).first()
        items.append(
            AuditLogItem(
                timestamp=log.timestamp,
                user=user.username if user else "Unknown",
                action=log.action,
                target_file=document.filename if document else None,
            )
        )

    return AuditLogResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/stats", response_model=SystemStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SystemStatsResponse:
    if current_user.role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    total_documents = db.query(Document).count()
    stats = system_stats(total_documents=total_documents)
    return SystemStatsResponse(**stats.__dict__)


@router.post("/backup")
def download_backup(
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    if current_user.role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    backup_path = create_backup()
    return FileResponse(path=backup_path, filename=backup_path.name, media_type="application/zip")


@router.post("/restore")
def restore_from_backup(
    backup_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    if current_user.role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    temp_path = DATA_DIR / "restore_upload.zip"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with temp_path.open("wb") as out_file:
        out_file.write(backup_file.file.read())

    try:
        restore_backup(temp_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {"status": "restored"}
