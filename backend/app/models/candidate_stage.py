from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from backend.app.db.base import Base

try:
    UUIDType = PGUUID(as_uuid=True)
except Exception:
    pass  # фоллбек для SQLite


class CandidateStageDict(Base):
    __tablename__ = "candidate_stage_dict"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        String(36), nullable=True, index=True
    )  # null = глобальная запись
    code = Column(String(50), nullable=False)  # 'new'
    label = Column(String(100), nullable=False)  # 'Новый'
    order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_stage_tenant_code"),
    )
