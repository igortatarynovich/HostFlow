"""Platform Business Completion + optional handoff resolution."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.additional_service import ServiceItem, ServiceOrder
from backend.app.module_registry.resolver import is_module_installed
from backend.app.services.service_order_beneficiary import (
    item_requires_handoff,
    service_handoff_action,
    service_requires_handoff,
)

SALES_CLIENT_ACTIVE = "sales.client_active"
SERVICES_ORDER_COMPLETED = "services.order_completed"

_HANDOFF_LABELS: dict[str, dict[str, str]] = {
    "recruitment.create_search": {
        "label": "Начать подбор персонала",
        "hint": "Подбор создастся для этой компании — контакт уже подставлен из заказа.",
        "module": "recruitment",
    },
    "marketing.create_project": {
        "label": "Создать marketing project",
        "hint": "Маркетинг-проект запустится по строке заказа.",
        # No module gate yet — executor is pluggable per order line (roadmap).
        "module": "",
    },
}

_COMPLETION_COPY: dict[str, dict[str, str]] = {
    SALES_CLIENT_ACTIVE: {
        "completion_title": "Клиент активен",
        "completion_message": "{client_name} добавлен в базу клиентов.",
        "done_title": "Клиент добавлен",
        "done_message": "Клиент активен. Выберите услуги и создайте заказ — Services поведёт выполнение и счёт.",
        "done_action_label": "Открыть клиента",
    },
    SERVICES_ORDER_COMPLETED: {
        "completion_title": "Заказ выполнен",
        "completion_message": "Услуги по заказу завершены.",
        "done_title": "Заказ закрыт",
        "done_message": "Все inline-услуги выполнены. Handoff-действия доступны ниже, если применимо.",
        "done_action_label": "Открыть заказ",
    },
}


def _trim(value: Any) -> str:
    return str(value or "").strip()


def _handoff_spec(action: str) -> Optional[dict[str, str]]:
    return _HANDOFF_LABELS.get(str(action or "").strip())


async def _handoffs_from_service_order(
    db: AsyncSession,
    tenant_id: str,
    service_order_id: str,
    *,
    base_context: dict[str, Any],
) -> list[dict[str, Any]]:
    order = await db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id, ServiceOrder.tenant_id == tenant_id)
        .options(selectinload(ServiceOrder.items).selectinload(ServiceItem.service))
    )
    if order is None:
        return []

    ctx = dict(base_context)
    if order.company_id:
        ctx.setdefault("client_id", str(order.company_id))
    if order.candidate_id:
        ctx.setdefault("candidate_id", str(order.candidate_id))
    if order.employee_id:
        ctx.setdefault("employee_id", str(order.employee_id))
    ctx.setdefault("service_order_id", str(order.id))

    seen: set[str] = set()
    handoffs: list[dict[str, Any]] = []
    for item in order.items or []:
        svc = getattr(item, "service", None)
        item_meta = getattr(item, "meta", None)
        svc_meta = getattr(svc, "meta", None) if svc is not None else None
        if not item_requires_handoff(item_meta, svc_meta):
            continue
        action = service_handoff_action(item_meta) or service_handoff_action(svc_meta)
        if not action or action in seen:
            continue
        spec = _handoff_spec(action)
        module = str(spec.get("module") or "").strip() if spec else ""
        if module and not await is_module_installed(db, tenant_id, module):
            continue
        seen.add(action)
        handoffs.append(
            {
                "action": action,
                "label": (spec or {}).get("label") or action,
                "hint": (spec or {}).get("hint"),
                "context": {
                    **ctx,
                    "service_item_id": str(item.id),
                    "service_code": getattr(svc, "code", None),
                },
            }
        )
    return handoffs


async def resolve_platform_completion(
    db: AsyncSession,
    tenant_id: str,
    *,
    event: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve completion copy and optional platform handoff(s) for a domain event."""
    ev = str(event or "").strip()
    ctx = dict(context or {})
    copy = _COMPLETION_COPY.get(ev)
    if copy is None:
        return {
            "event": event,
            "completion": {
                "title": "Готово",
                "message": "Работа завершена.",
            },
            "handoff": None,
            "handoffs": [],
        }

    client_name = _trim(ctx.get("client_name")) or "Компания"
    completion = {
        "title": copy["completion_title"],
        "message": str(copy["completion_message"]).format(client_name=client_name),
    }

    service_order_id = _trim(ctx.get("service_order_id"))
    handoffs = await _handoffs_from_service_order(db, tenant_id, service_order_id, base_context=ctx) if service_order_id else []

    explicit_actions = ctx.get("handoff_actions")
    if isinstance(explicit_actions, list) and not handoffs:
        for raw in explicit_actions:
            action = _trim(raw)
            if not action:
                continue
            spec = _handoff_spec(action)
            module = str(spec.get("module") or "").strip() if spec else ""
            if module and not await is_module_installed(db, tenant_id, module):
                continue
            handoffs.append(
                {
                    "action": action,
                    "label": (spec or {}).get("label") or action,
                    "hint": (spec or {}).get("hint"),
                    "context": ctx,
                }
            )

    handoff = handoffs[0] if handoffs else None
    client_id = _trim(ctx.get("client_id"))

    if not handoff:
        return {
            "event": event,
            "completion": completion,
            "handoff": None,
            "handoffs": [],
            "done": {
                "title": copy["done_title"],
                "message": copy["done_message"],
                "action_label": copy["done_action_label"],
                "client_id": client_id or None,
            },
        }

    return {
        "event": event,
        "completion": completion,
        "handoff": handoff,
        "handoffs": handoffs,
        "done": None,
    }
