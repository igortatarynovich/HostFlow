from __future__ import annotations

import asyncio
import csv
import io
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_maker
from backend.app.models import LeadImportJob, LeadImportJobStatus
from backend.app.modules.leads import crud, normalizer, service as leads_service
from backend.app.modules.leads.service import LeadProcessingError, MetaLeadResult
from backend.app.services import notifications
from backend.app.services import user_notifications


class LeadImportJobError(Exception):
    """Raised when CSV validation fails."""


IMPORT_SOURCE = "csv_import"

# Lightweight registry of running asyncio tasks (in-process only).
_IMPORT_TASKS: Dict[str, asyncio.Task[None]] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_header(name: str) -> str:
    return (name or "").strip().lower()


def _decode_csv_bytes(content: bytes) -> str:
    if not content:
        raise LeadImportJobError("CSV_EMPTY")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LeadImportJobError("CSV_ENCODING_UNSUPPORTED") from exc


def _parse_csv(content: bytes) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    text = _decode_csv_bytes(content)
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise LeadImportJobError("CSV_HEADER_MISSING")

    headers = [h.strip() for h in reader.fieldnames if h and h.strip()]
    normalized_headers = {_normalize_header(h) for h in headers}
    if "email" not in normalized_headers and "phone" not in normalized_headers and "phone_number" not in normalized_headers:
        raise LeadImportJobError("CSV_MISSING_CONTACT_COLUMNS")

    rows: List[Tuple[int, Dict[str, str]]] = []
    for index, row in enumerate(reader, start=2):
        if row is None:
            continue
        cleaned = {
            (key or "").strip(): (value or "").strip()
            for key, value in row.items()
            if key is not None
        }
        if not any(value for value in cleaned.values()):
            continue
        rows.append((index, cleaned))

    if not rows:
        raise LeadImportJobError("CSV_EMPTY_ROWS")

    return headers, rows


def _first_present(data: Dict[str, str], *aliases: str) -> Optional[str]:
    for alias in aliases:
        value = data.get(alias)
        if value:
            return value
    return None


def _flat_row_needs_meta_coercion(payload: Dict[str, Any]) -> bool:
    """Same rules as ``service._payload_needs_flat_field_data_coercion`` (avoid import cycles)."""
    if not isinstance(payload, dict) or not payload:
        return False
    entry = payload.get("entry")
    if isinstance(entry, list) and len(entry) > 0:
        return False
    if isinstance(payload.get("field_data"), list):
        return False
    return True


def _overlay_meta_export_normalization(
    row: Dict[str, str],
    *,
    field_mapping: Optional[Any],
    base: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Meta Lead Center exports are flat tab/CSV rows with ``ad_id`` = ``ag:…`` in ``field_data`` shape
    when coerced. The hand-built ``base`` dict omits ``ad_id``, so vacancy routing via
    ``meta_ads_map`` never runs unless we merge the full normalizer output.
    """
    flat: Dict[str, Any] = {k: v for k, v in row.items() if k is not None}
    if not _flat_row_needs_meta_coercion(flat):
        return base
    wrapped = normalizer.coerce_generic_json_to_meta_normalizer_payload(flat)
    rich = normalizer.normalize_meta_payload(wrapped, field_mapping=field_mapping)
    out = dict(base)
    merge_keys = (
        "ad_id",
        "phone",
        "email",
        "first_name",
        "last_name",
        "full_name",
        "phone_country_code",
        "preferred_contact",
        "poland_stay_basis",
        "poland_stay_basis_raw",
        "driving_experience_in_europe",
        "experience_eu_years",
        "geo_country",
        "geo_country_raw",
        "country",
        "country_raw",
        "in_poland",
        "utm",
        "company_id",
        "company_name_hint",
        "vacancy_id",
        "vacancy_hint",
        "vacancy_id_hint",
    )
    for k in merge_keys:
        v = rich.get(k)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        out[k] = v
    if rich.get("raw_field_names"):
        out["raw_field_names"] = rich["raw_field_names"]
    if rich.get("company_hints"):
        out["company_hints"] = rich["company_hints"]
    return out


def _normalize_row(
    tenant_id: str,
    row: Dict[str, str],
    headers: List[str],
    *,
    field_mapping: Optional[Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    lower_map = {_normalize_header(k): v for k, v in row.items()}

    first_name = lower_map.get("first_name") or ""
    last_name = lower_map.get("last_name") or ""
    full_name = lower_map.get("full_name") or ""
    if not first_name and not last_name and full_name:
        parts = normalizer._split_full_name(full_name)
        first_name = parts.get("first_name", "")
        last_name = parts.get("last_name", "")
    email = (lower_map.get("email") or "").strip().lower() or None

    phone = None
    for alias in normalizer.PHONE_ALIASES:
        candidate = lower_map.get(alias)
        if candidate:
            phone = normalizer._clean_phone(candidate)
            if phone:
                break

    preferred_contact = _first_present(lower_map, *normalizer.CONTACT_ALIASES)
    in_poland_raw = _first_present(lower_map, *normalizer.IN_POLAND_ALIASES)
    in_poland_val = normalizer._normalize_bool_hint(in_poland_raw)

    poland_basis = _first_present(lower_map, *normalizer.POLAND_STAY_BASIS_ALIASES)

    company_id = lower_map.get("company_id") or None
    company_name_hint = _first_present(lower_map, *normalizer.COMPANY_ALIASES)
    company_hints: List[str] = []
    if company_name_hint:
        company_hints.append(company_name_hint)

    vcol = lower_map.get("vacancy_id")
    vacancy_id_hint = (str(vcol).strip() if vcol else None) or None
    vacancy_id_resolved: Optional[str] = None
    if vacancy_id_hint:
        try:
            vacancy_id_resolved = str(UUID(vacancy_id_hint))
        except ValueError:
            vacancy_id_resolved = None

    if not email and not phone:
        raise LeadImportJobError("ROW_NO_CONTACTS")

    dedupe_seed = f"{tenant_id}|{email or ''}|{phone or ''}"
    dedupe_hash = hashlib.sha256(dedupe_seed.encode("utf-8")).hexdigest()
    external_id = f"{IMPORT_SOURCE}:{dedupe_hash}"

    raw_lead_key = (
        _first_present(lower_map, "id", "leadgen_id", "external_id") or external_id
    )

    normalized: Dict[str, Any] = {
        "raw_lead_id": raw_lead_key,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name or f"{first_name} {last_name}".strip(),
        "email": email,
        "phone": phone,
        "phone_country_code": normalizer._infer_country_code(phone),
        "preferred_contact": preferred_contact,
        "in_poland": in_poland_val if in_poland_val is not None else in_poland_raw,
        "poland_stay_basis": poland_basis,
        "company_id": company_id,
        "company_name_hint": company_name_hint,
        "company_hints": company_hints,
        "vacancy_id_hint": vacancy_id_hint,
        "vacancy_id": vacancy_id_resolved,
        "raw_field_names": headers,
    }

    ad_raw = _first_present(lower_map, "ad_id", "adset_id", "adgroup_id")
    parsed_ad = normalizer.parse_meta_export_ad_id(ad_raw) if ad_raw else None
    if parsed_ad is not None:
        normalized["ad_id"] = parsed_ad

    # Full Meta Lead Center row: merge routing + criteria fields (same as webhook reprocess).
    # Require ``ad_id`` — plain CRM CSVs often have ``company_id`` / ``vacancy_id`` only and must
    # not be passed through the Meta normalizer overlay.
    if any(_normalize_header(h) == "ad_id" for h in headers):
        normalized = _overlay_meta_export_normalization(
            row, field_mapping=field_mapping, base=normalized
        )

    payload = dict(row)
    return normalized, payload, external_id


async def create_import_job(
    db: AsyncSession,
    *,
    tenant_id: str,
    created_by: str,
    filename: str,
) -> LeadImportJob:
    job = LeadImportJob(
        tenant_id=tenant_id,
        created_by=created_by,
        filename=filename,
        status=LeadImportJobStatus.pending,
        total_rows=0,
        processed_rows=0,
        success_rows=0,
        duplicate_rows=0,
        failed_rows=0,
        error_report=[],
    )
    db.add(job)
    await db.flush()
    return job


async def list_import_jobs(
    db: AsyncSession,
    *,
    tenant_id: str,
    limit: int = 20,
) -> List[LeadImportJob]:
    stmt = (
        select(LeadImportJob)
        .where(LeadImportJob.tenant_id == tenant_id)
        .order_by(LeadImportJob.created_at.desc())
        .limit(limit)
    )
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_import_job(
    db: AsyncSession,
    *,
    tenant_id: str,
    job_id: str,
) -> Optional[LeadImportJob]:
    job = await db.get(LeadImportJob, job_id)
    if job and job.tenant_id != tenant_id:
        return None
    return job


async def _send_lead_received_webhook(
    tenant_id: str,
    job_id: str,
    row_number: int,
    result: MetaLeadResult,
) -> None:
    await notifications.send_webhook(
        "lead.received",
        {
            "tenant_id": tenant_id,
            "job_id": job_id,
            "lead_id": result.lead_id,
            "status": result.status,
            "row_number": row_number,
        },
    )


async def _send_lead_failed_webhook(
    tenant_id: str,
    job_id: str,
    row_number: int,
    reason: str,
) -> None:
    await notifications.send_webhook(
        "lead.failed",
        {
            "tenant_id": tenant_id,
            "job_id": job_id,
            "row_number": row_number,
            "reason": reason,
        },
    )


async def _update_job_status(
    session: AsyncSession,
    job: LeadImportJob,
    *,
    status: str,
    success_rows: Optional[int] = None,
    duplicate_rows: Optional[int] = None,
    failed_rows: Optional[int] = None,
    processed_rows: Optional[int] = None,
    total_rows: Optional[int] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error_report: Optional[List[Dict[str, Any]]] = None,
) -> None:
    job.status = status
    if success_rows is not None:
        job.success_rows = success_rows
    if duplicate_rows is not None:
        job.duplicate_rows = duplicate_rows
    if failed_rows is not None:
        job.failed_rows = failed_rows
    if processed_rows is not None:
        job.processed_rows = processed_rows
    if total_rows is not None:
        job.total_rows = total_rows
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    if error_report is not None:
        job.error_report = list(error_report)
    await session.flush()


async def _notify_initiator(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    payload: Dict[str, Any],
    event_type: str,
) -> None:
    await user_notifications.create_notification(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        payload=payload,
    )
    await session.flush()


async def run_import_job(
    job_id: str,
    *,
    tenant_id: str,
    created_by: str,
    filename: str,
    content: bytes,
) -> None:
    headers: List[str]
    rows: List[Tuple[int, Dict[str, str]]]
    try:
        headers, rows = _parse_csv(content)
    except LeadImportJobError as exc:
        async with async_session_maker() as session:
            job = await session.get(LeadImportJob, job_id)
            if not job:
                return
            await _update_job_status(
                session,
                job,
                status=LeadImportJobStatus.failed,
                total_rows=0,
                processed_rows=0,
                success_rows=0,
                duplicate_rows=0,
                failed_rows=0,
                started_at=_utc_now(),
                finished_at=_utc_now(),
                error_report=[{"row": None, "error": str(exc)}],
            )
            await session.commit()
        await _send_lead_failed_webhook(tenant_id, job_id, 0, str(exc))
        return

    dedupe_in_file: set[str] = set()
    success_rows = duplicate_rows = failed_rows = 0
    errors: List[Dict[str, Any]] = []

    async with async_session_maker() as session:
        job = await session.get(LeadImportJob, job_id)
        if not job:
            return
        await _update_job_status(
            session,
            job,
            status=LeadImportJobStatus.running,
            total_rows=len(rows),
            processed_rows=0,
            success_rows=0,
            duplicate_rows=0,
            failed_rows=0,
            started_at=_utc_now(),
        )
        await session.commit()

    async with async_session_maker() as session:
        job = await session.get(LeadImportJob, job_id)
        if not job:
            return

        await _update_job_status(
            session,
            job,
            status=LeadImportJobStatus.running,
            total_rows=len(rows),
        )
        await session.flush()

        for row_number, raw_row in rows:
            try:
                normalized, payload, external_id = _normalize_row(tenant_id, raw_row, headers)

                if external_id in dedupe_in_file:
                    duplicate_rows += 1
                    await _update_job_status(
                        session,
                        job,
                        status=LeadImportJobStatus.running,
                        processed_rows=success_rows + duplicate_rows + failed_rows,
                        duplicate_rows=duplicate_rows,
                        error_report=errors,
                    )
                    await session.commit()
                    continue

                dedupe_in_file.add(external_id)

                existing = await crud.get_lead_by_external_id(
                    session,
                    tenant_id=tenant_id,
                    source=IMPORT_SOURCE,
                    external_id=external_id,
                )
                if existing and existing.status not in {"failed", "needs_routing"}:
                    duplicate_rows += 1
                    await _update_job_status(
                        session,
                        job,
                        status=LeadImportJobStatus.running,
                        processed_rows=success_rows + duplicate_rows + failed_rows,
                        duplicate_rows=duplicate_rows,
                        error_report=errors,
                    )
                    await session.commit()
                    continue

                # Same doctrine as ``POST /leads/{id}/process`` and bulk queues: re-import must not
                # run conversion while intake / routing blocks apply to the stored row.
                if existing:
                    block = await leads_service.manual_process_block_code(session, tenant_id, existing)
                    if block:
                        failed_rows += 1
                        errors.append({"row": row_number, "error": block})
                        await _send_lead_failed_webhook(tenant_id, job_id, row_number, block)
                        continue

                target_lead_id = str(existing.id) if existing else None
                result = await leads_service.process_normalized_lead(
                    session,
                    tenant_id=tenant_id,
                    payload=payload,
                    normalized=normalized,
                    source=IMPORT_SOURCE,
                    external_id=external_id,
                    target_lead_id=target_lead_id,
                )

                if not result.is_new:
                    duplicate_rows += 1
                elif result.status == "duplicated":
                    duplicate_rows += 1
                elif result.status == "failed":
                    failed_rows += 1
                else:
                    success_rows += 1

                if result.is_new:
                    await _send_lead_received_webhook(tenant_id, job_id, row_number, result)

            except LeadProcessingError as exc:
                failed_rows += 1
                errors.append({"row": row_number, "error": str(exc)})
                await session.rollback()
                await _send_lead_failed_webhook(tenant_id, job_id, row_number, str(exc))
            except Exception as exc:
                failed_rows += 1
                errors.append({"row": row_number, "error": str(exc)})
                await session.rollback()
                await _send_lead_failed_webhook(tenant_id, job_id, row_number, str(exc))
            else:
                await session.commit()
            finally:
                await session.refresh(job)
                await _update_job_status(
                    session,
                    job,
                    status=LeadImportJobStatus.running,
                    processed_rows=success_rows + duplicate_rows + failed_rows,
                    success_rows=success_rows,
                    duplicate_rows=duplicate_rows,
                    failed_rows=failed_rows,
                    error_report=errors,
                )
                await session.commit()

        final_status = LeadImportJobStatus.completed
        if failed_rows and success_rows == 0 and duplicate_rows == 0:
            final_status = LeadImportJobStatus.failed

        await _update_job_status(
            session,
            job,
            status=final_status,
            finished_at=_utc_now(),
            error_report=errors,
        )

        notification_payload = {
            "job_id": job_id,
            "filename": filename,
            "status": final_status,
            "total_rows": job.total_rows,
            "processed_rows": job.processed_rows,
            "success_rows": job.success_rows,
            "duplicate_rows": job.duplicate_rows,
            "failed_rows": job.failed_rows,
        }
        await _notify_initiator(
            session,
            tenant_id=tenant_id,
            user_id=created_by,
            payload=notification_payload,
            event_type=(
                "lead.import.completed"
                if final_status == LeadImportJobStatus.completed
                else "lead.import.failed"
            ),
        )
        await session.commit()


def enqueue_import_job(
    job_id: str,
    *,
    tenant_id: str,
    created_by: str,
    filename: str,
    content: bytes,
) -> asyncio.Task[None]:
    async def _runner() -> None:
        try:
            await run_import_job(
                job_id,
                tenant_id=tenant_id,
                created_by=created_by,
                filename=filename,
                content=content,
            )
        finally:
            _IMPORT_TASKS.pop(job_id, None)

    task = asyncio.create_task(_runner())
    _IMPORT_TASKS[job_id] = task
    return task
