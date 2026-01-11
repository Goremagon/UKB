from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User

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
