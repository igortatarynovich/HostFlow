import enum
from enum import Enum


class DocumentStatus(str, Enum):
    """Статусы документов (общие, используются для всех типов)."""
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
    # Новые статусы для EVIDENCE модели
    uploaded = "uploaded"
    verified = "verified"
    # Новые статусы для PROCESS_WP_A модели
    not_required = "not_required"
    to_prepare = "to_prepare"
    issued = "issued"
    cancelled = "cancelled"
    # Новые статусы для PROCESS_OSWIADCZENIE модели
    to_register = "to_register"
    registered = "registered"
    active = "active"
    # Новые статусы для PROCESS_RESIDENCE модели


class DocumentStatusModel(str, Enum):
    """Модель статусов документа (определяет набор допустимых статусов)."""
    EVIDENCE = "evidence"  # Документы-доказательства (паспорт, права, тахо, świadectwo, карта квалификации)
    PROCESS_WP_A = "process_wp_a"  # Work Permit A (процесс)
    PROCESS_OSWIADCZENIE = "process_oswiadczenie"  # Oświadczenie (процесс/регистрация)
    PROCESS_RESIDENCE = "process_residence"  # Residence Card (как замещение)


class RequirementType(str, Enum):
    """Типы виртуальных требований (requirements)."""
    ID_EVIDENCE = "id_evidence"  # Документ удостоверения личности
    CODE95_EVIDENCE = "code95_evidence"  # Доказательство Code 95 (составное требование)
    RIGHT_TO_WORK_BASIS = "right_to_work_basis"  # Право работать (составное требование)
    CORE_PRO_DRIVER_SET = "core_pro_driver_set"  # Базовый проф-набор для рейса (составное)
    DRIVERS_CERTIFICATE_IF_REQUIRED = "drivers_certificate_if_required"  # Условное требование


class GateCode(str, Enum):
    """Коды stage gates (блокировки этапов)."""
    GATE_DOCS_RECEIVED = "gate_docs_received"  # "Документы получены"
    GATE_PLAN_ARRIVAL = "gate_plan_arrival"  # "Планируем приезд"
    GATE_ON_CLIENT_BASE = "gate_on_client_base"  # "На базе клиента"
    GATE_ON_ROUTE = "gate_on_route"  # "Выехал в рейс"


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
    """Legacy UI enum with **Russian display strings as values** — not the canonical ``candidates.stage`` codes.

    Do **not** use for writes to ``Candidate.stage`` (canonical codes are ``new``, ``docs_wait``, … in
    ``backend.app.constants.stages``). Kept for backwards compatibility in analytics / exports that
    still branch on ``isinstance(..., CandidateStage)``.
    """

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
