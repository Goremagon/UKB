from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.types import JSON

from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, unique=True, nullable=False, index=True)
    doc_type = Column(String, nullable=False)
    department = Column(String, nullable=True)
    date_published = Column(Date, nullable=True)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    tags = Column(JSON, nullable=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
