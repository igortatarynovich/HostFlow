from __future__ import annotations

# backend/app/models/service.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


def gen_uuid() -> str:
    return str(uuid4())


class ServiceCatalog(Base):
    __tablename__ = "service_catalog"

    id = Column(String, primary_key=True, default=gen_uuid)  # UUID по умолчанию
    tenant_id = Column(String, index=True, nullable=False)

    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True, default=dict)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_service_catalog_tenant_code"),
        Index("ix_service_catalog_tenant_active", "tenant_id", "is_active"),
    )


class CandidateService(Base):
    __tablename__ = "candidate_services"

    id = Column(String, primary_key=True, default=gen_uuid)  # UUID по умолчанию
    tenant_id = Column(String, index=True, nullable=False)

    candidate_id = Column(
        String, ForeignKey("candidates.id"), nullable=False, index=True
    )
    service_id = Column(
        String, ForeignKey("service_catalog.id"), nullable=False, index=True
    )

    status = Column(
        String, nullable=False, default="assigned"
    )  # assigned|in_progress|done|canceled...
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=True)  # PLN/EUR/...
    quantity = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime, nullable=True)

    service = relationship("app.models.services.ServiceCatalog", lazy="joined")

    __table_args__ = (
        Index("ix_candidate_services_tenant_candidate", "tenant_id", "candidate_id"),
        Index("ix_candidate_services_tenant_service", "tenant_id", "service_id"),
    )
