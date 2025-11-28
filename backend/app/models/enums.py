import enum
from enum import Enum


class DocumentStatus(str, Enum):
    missing = "missing"
    requested = "requested"
    in_progress = "in_progress"
    submitted = "submitted"
    received = "received"
    delivered = "delivered"
    approved = "approved"
    completed = "completed"
    overdue = "overdue"
    rejected = "rejected"
    expired = "expired"


class DocumentKind(str, Enum):
    driver = "driver"
    employer = "employer"
    process = "process"


class DocumentRequestedFrom(str, Enum):
    driver = "driver"
    employer = "employer"
    agency = "agency"


class DocumentProcessType(str, Enum):
    none = "none"
    work_permit = "work_permit"
    visa = "visa"
    residence_card = "residence_card"
    tachograph_card = "tachograph_card"
    driver_license_exchange = "driver_license_exchange"
    swiadectwo_kierowcy = "swiadectwo_kierowcy"
    other = "other"


class DocumentDuplicatePolicy(str, Enum):
    one_per_candidate = "one_per_candidate"
    many_allowed = "many_allowed"


class ScanSessionStatus(str, Enum):
    in_progress = "in_progress"
    processing = "processing"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"


class ScanPageStatus(str, Enum):
    pending = "pending"
    uploaded = "uploaded"
    processing = "processing"
    ok = "ok"
    needs_review = "needs_review"
    rejected = "rejected"
    error = "error"


class CandidateStage(str, enum.Enum):
    NEW = "Новый"
    NO_RESPONSE = "Не отвечает"
    CONTACT = "Контакт установлен"
    WAIT_DOCS = "Ожидаем документы"
    DOCS_OK = "Документы получены"
    PERMIT_ORDERED = "Заказ разрешения"
    VISA_FLOW = "Виза"
    RED_PAPER = "Красная бумага заказана"
    READY_TO_GO = "Готов к выезду"
    PLAN_ARRIVAL = "Планируем приезд"
    AT_BASE = "На базе клиента"
    HIRED = "Трудоустроен"
    REJECTED = "Отклонён"
    DECLINED = "Отказался"
