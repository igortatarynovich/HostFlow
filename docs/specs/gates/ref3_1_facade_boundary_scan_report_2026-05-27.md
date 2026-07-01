# REF-3.1 Facade Boundary Scan Report — 2026-05-27

## 1) Direct DocumentApplicabilityResolver Calls
backend/app/services/hr_expected_documents_resolver.py:13:    DocumentApplicabilityResolver,
backend/app/services/hr_expected_documents_resolver.py:74:    m4 = await DocumentApplicabilityResolver.resolve_expected_documents(
backend/app/api/v1/candidates/service.py:77:    DocumentApplicabilityResolver,
backend/app/services/document_applicability_resolver.py:39:class DocumentApplicabilityResolver:
backend/app/services/hr_documents_queue.py:20:    DocumentApplicabilityResolver,
backend/app/services/hr_documents_queue.py:237:        expected_docs = await DocumentApplicabilityResolver.resolve_expected_documents(
backend/app/services/workforce_eligibility_resolver.py:16:    DocumentApplicabilityResolver,
backend/app/services/workforce_eligibility_resolver.py:233:        expected = await DocumentApplicabilityResolver.resolve_expected_documents(
backend/app/services/hr_verification_plan.py:21:    DocumentApplicabilityResolver,
backend/app/services/hr_verification_plan.py:264:    expected = await DocumentApplicabilityResolver.resolve_expected_documents(
backend/app/services/reference_service_facade.py:14:    DocumentApplicabilityResolver,
backend/app/services/reference_service_facade.py:133:        rows = await DocumentApplicabilityResolver.resolve_expected_documents(

## 2) Direct DocumentTypeRuntimeResolver Calls
backend/app/services/hr_review_document_resolution.py:11:from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver
backend/app/services/hr_review_document_resolution.py:103:        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(db, doc)
backend/app/services/handoff_snapshot.py:22:from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver
backend/app/services/handoff_snapshot.py:130:        runtime_ref = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
backend/app/services/document_applicability_resolver.py:21:from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver
backend/app/services/document_applicability_resolver.py:210:                rr = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
backend/app/services/document_type_runtime_resolver.py:35:class DocumentTypeRuntimeResolver:
backend/app/services/hr_documents_queue.py:23:from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver
backend/app/services/hr_documents_queue.py:384:            runtime_ref = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
backend/app/services/status_transitions.py:17:    DocumentTypeRuntimeResolver,
backend/app/services/status_transitions.py:177:            resolved = await DocumentTypeRuntimeResolver.resolve_for_document(db, document)
backend/app/services/workforce_eligibility_resolver.py:18:from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver
backend/app/services/workforce_eligibility_resolver.py:265:            rr = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)

## 3) Reference Model/Table Reads (Ref*/Pack/Overrides)
backend/app/services/hr_expected_documents_resolver.py:10:from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeI18n, RefDocumentTypeVersion
backend/app/services/hr_expected_documents_resolver.py:35:def _group_for_ref(dt: RefDocumentType) -> str:
backend/app/services/hr_expected_documents_resolver.py:124:            select(RefDocumentType).where(
backend/app/services/hr_expected_documents_resolver.py:125:                RefDocumentType.status.in_(("active", "published", "draft"))
backend/app/services/hr_expected_documents_resolver.py:136:            select(RefDocumentTypeVersion).where(
backend/app/services/hr_expected_documents_resolver.py:137:                RefDocumentTypeVersion.document_type_id.in_(list(dt_by_id.keys())),
backend/app/services/hr_expected_documents_resolver.py:138:                or_(RefDocumentTypeVersion.valid_to.is_(None), RefDocumentTypeVersion.valid_to >= today),
backend/app/services/hr_expected_documents_resolver.py:142:    ver_by_doc: dict[str, RefDocumentTypeVersion] = {}
backend/app/services/hr_expected_documents_resolver.py:151:            select(RefDocumentTypeI18n).where(RefDocumentTypeI18n.document_type_id.in_(list(dt_by_id.keys())))
backend/app/services/document_applicability_resolver.py:12:    RefDocumentType,
backend/app/services/document_applicability_resolver.py:13:    RefDocumentTypeVersion,
backend/app/services/document_applicability_resolver.py:14:    RefPack,
backend/app/services/document_applicability_resolver.py:15:    RefPackItem,
backend/app/services/document_applicability_resolver.py:16:    RefPackRule,
backend/app/services/document_applicability_resolver.py:17:    TenantDocumentPackEnablement,
backend/app/services/document_applicability_resolver.py:18:    TenantDocumentTypeOverride,
backend/app/services/document_applicability_resolver.py:90:            select(TenantDocumentPackEnablement, RefPack)
backend/app/services/document_applicability_resolver.py:91:            .join(RefPack, RefPack.id == TenantDocumentPackEnablement.pack_id)
backend/app/services/document_applicability_resolver.py:92:            .where(TenantDocumentPackEnablement.tenant_id == tid)
backend/app/services/document_applicability_resolver.py:93:            .where(TenantDocumentPackEnablement.enabled.is_(True))
backend/app/services/document_applicability_resolver.py:94:            .where(RefPack.status == "active")
backend/app/services/document_applicability_resolver.py:105:                select(RefPackItem, RefDocumentTypeVersion, RefDocumentType)
backend/app/services/document_applicability_resolver.py:106:                .join(RefDocumentTypeVersion, RefDocumentTypeVersion.id == RefPackItem.document_type_version_id)
backend/app/services/document_applicability_resolver.py:107:                .join(RefDocumentType, RefDocumentType.id == RefDocumentTypeVersion.document_type_id)
backend/app/services/document_applicability_resolver.py:108:                .where(RefPackItem.pack_id.in_(pack_ids))
backend/app/services/document_applicability_resolver.py:113:            await db.execute(select(RefPackRule).where(RefPackRule.pack_id.in_(pack_ids)).order_by(RefPackRule.priority.asc()))
backend/app/services/document_applicability_resolver.py:115:        rules_by_pack: dict[str, list[RefPackRule]] = {}
backend/app/services/document_applicability_resolver.py:120:            await db.execute(select(TenantDocumentTypeOverride).where(TenantDocumentTypeOverride.tenant_id == tid))
backend/app/services/reference_service_facade.py:11:from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion
backend/app/services/reference_service_facade.py:160:            await db.execute(select(RefDocumentType).where(RefDocumentType.code == str(code).strip().lower()))
backend/app/services/reference_service_facade.py:172:                select(RefDocumentTypeVersion)
backend/app/services/reference_service_facade.py:173:                .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
backend/app/services/reference_service_facade.py:174:                .order_by(RefDocumentTypeVersion.valid_from.desc())
backend/app/services/document_type_runtime_resolver.py:11:from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion
backend/app/services/document_type_runtime_resolver.py:111:            select(RefDocumentTypeVersion, RefDocumentType)
backend/app/services/document_type_runtime_resolver.py:112:            .join(RefDocumentType, RefDocumentType.id == RefDocumentTypeVersion.document_type_id)
backend/app/services/document_type_runtime_resolver.py:113:            .where(RefDocumentTypeVersion.id == version_id)
backend/app/services/document_type_runtime_resolver.py:129:        doc_type = await db.get(RefDocumentType, document_type_id)
backend/app/services/document_type_runtime_resolver.py:134:            select(RefDocumentTypeVersion)
backend/app/services/document_type_runtime_resolver.py:135:            .where(RefDocumentTypeVersion.document_type_id == document_type_id)
backend/app/services/document_type_runtime_resolver.py:136:            .where(or_(RefDocumentTypeVersion.valid_to.is_(None), RefDocumentTypeVersion.valid_to >= RefDocumentTypeVersion.valid_from))
backend/app/services/document_type_runtime_resolver.py:137:            .order_by(RefDocumentTypeVersion.valid_from.desc(), RefDocumentTypeVersion.created_at.desc())
backend/app/services/document_type_runtime_resolver.py:155:        stmt = select(RefDocumentType).where(and_(RefDocumentType.code == canonical_code, RefDocumentType.status.in_(["active", "deprecated", "draft"])))
backend/app/services/document_type_runtime_resolver.py:161:            select(RefDocumentTypeVersion)
backend/app/services/document_type_runtime_resolver.py:162:            .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
backend/app/services/document_type_runtime_resolver.py:163:            .order_by(RefDocumentTypeVersion.valid_from.desc(), RefDocumentTypeVersion.created_at.desc())
backend/app/services/document_type_runtime_resolver.py:172:        doc_type: RefDocumentType,
backend/app/services/document_type_runtime_resolver.py:173:        ver: Optional[RefDocumentTypeVersion],

## 4) Legacy Mapping/Fallback Markers (reference/doc paths)
backend/app/services/candidate_notifications.py:10:from backend.app.services.document_catalog import get_doc_type_defaults
backend/app/services/candidate_notifications.py:14:def get_document_display_name(doc_type: str) -> str:
backend/app/services/candidate_notifications.py:15:    defaults = get_doc_type_defaults(doc_type)
backend/app/services/candidate_notifications.py:21:        or next(iter(title.values()), doc_type)
backend/app/services/candidate_notifications.py:30:    doc_type: str,
backend/app/services/candidate_notifications.py:42:    document_name = get_document_display_name(doc_type)
backend/app/services/hr_documents_hub.py:21:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/hr_documents_hub.py:23:    HR_HIGH_RISK_DOC_TYPES,
backend/app/services/hr_documents_hub.py:47:def _risk_for_type(doc_type: str) -> str:
backend/app/services/hr_documents_hub.py:48:    return "high" if normalize_doc_type(doc_type) in HR_HIGH_RISK_DOC_TYPES else "normal"
backend/app/services/hr_documents_hub.py:148:    wanted_doc_type: str | None = None
backend/app/services/hr_documents_hub.py:150:        wanted_doc_type = normalize_doc_type(document_type)
backend/app/services/hr_documents_hub.py:211:        if wanted_doc_type and normalize_doc_type(str(doc.doc_type or "")) != wanted_doc_type:
backend/app/services/hr_documents_hub.py:219:        canon = normalize_doc_type(str(doc.doc_type or ""))
backend/app/services/workforce_hr_review.py:102:    Hybrid mode (PR15): ``verification_plan`` only. Legacy: checklist + verified-fields + doc loop.
backend/app/services/workforce_hr_review.py:757:    legacy_rows = _documents_for_approval(bundle, journey)
backend/app/services/workforce_hr_review.py:758:    legacy_rows = await merge_candidate_documents_into_approval_rows(
backend/app/services/workforce_hr_review.py:759:        db, tenant_id, str(emp.candidate_id or ""), legacy_rows
backend/app/services/workforce_hr_review.py:767:        legacy_approval_rows=legacy_rows,
backend/app/services/workforce_hr_review.py:1073:    legacy_rows = _documents_for_approval({}, {})
backend/app/services/workforce_hr_review.py:1074:    legacy_rows = await merge_candidate_documents_into_approval_rows(
backend/app/services/workforce_hr_review.py:1075:        db, tenant_id, str(review.candidate_id or ""), legacy_rows
backend/app/services/workforce_hr_review.py:1083:        legacy_approval_rows=legacy_rows,
backend/app/services/reminders.py:19:from backend.app.services.document_catalog import get_doc_type_defaults
backend/app/services/reminders.py:67:    defaults = get_doc_type_defaults(getattr(document, "doc_type", None))
backend/app/services/reminders.py:246:        or getattr(document, "doc_type", None)
backend/app/services/reminders.py:378:    doc_type = getattr(document, "type", None) or getattr(document, "doc_type", "document")
backend/app/services/reminders.py:395:            f"Шаг '{step_title}' по документу '{doc_type}' "
backend/app/services/reminders.py:522:        doc_type = (
backend/app/services/reminders.py:525:            or getattr(doc, "doc_type", None)
backend/app/services/reminders.py:536:            "document_name": doc_type,
backend/app/services/reminders.py:548:            subject = f"📄 Напоминание по документу '{doc_type}'"
backend/app/services/reminders.py:553:                subject = f"📄 Документ '{doc_type}' истекает через {days} {_plural_days(days)}"
backend/app/services/reminders.py:555:                subject = f"📄 Документ '{doc_type}' истекает через {remaining} ч"
backend/app/services/reminders.py:557:            subject = f"📄 Документ '{doc_type}' истекает сегодня"
backend/app/services/reminders.py:561:                subject = f"⚠️ Документ '{doc_type}' просрочен на {days} {_plural_days(days)}"
backend/app/services/reminders.py:563:                subject = f"⚠️ Документ '{doc_type}' просрочен на {offset_hours} ч"
backend/app/services/reminders.py:565:        message_line = _format_expiry_message(doc_type, expires_for_message, offset_hours or 0)
backend/app/services/reminders.py:570:            f"Документ: {doc_type}",
backend/app/services/reminders.py:727:            doc_type = getattr(doc, "doc_type", None) or getattr(doc, "type", "document")
backend/app/services/reminders.py:728:            subject = f"⚙️ Шаг '{step_title}' по документу '{doc_type}' до {due_date}"
backend/app/services/reminders.py:731:                f"Документ: {doc_type}\n"
backend/app/services/recruitment_application_service.py:6:Legacy ``active`` is normalized to ``applied`` on read and on assign through the helper.
backend/app/services/recruiter_assignment.py:49:        # vacancy produced a recruiter, fell into tenant-wide fallback
backend/app/services/recruiter_assignment.py:50:        # (``MetaLeadSettings.fallback_recruiter_id`` / hint).
backend/app/services/recruiter_assignment.py:51:        "lead_fallback",
backend/app/services/recruiter_assignment.py:57:        # Manual lead re-route — fallback branch (tenant hint).
backend/app/services/recruiter_assignment.py:58:        "lead_reroute_fallback",
backend/app/services/recruiter_assignment.py:379:    vacancy-scoped resolution (no company-supervisor / tenant-admin fallback).
backend/app/services/recruiter_assignment.py:388:       ``MetaLeadSettings.fallback_recruiter_id``).
backend/app/services/recruiter_assignment.py:393:    through to the tenant-wide fallback.
backend/app/services/recruiter_assignment.py:504:        # fix a drifted ``Candidate.manager`` (legacy column; no FK) so the
backend/app/services/recruiter_assignment.py:510:        legacy_manager = _normalise_owner_id(getattr(candidate, "manager", None))
backend/app/services/recruiter_assignment.py:511:        if legacy_manager != new_value:
backend/app/services/message_hub.py:4:call contracts untouched. It centralizes variable rendering and fallback logic
backend/app/services/message_hub.py:45:    fallback_subject: str,
backend/app/services/message_hub.py:46:    fallback_body: str,
backend/app/services/message_hub.py:50:    """Resolve template (if active) and render placeholders, else fallback."""
backend/app/services/message_hub.py:51:    subject = str(fallback_subject or "")
backend/app/services/message_hub.py:52:    body = str(fallback_body or "")
backend/app/services/scanner_presets.py:473:    # Default fallback
backend/app/services/scanner_presets.py:512:def get_preset_for_doc_type(doc_type: str) -> ScannerPreset:
backend/app/services/scanner_presets.py:514:    Map document type (doc_type) to scanner preset.
backend/app/services/scanner_presets.py:517:    # Normalize doc_type
backend/app/services/scanner_presets.py:518:    doc_type_lower = doc_type.lower().strip()
backend/app/services/scanner_presets.py:599:        # Fallback
backend/app/services/scanner_presets.py:606:    if doc_type_lower in mapping:
backend/app/services/scanner_presets.py:607:        preset_code = mapping[doc_type_lower]
backend/app/services/scanner_presets.py:615:        if key in doc_type_lower:
backend/app/services/scanner_presets.py:620:    # Try reverse partial match (doc_type contains key)
backend/app/services/scanner_presets.py:622:        if doc_type_lower in key:
backend/app/services/scanner_presets.py:627:    # Default fallback - ensure we always return a valid preset
backend/app/services/scanner_presets.py:635:    raise ValueError(f"No scanner preset available for document type: {doc_type}")
backend/app/services/hr_document_verification.py:105:            "doc_type": document.doc_type if document else None,
backend/app/services/hiring_pipeline_gates.py:5:Missing keys fall back to product defaults (matches legacy hardcoded behavior).
backend/app/services/hiring_pipeline_gates.py:16:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/hiring_pipeline_gates.py:17:from backend.app.services.pipeline_override_policy import NON_OVERRIDABLE_DOC_TYPES
backend/app/services/hiring_pipeline_gates.py:72:        c = normalize_doc_type(str(item))
backend/app/services/hiring_pipeline_gates.py:89:    non_overridable_doc_types_extra: FrozenSet[str]
backend/app/services/hiring_pipeline_gates.py:91:    def effective_non_overridable_doc_types(self) -> FrozenSet[str]:
backend/app/services/hiring_pipeline_gates.py:92:        return NON_OVERRIDABLE_DOC_TYPES | self.non_overridable_doc_types_extra
backend/app/services/hiring_pipeline_gates.py:102:        non_overridable_doc_types_extra=frozenset(),
backend/app/services/hiring_pipeline_gates.py:136:        non_overridable_doc_types_extra=_as_extra_non_overridable(raw.get("non_overridable_doc_types_extra")),
backend/app/services/hiring_pipeline_gates.py:207:    eff = sorted(gates.effective_non_overridable_doc_types())
backend/app/services/hiring_pipeline_gates.py:215:        "non_overridable_doc_types_extra": sorted(gates.non_overridable_doc_types_extra),
backend/app/services/hiring_pipeline_gates.py:216:        "effective_non_overridable_doc_types": eff,
backend/app/services/assignee_load_taxonomy.py:1:"""Таксономия событий для **взвешенной дневной нагрузки** (fallback выбора assignee).
backend/app/services/assignee_load_taxonomy.py:35:#    ``communication_planner_events``) with a fallback to ``Activity.type``
backend/app/services/assignee_load_taxonomy.py:154:# (Phase 2.1 absorbed legacy ``CommunicationPlannerEvent.status``;
backend/app/services/assignee_load_taxonomy.py:163:# (legacy ``ReminderStatus`` constants are still importable; the values
backend/app/services/document_merge/templates_repo.py:85:        doc_type=str(payload.get("doc_type") or "additional_document").strip(),
backend/app/services/document_merge/templates_repo.py:121:    if "doc_type" in payload and payload["doc_type"] is not None:
backend/app/services/document_merge/templates_repo.py:122:        row.doc_type = str(payload["doc_type"]).strip()
backend/app/services/document_merge/generate.py:13:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/document_merge/generate.py:148:    doc_type = normalize_doc_type(template.doc_type or "additional_document")
backend/app/services/document_merge/generate.py:185:            "doc_type": doc_type,
backend/app/services/automation_rules.py:139:    - Legacy: scalar value → equality (``source`` compared case-insensitively).
backend/app/services/tenant_visibility.py:42:    fallback_id = tenant_id or str(info.get("tenant_id") or "")
backend/app/services/tenant_visibility.py:43:    if not fallback_id:
backend/app/services/tenant_visibility.py:44:        fallback_id = "unknown"
backend/app/services/tenant_visibility.py:45:    visibility = TenantVisibility(tenant_id=fallback_id)
backend/app/services/hr_operational_alerts.py:57:    """Stable 36-char id for notification dedupe (entity_type + entity_id fallback)."""
backend/app/services/hr_handoff_profile_context.py:12:_DOC_TYPE_ALIASES: dict[str, str] = {
backend/app/services/hr_handoff_profile_context.py:51:def _norm_doc_type(raw: str) -> str:
backend/app/services/hr_handoff_profile_context.py:70:        bucket = _DOC_TYPE_ALIASES.get(_norm_doc_type(str(doc.get("type") or "")))
backend/app/services/hr_expected_documents_resolver.py:71:    """Resolve expected document rows from system dictionaries + policies, with JSON fallback."""
backend/app/services/candidate_lifecycle.py:19:   either via the canonical ``related_entity_*`` pair *or* via the legacy
backend/app/services/candidate_lifecycle.py:77:# (planned / in_progress) plus the legacy transient values that the
backend/app/services/candidate_lifecycle.py:231:    ``old_stage`` / ``new_stage`` (bulk stage updates, legacy callers).
backend/app/services/candidate_lifecycle.py:351:      * or via the legacy ``metadata.planner.linked_candidate_id`` marker
backend/app/services/candidate_lifecycle.py:371:                # Legacy ``linked_candidate_id`` preserved by backfill in
backend/app/services/candidate_lifecycle.py:434:    (``UserNotification``, or the legacy ``Reminder`` / ``CommunicationPlannerEvent``
backend/app/services/document_reference_sync.py:49:LEGACY_CODE_MAP: dict[str, str] = {
backend/app/services/document_reference_sync.py:90:def normalize_legacy_doc_type(value: Optional[str]) -> str:
backend/app/services/document_reference_sync.py:94:    return LEGACY_CODE_MAP.get(key, "other")
backend/app/services/document_reference_sync.py:252:        text("SELECT id, doc_type FROM documents WHERE document_type_id IS NULL OR document_type_version_id IS NULL")
backend/app/services/document_reference_sync.py:255:        code = normalize_legacy_doc_type(row.get("doc_type"))
backend/app/services/document_reference_sync.py:268:            SELECT dp.id AS policy_id, dt.code AS legacy_code
backend/app/services/document_reference_sync.py:277:        code = normalize_legacy_doc_type(row.get("legacy_code"))
backend/app/services/recruitment_lead_assignee.py:73:    """Active tenant recruiter with optional company access + availability (for lead fallback)."""
backend/app/services/additional_services.py:34:    get_doc_type_defaults,
backend/app/services/additional_services.py:35:    normalize_doc_type,
backend/app/services/additional_services.py:52:_LEGACY_SERVICE_ORDER_STATUS: Dict[str, str] = {
backend/app/services/additional_services.py:63:    canon = _LEGACY_SERVICE_ORDER_STATUS.get(raw, raw)
backend/app/services/additional_services.py:554:            result_doc_type = item_payload.get("result_document_type")
backend/app/services/additional_services.py:555:            if result_doc_type is None:
backend/app/services/additional_services.py:556:                result_doc_type = service.result_document_type
backend/app/services/additional_services.py:573:                result_document_type=result_doc_type,
backend/app/services/additional_services.py:625:        result_doc_type = item_payload.get("result_document_type")
backend/app/services/additional_services.py:626:        if result_doc_type is None:
backend/app/services/additional_services.py:627:            result_doc_type = service.result_document_type
backend/app/services/additional_services.py:643:            result_document_type=result_doc_type,
backend/app/services/additional_services.py:803:                doc_type=item.result_document_type,
backend/app/services/additional_services.py:921:        doc_codes = [normalize_doc_type(code) for code in required if code]
backend/app/services/additional_services.py:924:        stmt = select(Document.doc_type, Document.status).where(
backend/app/services/additional_services.py:927:            Document.doc_type.in_(doc_codes),
backend/app/services/additional_services.py:932:        for doc_type_value, status_value in rows.all():
backend/app/services/additional_services.py:934:                status_by_code[doc_type_value] = status_value
backend/app/services/additional_services.py:937:                    status_by_code[doc_type_value] = normalize_status(status_value)
backend/app/services/additional_services.py:939:                    status_by_code[doc_type_value] = DocumentStatus.missing
backend/app/services/additional_services.py:952:        doc_type: str,
backend/app/services/additional_services.py:956:        canonical_type = normalize_doc_type(doc_type)
backend/app/services/additional_services.py:957:        defaults = get_doc_type_defaults(canonical_type)
backend/app/services/additional_services.py:962:            Document.doc_type == canonical_type,
backend/app/services/additional_services.py:972:        meta_payload.setdefault("doc_type", canonical_type)
backend/app/services/additional_services.py:973:        original_type = payload.get("document_type") or payload.get("doc_type")
backend/app/services/additional_services.py:975:            meta_payload.setdefault("submitted_doc_type", original_type)
backend/app/services/additional_services.py:1051:                doc_type=canonical_type,
backend/app/services/workforce_operational_profile.py:675:    # M5.2: legacy summary fields are compatibility projections from decision contract.
backend/app/services/rodo.py:110:    fallback_body = f"""Dear {first_name},
backend/app/services/rodo.py:145:        fallback_subject="RODO / GDPR — Personal data processing information | HostFlow",
backend/app/services/rodo.py:146:        fallback_body=fallback_body,
backend/app/services/hr_review_document_resolution.py:13:# document_key (HR verification card) -> candidate Document.doc_type aliases
backend/app/services/hr_review_document_resolution.py:54:def _norm_doc_type(raw: str) -> str:
backend/app/services/hr_review_document_resolution.py:68:    st = _norm_doc_type(str(getattr(doc, "status", "") or ""))
backend/app/services/hr_review_document_resolution.py:104:        key = _norm_doc_type(str(resolved.canonical_code or ""))
backend/app/services/hr_review_document_resolution.py:118:        candidates.extend(by_type.get(_norm_doc_type(alias), []))
backend/app/services/hr_review_document_resolution.py:149:        st = _norm_doc_type(str(getattr(doc, "status", "") or ""))
backend/app/services/hr_review_document_resolution.py:158:        r["context_type"] = r.get("context_type") or str(doc.doc_type or "")
backend/app/services/team_assignee_auto.py:1:"""Manager queue: unavailable assignee → fallback peer by queue + optional **weighted day load**.
backend/app/services/team_assignee_auto.py:3:When ``respectAvailability`` is on, we can pick the fallback using the same calendar
backend/app/services/team_assignee_auto.py:60:    "resolve_assignee_id_with_queue_fallback",
backend/app/services/team_assignee_auto.py:90:    ``load_context`` for **weighted** manager-queue fallback. Returns ``None`` on
backend/app/services/team_assignee_auto.py:361:async def resolve_assignee_id_with_queue_fallback(
backend/app/services/team_assignee_auto.py:372:    If ``load_context`` contains an ``anchor`` datetime, fallback assignee is chosen by
backend/app/services/team_assignee_auto.py:469:            "load_note": "fallback_queue_after_weighted_error",
backend/app/services/candidate_document_checklist.py:15:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/candidate_document_checklist.py:42:    n = normalize_doc_type(raw)
backend/app/services/candidate_document_checklist.py:99:        raw = item.get("document_type_id") or item.get("doc_type")
backend/app/services/candidate_document_checklist.py:104:        if normalize_doc_type(norm_underscored) != "additional_document":
backend/app/services/candidate_document_checklist.py:137:            n = normalize_doc_type(h)
backend/app/services/candidate_document_checklist.py:140:        raw = item.get("document_type_id") or item.get("doc_type")
backend/app/services/candidate_document_checklist.py:144:            n2 = normalize_doc_type(norm_underscored)
backend/app/services/next_action.py:24:fallback ("Wait — nothing to do right now") so the empty state is never a
backend/app/services/next_action.py:498:# the only thing this branch ladder needs to handle. The legacy
backend/app/services/next_action.py:530:    rewritten to expect canonical `on_hold`; the legacy `paused` alias
backend/app/services/next_action.py:1060:   10.  fallback                                      → IDLE (no_signal)
backend/app/services/working_hours_window.py:152:    exact same fallback policy (otherwise a malformed tz string could
backend/app/services/working_hours_window.py:183:        as a safe fallback.
backend/app/services/working_hours_window.py:209:        # validation. Treat as "no schedule" — safe fallback.
backend/app/services/handoff_snapshot.py:133:                "type": str(getattr(d, "doc_type", "") or ""),
backend/app/services/handoff_snapshot.py:141:                    "fallback_used": runtime_ref.fallback_used,
backend/app/services/ensure_activity_layer_v1.py:6:    A) Pre-Phase-1.3 (legacy):
backend/app/services/ensure_activity_layer_v1.py:13:       so when running on a legacy DB the app would 500-fail every
backend/app/services/ensure_activity_layer_v1.py:97:def _is_legacy(states: dict[str, str]) -> bool:
backend/app/services/ensure_activity_layer_v1.py:165:    if _is_legacy(states):
backend/app/services/ensure_activity_layer_v1.py:167:            "[startup:activity_layer_v1] legacy schema detected (reminders/user_notifications "
backend/app/services/ensure_activity_layer_v1.py:180:        "Neither pre-Phase-1.3 (legacy) nor canonical. This typically means a "
backend/app/services/lead_lifecycle.py:47:# (planned / in_progress / done / cancelled / overdue) plus the legacy
backend/app/services/lead_lifecycle.py:404:    (which handles deadline-only rows). The legacy
backend/app/services/document_applicability_resolver.py:40:    """Resolves expected documents from enabled packs with safe fallback behavior."""
backend/app/services/document_applicability_resolver.py:125:        for item, ver, doc_type in items:
backend/app/services/document_applicability_resolver.py:133:            criticality = str(doc_type.criticality or "informational")
backend/app/services/document_applicability_resolver.py:149:            ov = ov_by_doc_id.get(str(doc_type.id))
backend/app/services/document_applicability_resolver.py:165:            code = str(doc_type.code)
backend/app/services/document_applicability_resolver.py:169:                "label": str(doc_type.public_name or code),
backend/app/services/document_applicability_resolver.py:170:                "group": str(doc_type.category_code or "other"),
backend/app/services/document_applicability_resolver.py:180:                "document_type_id": str(doc_type.id),
backend/app/services/hr_acceptance_orchestrator.py:36:    """After handoff marked accepted: legacy creates workforce immediately; delayed only opens HR review."""
backend/app/services/hr_documents_queue.py:22:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/hr_documents_queue.py:25:HR_HIGH_RISK_DOC_TYPES: frozenset[str] = frozenset(
backend/app/services/hr_documents_queue.py:80:def _snapshot_doc_status(payload: dict[str, Any] | None, doc_type: str) -> str | None:
backend/app/services/hr_documents_queue.py:83:    canon = normalize_doc_type(doc_type)
backend/app/services/hr_documents_queue.py:85:        t = normalize_doc_type(str(d.get("document_code") or ""))
backend/app/services/hr_documents_queue.py:89:        t = normalize_doc_type(str((d.get("canonical") or {}).get("code") or d.get("type") or ""))
backend/app/services/hr_documents_queue.py:102:def _live_best_status_for_type(docs: Sequence[Any], doc_type: str) -> str:
backend/app/services/hr_documents_queue.py:103:    canon = normalize_doc_type(doc_type)
backend/app/services/hr_documents_queue.py:108:        if normalize_doc_type(str(getattr(d, "doc_type", "") or "")) in acceptable
backend/app/services/hr_documents_queue.py:119:def _risk_for_type(doc_type: str) -> str:
backend/app/services/hr_documents_queue.py:120:    return "high" if normalize_doc_type(doc_type) in HR_HIGH_RISK_DOC_TYPES else "normal"
backend/app/services/hr_documents_queue.py:260:            normalize_doc_type(str(item.get("document_code") or ""))
backend/app/services/hr_documents_queue.py:265:            # Safe compatibility fallback when packs are not enabled yet for a tenant.
backend/app/services/hr_documents_queue.py:267:                normalize_doc_type(str(getattr(d, "doc_type", "") or ""))
backend/app/services/hr_documents_queue.py:269:                if str(getattr(d, "doc_type", "") or "").strip()
backend/app/services/hr_documents_queue.py:287:            canon = normalize_doc_type(mtype)
backend/app/services/hr_documents_queue.py:288:            if document_type and normalize_doc_type(document_type) != canon:
backend/app/services/hr_documents_queue.py:385:            canon = normalize_doc_type(str(runtime_ref.canonical_code or getattr(d, "doc_type", "") or ""))
backend/app/services/hr_documents_queue.py:386:            if document_type and normalize_doc_type(document_type) != canon:
backend/app/services/own_company_doc_scope.py:60:    """Filter document_policies rows for active workspace + legacy NULL."""
backend/app/services/legal_documents.py:8:from backend.app.legal.billing_terms_templates_v1 import ORDERED_LEGAL_DOC_TYPES
backend/app/services/legal_documents.py:15:    doc_type: str,
backend/app/services/legal_documents.py:21:        .where(LegalDocument.type == doc_type)
backend/app/services/legal_documents.py:36:    for doc_type in ORDERED_LEGAL_DOC_TYPES:
backend/app/services/legal_documents.py:37:        out[doc_type] = await get_active_legal_document(db, tenant_id, doc_type)
backend/app/services/status_transitions.py:161:        doc_type = (await db.execute(stmt)).scalar_one_or_none()
backend/app/services/status_transitions.py:162:        if doc_type and hasattr(doc_type, "status_model") and doc_type.status_model:
backend/app/services/status_transitions.py:163:            return doc_type.status_model
backend/app/services/status_transitions.py:164:        # Fallback: определяем по типу документа
backend/app/services/status_transitions.py:165:        return cls._infer_status_model_from_doc_type(doc_type.code if doc_type else None)
backend/app/services/status_transitions.py:174:        fallback to legacy doc_type inference.
backend/app/services/status_transitions.py:185:        return cls._infer_status_model_from_doc_type(document.doc_type)
backend/app/services/status_transitions.py:188:    def _infer_status_model_from_doc_type(cls, doc_type_code: Optional[str]) -> DocumentStatusModel:
backend/app/services/status_transitions.py:190:        if not doc_type_code:
backend/app/services/status_transitions.py:193:        doc_type_upper = doc_type_code.upper()
backend/app/services/status_transitions.py:194:        if doc_type_upper in ("WORK_PERMIT_A", "Zezwolenie typu A"):
backend/app/services/status_transitions.py:196:        elif doc_type_upper in ("EMPLOYER_STATEMENT_OSWIADCZENIE", "Oświadczenie"):
backend/app/services/status_transitions.py:198:        elif doc_type_upper in ("RESIDENCE_CARD", "Karta pobytu"):
backend/app/services/status_transitions.py:252:            status_model = cls._infer_status_model_from_doc_type(document.doc_type)
backend/app/services/status_transitions.py:318:            status_model = cls._infer_status_model_from_doc_type(document.doc_type)
backend/app/services/status_transitions.py:347:        status_model = cls._infer_status_model_from_doc_type(document.doc_type)
backend/app/services/lead_distribution.py:276:    meta: Dict[str, Any] = {"explicit_route": False, "preference_fallback": False}
backend/app/services/lead_distribution.py:286:        meta["preference_fallback"] = True
backend/app/services/lead_distribution.py:443:    elif lang_meta.get("preference_fallback") and language_route_user_ids(cfg, preview_lang):
backend/app/services/pipeline_override_policy.py:3:# Doc type codes (normalized via `normalize_doc_type`) that must never receive a pipeline waiver.
backend/app/services/pipeline_override_policy.py:6:NON_OVERRIDABLE_DOC_TYPES: frozenset[str] = frozenset(
backend/app/services/notification_templates.py:308:    Resolve template by offset. Fallbacks map any unknown negative offsets
backend/app/services/plan_feature_gates.py:262:    """Map license.plan (incl. legacy segment names) to starter | team | pro for §2.16 numeric caps."""
backend/app/services/workforce_eligibility_resolver.py:39:    _LEGACY_OPS = (
backend/app/services/workforce_eligibility_resolver.py:198:            "legacy_resolution_action": (
backend/app/services/workforce_eligibility_resolver.py:401:        for legacy, canonical in cls._OP_ALIASES.items():
backend/app/services/workforce_eligibility_resolver.py:402:            allowed_operations[legacy] = bool(allowed_operations.get(canonical, True))
backend/app/services/founder_pricing.py:26:    Map DB license.plan (may be legacy strings) to billing plan_code team|pro for founder slots.
backend/app/services/hr_verified_field_catalog.py:163:            "profile_keys": ["document.doc_type", "context.context_type"],
backend/app/services/user_notifications.py:102:    Used at write time and as fallback for legacy rows with NULL DB column.
backend/app/services/user_notifications.py:252:        # 2) fallback to entity-based match when no dedupe_key provided.
backend/app/services/communications_scheduler.py:1648:    """Clear lead-scoped reminders/planner rows that survived a lead→candidate link (hook missed or legacy data)."""
backend/app/services/lead_communications.py:286:        fallback_subject=default_subject,
backend/app/services/lead_communications.py:287:        fallback_body=default_body,
backend/app/services/recruitment_application_lifecycle.py:5:Legacy MVP bucket ``active`` maps to ``applied`` (lifecycle doc §3 legacy note).
backend/app/services/recruitment_application_lifecycle.py:35:_LEGACY_STATUS_ALIASES = {"active": "applied"}
backend/app/services/recruitment_application_lifecycle.py:47:    """Lowercase strip + map legacy ``active`` → ``applied``."""
backend/app/services/recruitment_application_lifecycle.py:51:    return _LEGACY_STATUS_ALIASES.get(s, s)
backend/app/services/recruitment_application_lifecycle.py:148:    * Legacy ``active`` is normalized to ``applied`` (same as reads).
backend/app/services/stripe_price_catalog.py:97:        "addon_operating_company_legacy",
backend/app/services/stripe_price_catalog.py:101:        "Legacy single Price if team/business-specific IDs not set",
backend/app/services/document_orders.py:8:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/document_orders.py:53:def _doc_type_of(doc: Any) -> str:
backend/app/services/document_orders.py:54:    raw_type = getattr(doc, "doc_type", None)
backend/app/services/document_orders.py:56:        raw_type = doc.get("doc_type")
backend/app/services/document_orders.py:57:    return normalize_doc_type(str(raw_type or ""))
backend/app/services/document_orders.py:95:    doc_type: str,
backend/app/services/document_orders.py:98:    canonical = normalize_doc_type(doc_type)
backend/app/services/document_orders.py:103:        if _doc_type_of(doc) not in acceptable:
backend/app/services/document_orders.py:113:        canonical = normalize_doc_type(str(raw))
backend/app/services/document_orders.py:128:    for doc_type in base_required_types(checklist):
backend/app/services/document_orders.py:129:        if not has_ready_document(documents, doc_type, last_check_by_document_id):
backend/app/services/document_orders.py:130:            missing.append(doc_type)
backend/app/services/document_orders.py:134:def find_documents_by_type(documents: Sequence[Any], doc_type: str) -> List[Any]:
backend/app/services/document_orders.py:135:    canonical = normalize_doc_type(doc_type)
backend/app/services/document_orders.py:138:    return [doc for doc in _iter_documents(documents) if _doc_type_of(doc) == canonical]
backend/app/services/document_orders.py:141:def is_orderable(doc_type: str) -> bool:
backend/app/services/document_orders.py:142:    return normalize_doc_type(doc_type) in ORDERABLE_CODES
backend/app/services/document_files.py:116:    # Legacy fallback for documents that only carry `Document.path`.
backend/app/api/public/intake.py:46:    doc_type_requires_user_comment,
backend/app/api/public/intake.py:47:    get_doc_type_defaults,
backend/app/api/public/intake.py:308:    """Intake models require exactly two letters; legacy rows may hold 3-letter codes or garbage."""
backend/app/api/public/intake.py:427:    # legacy fields for backwards compatibility
backend/app/api/public/intake.py:636:    doc_type: str
backend/app/api/public/intake.py:1267:def _ensure_user_comment(doc_type: str, comment: Optional[str]) -> None:
backend/app/api/public/intake.py:1268:    if doc_type_requires_user_comment(doc_type) and not comment:
backend/app/api/public/intake.py:1271:            detail="user_comment required for doc_type 'additional_document'",
backend/app/api/public/intake.py:1300:    doc_type_hint: str,
backend/app/api/public/intake.py:1336:    guessed = auto_fill_from_file(str(target_path), hinted_key=doc_type_hint)
backend/app/api/public/intake.py:1337:    defaults = get_doc_type_defaults(guessed.get("key") or doc_type_hint)
backend/app/api/public/intake.py:1338:    doc_type = defaults.doc_type
backend/app/api/public/intake.py:1346:    resolved_title = guessed.get("title") or (original_name or doc_type)
backend/app/api/public/intake.py:1347:    custom_name = resolved_title if doc_type == "other" else None
backend/app/api/public/intake.py:1354:            Document.doc_type == doc_type,
backend/app/api/public/intake.py:1372:    _ensure_user_comment(doc_type, final_comment)
backend/app/api/public/intake.py:1420:        "doc_type": doc_type,
backend/app/api/public/intake.py:1455:            doc_type=doc_type,
backend/app/api/public/intake.py:1672:        doc_type = str(entry.get("doc_type") or entry.get("type") or "").strip()
backend/app/api/public/intake.py:1673:        if not doc_type:
backend/app/api/public/intake.py:1675:        entries_by_type.setdefault(doc_type, entry)
backend/app/api/public/intake.py:1780:def _serialize_doc_types(codes: Sequence[str]) -> Dict[str, Any]:
backend/app/api/public/intake.py:1783:        defaults = get_doc_type_defaults(code)
backend/app/api/public/intake.py:1784:        doc_type = defaults.doc_type
backend/app/api/public/intake.py:1785:        if doc_type in payload:
backend/app/api/public/intake.py:1787:        payload[doc_type] = {
backend/app/api/public/intake.py:1788:            "doc_type": doc_type,
backend/app/api/public/intake.py:1811:def _collect_doc_type_codes(
backend/app/api/public/intake.py:1819:            doc_type = str(entry).strip()
backend/app/api/public/intake.py:1820:            if doc_type and doc_type not in seen:
backend/app/api/public/intake.py:1821:                seen.add(doc_type)
backend/app/api/public/intake.py:1822:                codes.append(doc_type)
backend/app/api/public/intake.py:1824:        doc_type = str(doc.get("doc_type") or doc.get("type") or "").strip()
backend/app/api/public/intake.py:1825:        if doc_type and doc_type not in seen:
backend/app/api/public/intake.py:1826:            seen.add(doc_type)
backend/app/api/public/intake.py:1827:            codes.append(doc_type)
backend/app/api/public/intake.py:1897:                "type": doc.doc_type,
backend/app/api/public/intake.py:1898:                "doc_type": doc.doc_type,
backend/app/api/public/intake.py:1916:    doc_type_codes = _collect_doc_type_codes(checklist, doc_entries)
backend/app/api/public/intake.py:1917:    if not doc_type_codes:
backend/app/api/public/intake.py:1919:        doc_type_codes = [getattr(row, "code", None) or getattr(row, "key", None) or "" for row in catalog]
backend/app/api/public/intake.py:1920:        doc_type_codes = [code for code in doc_type_codes if code]
backend/app/api/public/intake.py:1924:        "doc_types": _serialize_doc_types(doc_type_codes),
backend/app/api/public/intake.py:2664:        doc_type
backend/app/api/public/intake.py:2665:        for doc_type in checklist.get("requiredTypes") or []
backend/app/api/public/intake.py:2666:        if not has_ready_document(docs, doc_type)
backend/app/api/public/intake.py:2736:    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
backend/app/api/public/intake.py:2747:        document_class=payload.doc_type.strip(),
backend/app/api/public/intake.py:2809:            document_class=payload.doc_type.strip(),
backend/app/api/public/intake.py:2815:    filename = payload.filename.strip() or f"{payload.doc_type}.bin"
backend/app/api/public/intake.py:2826:        document_class=payload.doc_type.strip(),
backend/app/api/public/intake.py:2843:    doc_type: str = Form(...),
backend/app/api/public/intake.py:2849:    if not doc_type.strip():
backend/app/api/public/intake.py:2850:        raise HTTPException(status_code=422, detail="doc_type is required")
backend/app/api/public/intake.py:2858:        doc_type.strip(),
backend/app/api/public/intake.py:2868:            source_doc_type=doc_type.strip(),
backend/app/api/public/intake.py:2899:    doc_type: str = Form(...),
backend/app/api/public/intake.py:2908:    if not doc_type.strip():
backend/app/api/public/intake.py:2909:        raise HTTPException(status_code=422, detail="doc_type is required")
backend/app/api/public/intake.py:2928:        doc_type.strip(),
backend/app/api/public/intake.py:2988:            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
backend/app/api/public/intake.py:3002:        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
backend/app/api/public/intake.py:3054:            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
backend/app/api/public/intake.py:3068:        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
backend/app/api/public/intake.py:3097:    fallback_cfg = _DEFAULT_CANDIDATE_DEFAULTS
backend/app/api/public/intake.py:3103:            or fallback_cfg.get("requiredTypes")
backend/app/api/public/intake.py:3109:            or fallback_cfg.get("optionalTypes")
backend/app/services/scanner.py:83:            # Fallback to current timestamp if file doesn't exist or error
backend/app/services/scanner.py:103:        from backend.app.services.scanner_presets import get_preset_for_doc_type, get_preset
backend/app/services/scanner.py:105:            preset_obj = get_preset_for_doc_type(document_type)
backend/app/services/scanner.py:111:            # Try fallback to additional_document preset
backend/app/services/scanner.py:314:        detected_doc_type = session.document_type
backend/app/services/scanner.py:363:                        doc_type_hint=session.document_type,
backend/app/services/scanner.py:381:                        # Fallback: process image directly if scanner didn't save it
backend/app/services/scanner.py:423:                        # Always update detected_doc_type from scan result
backend/app/services/scanner.py:424:                        detected_doc_type = scan_result.document_type
backend/app/services/scanner.py:429:                            old_doc_type = session.document_type
backend/app/services/scanner.py:430:                            session.document_type = detected_doc_type
backend/app/services/scanner.py:433:                            logger.info(f"Auto-detected document type: {old_doc_type} -> {detected_doc_type} (confidence: {confidence:.2f})")
backend/app/services/scanner.py:448:        session.meta["detected_document_type"] = detected_doc_type
backend/app/services/scanner.py:454:    except Exception as exc:  # pragma: no cover - safety fallback
backend/app/services/scanner.py:653:            doc_type=session.document_type,
backend/app/api/public/scanner.py:231:        doc_type_hint = str(meta_payload.get("doc_type") or session.document_type or "").strip() or "other"
backend/app/api/public/scanner.py:238:            doc_type_hint,
backend/app/api/public/scanner.py:252:                source_doc_type=doc_type_hint,
backend/app/services/contract_generation.py:50:            # Bare legacy keys at bindings root (legal_name without namespace) — disallow in templates
backend/app/api/public/legal_pages.py:12:from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, get_db
backend/app/api/public/legal_pages.py:18:_SLUG_TO_DOC_TYPE: dict[str, str] = {
backend/app/api/public/legal_pages.py:29:        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/public/legal_pages.py:68:        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/public/legal_pages.py:76:        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/public/legal_pages.py:84:    return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/public/legal_pages.py:88:        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/public/legal_pages.py:120:    doc_type = _SLUG_TO_DOC_TYPE.get((slug or "").strip().lower())
backend/app/api/public/legal_pages.py:121:    if not doc_type:
backend/app/api/public/legal_pages.py:122:        fallback = Path("/app/public/legal") / f"{slug}.html"
backend/app/api/public/legal_pages.py:123:        if fallback.is_file():
backend/app/api/public/legal_pages.py:124:            return FileResponse(str(fallback))
backend/app/api/public/legal_pages.py:130:        if explicit_tenant != str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID) or (tenant_id_header or tenant_id_query)
backend/app/api/public/legal_pages.py:133:    doc = await get_active_legal_document(db, tenant_id, doc_type)
backend/app/api/public/legal_pages.py:147:    fallback = Path("/app/public/legal") / f"{slug}.html"
backend/app/api/public/legal_pages.py:148:    if fallback.is_file():
backend/app/api/public/legal_pages.py:149:        return FileResponse(str(fallback))
backend/app/api/public/intake_tenant_bind.py:4:SQLite / tests: ORM fallback (no RLS).
backend/app/api/public/intake_tenant_bind.py:17:from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, bind_tenant_context_to_session, get_db
backend/app/api/public/intake_tenant_bind.py:212:    """Tenant for POST /public/intake: lead-form reference wins; else explicit X-Tenant-Id (not the legacy default)."""
backend/app/api/public/intake_tenant_bind.py:269:    if tid == PUBLIC_LEGACY_DEFAULT_TENANT_UUID:
backend/app/services/timeoff_cleanup.py:65:# enum from ADR-012 §6 plus the `cancelled` terminal. The legacy
backend/app/services/timeoff_cleanup.py:180:    # window on ``due_at`` — same semantics as the legacy reminders
backend/app/services/timeoff_cleanup.py:182:    # "active" status; the legacy ``pending`` value is collapsed to
backend/app/services/timeoff_cleanup.py:202:    # Time-bound rows have ``starts_at IS NOT NULL``. The legacy
backend/app/services/global_search_v1.py:398:        # JSON: prefer trigger-maintained tsvector (GIN); coalesce fallback before backfill / old rows.
backend/app/services/global_search_v1.py:484:            func.lower(Document.doc_type).like(like),
backend/app/services/global_search_v1.py:499:            func.coalesce(Document.doc_type, ""),
backend/app/services/global_search_v1.py:550:        title = (str(doc.custom_name).strip() if doc.custom_name else "") or str(doc.doc_type or "").strip() or "Document"
backend/app/services/documents.py:56:    # Нормализуем doc_types к List[Dict[str, Any]]
backend/app/services/documents.py:57:    doc_types_raw: Any = load_config("doc_types.json")
backend/app/services/documents.py:58:    if isinstance(doc_types_raw, dict):
backend/app/services/documents.py:59:        doc_types: List[Dict[str, Any]] = [
backend/app/services/documents.py:60:            v for v in doc_types_raw.values() if isinstance(v, dict)
backend/app/services/documents.py:62:    elif isinstance(doc_types_raw, list):
backend/app/services/documents.py:63:        doc_types = [d for d in doc_types_raw if isinstance(d, dict)]
backend/app/services/documents.py:65:        doc_types = []
backend/app/services/documents.py:105:        d["code"]: d for d in doc_types if isinstance(d, dict) and "code" in d
backend/app/services/draft_reminders.py:66:    # Fallback for local dev
backend/app/services/hr_review_current_task.py:399:    # Fallback: unresolved blockers
backend/app/services/candidate_telegram_notifications.py:85:def _candidate_intake_documents_url(candidate: Candidate, *, doc_type: str | None = None) -> str | None:
backend/app/services/candidate_telegram_notifications.py:91:    if doc_type:
backend/app/services/candidate_telegram_notifications.py:92:        query["doc"] = str(doc_type).strip()
backend/app/services/candidate_telegram_notifications.py:298:                "type": str(doc.doc_type or "").strip(),
backend/app/services/candidate_telegram_notifications.py:299:                "doc_type": str(doc.doc_type or "").strip(),
backend/app/services/candidate_telegram_notifications.py:320:        "next_doc_type": next_doc,
backend/app/services/candidate_telegram_notifications.py:435:    source_doc_type: str | None = None,
backend/app/services/candidate_telegram_notifications.py:457:        if source_doc_type:
backend/app/services/candidate_telegram_notifications.py:458:            lines.append(f"Загружен: {get_document_display_name(str(source_doc_type))}")
backend/app/services/candidate_telegram_notifications.py:464:        next_doc = str(snapshot.get("next_doc_type") or "").strip() or None
backend/app/services/candidate_telegram_notifications.py:465:        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
backend/app/services/candidate_telegram_notifications.py:509:        next_doc = str(snapshot.get("next_doc_type") or "").strip() or missing[0]
backend/app/services/candidate_telegram_notifications.py:518:        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
backend/app/services/hr_verification_plan.py:401:def _legacy_row_for_slot(
backend/app/services/hr_verification_plan.py:403:    legacy_rows: list[dict[str, Any]],
backend/app/services/hr_verification_plan.py:405:    for r in legacy_rows:
backend/app/services/hr_verification_plan.py:423:    legacy_approval_rows: Optional[list[dict[str, Any]]] = None,
backend/app/services/hr_verification_plan.py:466:    legacy = list(legacy_approval_rows or [])
backend/app/services/hr_verification_plan.py:487:        row = _legacy_row_for_slot(slot.document_key, legacy)
backend/app/services/lead_rodo.py:282:        fallback_subject="RODO / GDPR — Personal data processing information | HostFlow",
backend/app/services/lead_rodo.py:283:        fallback_body=body,
backend/app/services/reference_service_facade.py:159:        doc_type = (
backend/app/services/reference_service_facade.py:162:        if not doc_type:
backend/app/services/reference_service_facade.py:173:                .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
backend/app/services/reference_service_facade.py:182:                "document_code": str(doc_type.code),
backend/app/services/reference_service_facade.py:183:                "category": str(doc_type.category_code or ""),
backend/app/services/reference_service_facade.py:184:                "criticality": str(doc_type.criticality or ""),
backend/app/services/reference_service_facade.py:185:                "document_type_id": str(doc_type.id),
backend/app/services/document_catalog.py:19:    doc_type: str
backend/app/services/document_catalog.py:56:        doc_type=definition.code,
backend/app/services/document_catalog.py:78:        DOCUMENT_TYPE_ALIASES[alias] = defaults.doc_type
backend/app/services/document_catalog.py:81:def normalize_doc_type(raw: str | None) -> str:
backend/app/services/document_catalog.py:91:def get_doc_type_defaults(raw: str | None) -> DocumentTypeDefaults:
backend/app/services/document_catalog.py:92:    canonical = normalize_doc_type(raw)
backend/app/services/document_catalog.py:97:        doc_type=canonical,
backend/app/services/document_catalog.py:116:def doc_type_requires_user_comment(raw: str | None) -> bool:
backend/app/services/document_catalog.py:121:    defaults = get_doc_type_defaults(raw)
backend/app/services/document_catalog.py:122:    return defaults.doc_type == "additional_document"
backend/app/services/document_catalog.py:170:def normalize_kind(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
backend/app/services/document_catalog.py:172:        return fallback
backend/app/services/document_catalog.py:180:    value: Optional[str], fallback: DocumentRequestedFrom
backend/app/services/document_catalog.py:183:        return fallback
backend/app/services/document_catalog.py:191:    value: Optional[str], fallback: DocumentProcessType
backend/app/services/document_catalog.py:194:        return fallback
backend/app/services/document_catalog.py:199:        if fallback:
backend/app/services/document_catalog.py:200:            return fallback
backend/app/services/document_catalog.py:215:        raw_doc_type = item.get("doc_type")
backend/app/services/document_catalog.py:216:        doc_type = normalize_doc_type(str(raw_doc_type or ""))
backend/app/services/document_catalog.py:217:        if not doc_type:
backend/app/services/document_catalog.py:220:        defaults = get_doc_type_defaults(doc_type)
backend/app/services/document_catalog.py:247:        prepared[doc_type] = {
backend/app/services/document_catalog.py:248:            "doc_type": doc_type,
backend/app/services/document_catalog.py:259:        pesel_defaults = get_doc_type_defaults("pesel")
backend/app/services/document_catalog.py:261:            "doc_type": "pesel",
backend/app/services/hr_dashboard.py:26:# Open / actionable reminder rows (legacy statuses still possible in DB).
backend/app/services/hr_dashboard.py:335:    for doc_type in sorted(by_type.keys()):
backend/app/services/hr_dashboard.py:336:        items = by_type[doc_type]
backend/app/services/hr_dashboard.py:339:                "document_type": doc_type,
backend/app/services/pipeline_sync.py:59:    Safe fallback: returns 'unknown' when empty; passes through unknown codes.
backend/app/api/v1/candidate_documents.py:62:    doc_type_requires_user_comment,
backend/app/api/v1/candidate_documents.py:63:    get_doc_type_defaults,
backend/app/api/v1/candidate_documents.py:64:    normalize_doc_type,
backend/app/api/v1/candidate_documents.py:191:def _kind_or_422(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
backend/app/api/v1/candidate_documents.py:193:        return normalize_kind(value, fallback)
backend/app/api/v1/candidate_documents.py:199:    value: Optional[str], fallback: DocumentRequestedFrom
backend/app/api/v1/candidate_documents.py:202:        return normalize_requested_from(value, fallback)
backend/app/api/v1/candidate_documents.py:216:    value: Optional[str], fallback: DocumentProcessType
backend/app/api/v1/candidate_documents.py:219:        return normalize_process_type(value, fallback)
backend/app/api/v1/candidate_documents.py:289:    fallback: Optional[str] = None,
backend/app/api/v1/candidate_documents.py:301:    return fallback
backend/app/api/v1/candidate_documents.py:304:def _ensure_comment_requirement(doc_type: str, comment: Optional[str]) -> None:
backend/app/api/v1/candidate_documents.py:305:    if doc_type_requires_user_comment(doc_type) and not comment:
backend/app/api/v1/candidate_documents.py:308:            detail="user_comment required for doc_type 'additional_document'",
backend/app/api/v1/candidate_documents.py:466:    doc_type: str
backend/app/api/v1/candidate_documents.py:534:        title = custom_name or (meta.get("title") if isinstance(meta, dict) else None) or d.doc_type
backend/app/api/v1/candidate_documents.py:541:            key=d.doc_type,
backend/app/api/v1/candidate_documents.py:542:            doc_type=d.doc_type,
backend/app/api/v1/candidate_documents.py:574:    doc_type: Optional[str] = None
backend/app/api/v1/candidate_documents.py:600:    doc_type: Optional[str] = None
backend/app/api/v1/candidate_documents.py:869:    effective_key = (payload.key or payload.doc_type or "").strip()
backend/app/api/v1/candidate_documents.py:871:        raise HTTPException(status_code=422, detail="Document key or doc_type required")
backend/app/api/v1/candidate_documents.py:873:    defaults = get_doc_type_defaults(payload.doc_type or effective_key)
backend/app/api/v1/candidate_documents.py:877:    doc_type = defaults.doc_type
backend/app/api/v1/candidate_documents.py:899:    _ensure_comment_requirement(doc_type, user_comment)
backend/app/api/v1/candidate_documents.py:904:    meta_payload.setdefault("doc_type", doc_type)
backend/app/api/v1/candidate_documents.py:929:    await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
backend/app/api/v1/candidate_documents.py:938:        doc_type=doc_type,
backend/app/api/v1/candidate_documents.py:975:            doc_type=doc_type,
backend/app/api/v1/candidate_documents.py:1043:    meta_payload.setdefault("doc_type", getattr(m, "doc_type", None))
backend/app/api/v1/candidate_documents.py:1048:    doc_type_input = payload.doc_type or payload.key
backend/app/api/v1/candidate_documents.py:1049:    if doc_type_input is not None:
backend/app/api/v1/candidate_documents.py:1050:        defaults = get_doc_type_defaults(doc_type_input)
backend/app/api/v1/candidate_documents.py:1051:        m.doc_type = defaults.doc_type
backend/app/api/v1/candidate_documents.py:1052:        await documents_crud.ensure_document_type(db, str(cand.tenant_id), defaults.doc_type)
backend/app/api/v1/candidate_documents.py:1059:        meta_payload["doc_type"] = doc_type_input
backend/app/api/v1/candidate_documents.py:1061:        defaults = get_doc_type_defaults(m.doc_type)
backend/app/api/v1/candidate_documents.py:1072:        requires_custom = get_doc_type_defaults(m.doc_type).requires_custom_name
backend/app/api/v1/candidate_documents.py:1076:    elif doc_type_input is not None and get_doc_type_defaults(m.doc_type).requires_custom_name:
backend/app/api/v1/candidate_documents.py:1077:        fallback_name = m.custom_name or (payload.title or "").strip()
backend/app/api/v1/candidate_documents.py:1078:        if not fallback_name:
backend/app/api/v1/candidate_documents.py:1116:        fallback=getattr(m, "user_comment", None),
backend/app/api/v1/candidate_documents.py:1118:    _ensure_comment_requirement(m.doc_type, user_comment)
backend/app/api/v1/candidate_documents.py:1220:                    f"Статус вашего документа '{m.doc_type}' изменен на '{status_label}'",
backend/app/api/v1/candidate_documents.py:1224:                        "document_type": m.doc_type,
backend/app/api/v1/candidate_documents.py:1261:                document_type=str(getattr(m, "doc_type", "") or ""),
backend/app/api/v1/candidate_documents.py:1315:    keep_types = {entry["doc_type"] for entry in template_docs}
backend/app/api/v1/candidate_documents.py:1334:        existing_by_type.setdefault(doc.doc_type, doc)
backend/app/api/v1/candidate_documents.py:1339:        doc_type = entry["doc_type"]
backend/app/api/v1/candidate_documents.py:1340:        defaults = get_doc_type_defaults(doc_type)
backend/app/api/v1/candidate_documents.py:1344:        await documents_crud.ensure_document_type(db, str(cand.tenant_id), defaults.doc_type)
backend/app/api/v1/candidate_documents.py:1356:        existing = existing_by_type.get(doc_type)
backend/app/api/v1/candidate_documents.py:1402:            doc_meta.setdefault("doc_type", doc_type)
backend/app/api/v1/candidate_documents.py:1414:            await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
backend/app/api/v1/candidate_documents.py:1423:                doc_type=doc_type,
backend/app/api/v1/candidate_documents.py:1439:        if doc.doc_type in keep_types or doc.doc_type == "other" or doc.deleted_at is not None:
backend/app/api/v1/candidate_documents.py:1705:    defaults = get_doc_type_defaults(g_key)
backend/app/api/v1/candidate_documents.py:1709:    doc_type = defaults.doc_type
backend/app/api/v1/candidate_documents.py:1713:    if doc_type == "other":
backend/app/api/v1/candidate_documents.py:1723:    _ensure_comment_requirement(doc_type, normalized_comment)
backend/app/api/v1/candidate_documents.py:1726:    meta_payload["doc_type"] = doc_type
backend/app/api/v1/candidate_documents.py:1754:    await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
backend/app/api/v1/candidate_documents.py:1770:        doc_type=doc_type,
backend/app/api/v1/candidate_documents.py:1896:            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
backend/app/api/v1/candidate_documents.py:1915:            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
backend/app/api/v1/candidate_documents.py:1929:            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
backend/app/api/v1/candidate_documents.py:1946:        document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
backend/app/services/requirement_checker.py:108:            doc_type_code = rule.get("document_type")
backend/app/services/requirement_checker.py:122:            if doc_type_code:
backend/app/services/requirement_checker.py:123:                stmt_doc_type = (
backend/app/services/requirement_checker.py:126:                    .where(DocumentType.code == doc_type_code)
backend/app/services/requirement_checker.py:129:                doc_type = (await db.execute(stmt_doc_type)).scalar_one_or_none()
backend/app/services/requirement_checker.py:130:                if doc_type:
backend/app/services/requirement_checker.py:131:                    stmt_docs = stmt_docs.where(Document.doc_type == doc_type.code)
backend/app/services/requirement_checker.py:177:        stmt_doc_type = (
backend/app/services/requirement_checker.py:182:        doc_type = (await db.execute(stmt_doc_type)).scalar_one_or_none()
backend/app/services/requirement_checker.py:183:        if not doc_type:
backend/app/services/requirement_checker.py:196:            .where(Document.doc_type == doc_type.code)
backend/app/services/requirement_checker.py:214:            message=None if satisfied else f"Document type {doc_type.code} not found or invalid",
backend/app/services/candidate_doc_pipeline_guard.py:26:from backend.app.services.document_catalog import normalize_doc_type
backend/app/services/candidate_doc_pipeline_guard.py:105:def _norm_doc_type(value: str) -> str:
backend/app/services/candidate_doc_pipeline_guard.py:109:    return normalize_doc_type(raw) or raw
backend/app/services/candidate_doc_pipeline_guard.py:118:    rset = {_norm_doc_type(x) for x in relaxed if x}
backend/app/services/candidate_doc_pipeline_guard.py:124:            if _norm_doc_type(x) not in rset:
backend/app/services/candidate_doc_pipeline_guard.py:176:        "type": doc.doc_type,
backend/app/services/candidate_doc_pipeline_guard.py:177:        "doc_type": doc.doc_type,
backend/app/services/reminder_tasks.py:23:    resolve_assignee_id_with_queue_fallback,
backend/app/services/reminder_tasks.py:307:    eff_assignee, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
backend/app/services/reminder_tasks.py:597:    # legacy planner-event PATCHes onto `PATCH /activities/{id}` and may
backend/app/services/reminder_tasks.py:606:        # Closed Activity enum (ADR-012 §6) plus the transient legacy
backend/app/services/reminder_tasks.py:615:            # Legacy planner / reminder statuses — collapsed to "planned"
backend/app/services/reminder_tasks.py:648:        # Wholesale replace — mirrors legacy planner PATCH semantics. The
backend/app/services/reminder_tasks.py:675:        eff_id, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
backend/app/services/users.py:1975:    (legacy / partially migrated tenants) so solo-operator detection still works.
backend/app/services/document_type_runtime_resolver.py:12:from backend.app.services.document_reference_sync import normalize_legacy_doc_type
backend/app/services/document_type_runtime_resolver.py:31:    fallback_used: bool
backend/app/services/document_type_runtime_resolver.py:32:    fallback_source: Optional[str]
backend/app/services/document_type_runtime_resolver.py:36:    """Single runtime source for document type metadata with legacy fallback."""
backend/app/services/document_type_runtime_resolver.py:63:        # 3) legacy documents.doc_type -> canonical mapping
backend/app/services/document_type_runtime_resolver.py:64:        legacy_raw = str(getattr(document, "doc_type", "") or "").strip()
backend/app/services/document_type_runtime_resolver.py:65:        canonical_code = normalize_legacy_doc_type(legacy_raw)
backend/app/services/document_type_runtime_resolver.py:66:        resolved = await cls._resolve_by_canonical_code(db, canonical_code, fallback_used=True, fallback_source="legacy_doc_type", document=document)
backend/app/services/document_type_runtime_resolver.py:69:                "document_reference_runtime_fallback_used",
backend/app/services/document_type_runtime_resolver.py:71:                legacy_doc_type=legacy_raw,
backend/app/services/document_type_runtime_resolver.py:73:                fallback_source="legacy_doc_type",
backend/app/services/document_type_runtime_resolver.py:77:        # 4) fallback to other
backend/app/services/document_type_runtime_resolver.py:78:        cls._log("document_reference_unknown_legacy_type", document_id=str(document.id), legacy_doc_type=legacy_raw)
backend/app/services/document_type_runtime_resolver.py:79:        resolved_other = await cls._resolve_by_canonical_code(db, "other", fallback_used=True, fallback_source="other", document=document)
backend/app/services/document_type_runtime_resolver.py:81:            cls._log("document_reference_runtime_fallback_used", document_id=str(document.id), legacy_doc_type=legacy_raw, canonical_code="other", fallback_source="other")
backend/app/services/document_type_runtime_resolver.py:98:            fallback_used=True,
backend/app/services/document_type_runtime_resolver.py:99:            fallback_source="emergency",
backend/app/services/document_type_runtime_resolver.py:118:        ver, doc_type = row
backend/app/services/document_type_runtime_resolver.py:119:        return cls._build_resolved(doc_type, ver, fallback_used=False, fallback_source=None)
backend/app/services/document_type_runtime_resolver.py:129:        doc_type = await db.get(RefDocumentType, document_type_id)
backend/app/services/document_type_runtime_resolver.py:130:        if not doc_type:
backend/app/services/document_type_runtime_resolver.py:142:            return cls._build_resolved(doc_type, None, fallback_used=True, fallback_source="document_type_no_version")
backend/app/services/document_type_runtime_resolver.py:143:        return cls._build_resolved(doc_type, ver, fallback_used=False, fallback_source=None)
backend/app/services/document_type_runtime_resolver.py:151:        fallback_used: bool,
backend/app/services/document_type_runtime_resolver.py:152:        fallback_source: Optional[str],
backend/app/services/document_type_runtime_resolver.py:156:        doc_type = (await db.execute(stmt)).scalars().first()
backend/app/services/document_type_runtime_resolver.py:157:        if not doc_type:
backend/app/services/document_type_runtime_resolver.py:162:            .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
backend/app/services/document_type_runtime_resolver.py:168:        return cls._build_resolved(doc_type, ver, fallback_used=fallback_used, fallback_source=fallback_source)
backend/app/services/document_type_runtime_resolver.py:172:        doc_type: RefDocumentType,
backend/app/services/document_type_runtime_resolver.py:175:        fallback_used: bool,
backend/app/services/document_type_runtime_resolver.py:176:        fallback_source: Optional[str],
backend/app/services/document_type_runtime_resolver.py:196:            canonical_document_type_id=str(doc_type.id),
backend/app/services/document_type_runtime_resolver.py:197:            canonical_code=str(doc_type.code),
backend/app/services/document_type_runtime_resolver.py:198:            canonical_public_name=str(doc_type.public_name or ""),
backend/app/services/document_type_runtime_resolver.py:200:            category_code=str(doc_type.category_code or "") or None,
backend/app/services/document_type_runtime_resolver.py:201:            subcategory_code=str(doc_type.subcategory_code or "") or None,
backend/app/services/document_type_runtime_resolver.py:205:            compliance_criticality=str(doc_type.criticality or "") or None,
backend/app/services/document_type_runtime_resolver.py:208:            fallback_used=fallback_used,
backend/app/services/document_type_runtime_resolver.py:209:            fallback_source=fallback_source,
backend/app/services/document_workflow.py:381:    # Generic fallbacks
backend/app/api/v1/meta.py:129:    # Fallback: use candidate_stage_dict if no funnel stages
backend/app/api/v1/meta.py:180:    # используем codes (если он пустой, fallback на merged_order)
backend/app/api/v1/own_companies.py:29:legacy_router = APIRouter(prefix="/own_companies", tags=["own-companies"], redirect_slashes=False)
backend/app/api/v1/own_companies.py:150:@legacy_router.get("", response_model=OwnCompanyListOut, include_in_schema=False)
backend/app/api/v1/own_companies.py:151:@legacy_router.get("/", response_model=OwnCompanyListOut, include_in_schema=False)
backend/app/api/v1/own_companies.py:176:@legacy_router.post("", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
backend/app/api/v1/own_companies.py:177:@legacy_router.post("/", response_model=OwnCompanyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
backend/app/api/v1/own_companies.py:296:@legacy_router.patch("/{own_company_id}", response_model=OwnCompanyOut, include_in_schema=False)
backend/app/api/v1/own_companies.py:334:@legacy_router.post("/active", response_model=OwnCompanyListOut, include_in_schema=False)
backend/app/api/v1/calendar.py:32:from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, get_db, get_db_with_tenant
backend/app/api/v1/calendar.py:762:    return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
backend/app/api/v1/document_policies.py:98:    """List document policies for the tenant (scoped to active own-company + legacy rows)."""
backend/app/api/v1/documents.py:16:except Exception:  # pragma: no cover - pydantic<2 fallback
backend/app/api/v1/documents.py:39:    doc_type_requires_user_comment,
backend/app/api/v1/documents.py:40:    get_doc_type_defaults,
backend/app/api/v1/documents.py:41:    normalize_doc_type,
backend/app/api/v1/documents.py:163:def _ensure_user_comment_requirement(doc_type: str, comment: Optional[str]) -> None:
backend/app/api/v1/documents.py:164:    if doc_type_requires_user_comment(doc_type) and not comment:
backend/app/api/v1/documents.py:167:            detail="user_comment required for doc_type 'additional_document'",
backend/app/api/v1/documents.py:179:    "doc_type": ("doc_type", "type", "key"),
backend/app/api/v1/documents.py:187:    "doc_type": ("doc_type", "type", "key"),
backend/app/api/v1/documents.py:214:        doc_type: str = Field(
backend/app/api/v1/documents.py:215:            ..., min_length=1, validation_alias=AliasChoices("doc_type", "type", "key")
backend/app/api/v1/documents.py:255:        doc_type: str
backend/app/api/v1/documents.py:308:        doc_type: str = Field(..., min_length=1)
backend/app/api/v1/documents.py:351:        doc_type: str
backend/app/api/v1/documents.py:408:    doc_type: str
backend/app/api/v1/documents.py:430:    doc_type: str = Field(
backend/app/api/v1/documents.py:433:        validation_alias=AliasChoices("doc_type", "type", "key") if PYDANTIC_V2 else None,
backend/app/api/v1/documents.py:442:        def _assign_doc_type(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[misc]
backend/app/api/v1/documents.py:444:            selected = data.get("doc_type")
backend/app/api/v1/documents.py:449:                        data["doc_type"] = alias_value
backend/app/api/v1/documents.py:648:    canonical_type = normalize_doc_type(getattr(d, "doc_type", None) or getattr(d, "type", ""))
backend/app/api/v1/documents.py:649:    display_type = meta.get("submitted_doc_type") or canonical_type
backend/app/api/v1/documents.py:657:        doc_type=canonical_type,
backend/app/api/v1/documents.py:695:            doc_type=entry["doc_type"],
backend/app/api/v1/documents.py:722:    doc_type: Optional[str] = Query(None, alias="type"),
backend/app/api/v1/documents.py:741:    current_type = doc_type or key
backend/app/api/v1/documents.py:743:        stmt = stmt.where(Document.doc_type == normalize_doc_type(current_type))
backend/app/api/v1/documents.py:786:    doc_type = normalize_doc_type(payload.doc_type)
backend/app/api/v1/documents.py:787:    defaults = get_doc_type_defaults(doc_type)
backend/app/api/v1/documents.py:788:    if doc_type not in ORDERABLE_CODES or not defaults.orderable:
backend/app/api/v1/documents.py:789:        raise HTTPException(status_code=422, detail="doc_type is not orderable")
backend/app/api/v1/documents.py:791:    if doc_type == "work_permit" and payload.requested_from is None:
backend/app/api/v1/documents.py:825:    same_type_docs = find_documents_by_type(active_docs, doc_type)
backend/app/api/v1/documents.py:829:            detail={"code": "document_exists", "doc_type": doc_type},
backend/app/api/v1/documents.py:833:    if doc_type == "driver_certificate":
backend/app/api/v1/documents.py:854:        "doc_type": doc_type,
backend/app/api/v1/documents.py:882:        doc_type=doc_type,
backend/app/api/v1/documents.py:907:    defaults = get_doc_type_defaults(payload.doc_type)
backend/app/api/v1/documents.py:908:    doc_type = defaults.doc_type
backend/app/api/v1/documents.py:918:            status_code=422, detail="custom_name required for doc_type 'other'"
backend/app/api/v1/documents.py:921:        raise HTTPException(status_code=422, detail="kind required for doc_type 'other'")
backend/app/api/v1/documents.py:927:    _ensure_user_comment_requirement(doc_type, user_comment)
backend/app/api/v1/documents.py:946:    await documents_crud.ensure_document_type(db, str(tenant_id), doc_type)
backend/app/api/v1/documents.py:963:        doc_type=doc_type,
backend/app/api/v1/documents.py:999:        doc_type: Optional[str] = Field(
backend/app/api/v1/documents.py:1000:            default=None, validation_alias=AliasChoices("doc_type", "type", "key")
backend/app/api/v1/documents.py:1037:        doc_type: Optional[str] = Field(default=None)
backend/app/api/v1/documents.py:1099:    defaults = get_doc_type_defaults(obj.doc_type)
backend/app/api/v1/documents.py:1108:    if payload.doc_type is not None:
backend/app/api/v1/documents.py:1109:        defaults = get_doc_type_defaults(payload.doc_type)
backend/app/api/v1/documents.py:1110:        obj.doc_type = defaults.doc_type
backend/app/api/v1/documents.py:1111:        await documents_crud.ensure_document_type(db, str(tenant_id), defaults.doc_type)
backend/app/api/v1/documents.py:1149:        raise HTTPException(status_code=422, detail="custom_name required for doc_type 'other'")
backend/app/api/v1/documents.py:1153:    _ensure_user_comment_requirement(obj.doc_type, obj.user_comment)
backend/app/api/v1/documents.py:1294:                    document_type=str(getattr(obj, "doc_type", "") or ""),
backend/app/api/v1/documents.py:1461:def _kind_or_422(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
backend/app/api/v1/documents.py:1463:        return normalize_kind(value, fallback)
backend/app/api/v1/documents.py:1469:    value: Optional[str], fallback: DocumentRequestedFrom
backend/app/api/v1/documents.py:1472:        return normalize_requested_from(value, fallback)
backend/app/api/v1/documents.py:1478:    value: Optional[str], fallback: DocumentProcessType
backend/app/api/v1/documents.py:1481:        return normalize_process_type(value, fallback)
backend/app/api/v1/platform/tenants.py:223:            detail="Founder pricing requires a Team/Business-class license plan (internal team/pro or supported legacy plan codes).",
backend/app/api/v1/admin/users.py:380:async def revoke_refresh_legacy(
backend/app/api/v1/communications/__init__.py:168:    _format_doc_types_bullets,
backend/app/api/v1/communications/routes/planner.py:14:Phase 2.1 (ADR-012, 2026-05-09): the legacy planner-event surface
backend/app/api/v1/communications/routes/planner.py:18:``hostflow-frontend/src/api/communications.ts`` keeps the legacy
backend/app/api/v1/communications/routes/planner.py:457:# Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event HTTP routes
backend/app/api/v1/communications/routes/planner.py:462:# ``hostflow-frontend/src/api/communications.ts`` keeps the legacy
backend/app/api/v1/communications/routes/planner.py:546:# Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event create/patch
backend/app/api/v1/communications/routes/planner.py:551:# ``hostflow-frontend/src/api/communications.ts`` keeps the legacy
backend/app/api/v1/communications/routes/__init__.py:13:                 Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event
backend/app/api/v1/communications/schemas.py:3:Extracted from the legacy monolithic ``backend/app/api/v1/communications.py``
backend/app/api/v1/communications/schemas.py:78:    # removed together with the legacy planner-event HTTP routes. The
backend/app/api/v1/communications/schemas.py:681:# Phase 2.1 (ADR-012, 2026-05-09): the legacy planner-event schemas
backend/app/api/v1/communications/_helpers/oauth.py:11:* :mod:`backend.app.constants.spa_paths` — ``EMAIL_LEGACY``
backend/app/api/v1/communications/_helpers/oauth.py:21:from backend.app.constants.spa_paths import EMAIL_LEGACY
backend/app/api/v1/communications/_helpers/oauth.py:209:    safe_redirect_uri = redirect_uri or f"{_fe}{EMAIL_LEGACY}"
backend/app/api/v1/communications/_helpers/dispatch.py:106:    """Test/development fallback adapter used when no real channel adapter
backend/app/api/v1/communications/_helpers/dispatch.py:179:        # MVP fallback: keep HTML as plain text payload to avoid losing message.
backend/app/api/v1/communications/_helpers/candidate_lookup.py:14:  ``intake_state.notifications.telegram.chat_id`` fallback for chats
backend/app/api/v1/communications/_helpers/candidate_lookup.py:141:    # Fallback for newly linked chats before thread link sync.
backend/app/api/v1/communications/_helpers/telegram_intake/dispatcher.py:467:                        requested_doc_type=requested_doc,
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:32:    _format_doc_types_bullets,
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:61:    candidate: Candidate, doc_type: str | None = None
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:63:    """Public intake apply flow with documents step (replaces legacy /public/scan)."""
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:72:    doc_norm = str(doc_type or "").strip()
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:113:                "type": str(doc.doc_type or "").strip(),
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:114:                "doc_type": str(doc.doc_type or "").strip(),
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:170:        lines.extend(_format_doc_types_bullets(missing))
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:173:        lines.extend(_format_doc_types_bullets(in_progress))
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:176:        lines.extend(_format_doc_types_bullets(problematic))
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:217:                lines.extend(_format_doc_types_bullets(missing, limit=3))
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:236:        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:257:    requested_doc_type: str | None = None,
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:268:    requested = str(requested_doc_type or "").strip().lower()
backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py:304:        lines.extend(_format_doc_types_bullets(missing, limit=3))
backend/app/api/v1/communications/_helpers/telegram_intake/__init__.py:26:    _format_doc_types_bullets,
backend/app/api/v1/communications/_helpers/telegram_intake/__init__.py:80:    "_format_doc_types_bullets",
backend/app/api/v1/communications/_helpers/telegram_intake/ui_text.py:157:        "/scan [doc_type] - ссылка на загрузку документов на сайте\n"
backend/app/api/v1/communications/_helpers/telegram_intake/ui_text.py:241:def _format_doc_types_bullets(items: list[str], *, limit: int = 5) -> list[str]:
backend/app/api/v1/communications/_helpers/dto.py:124:# along with the legacy planner-event HTTP routes. Activity rows are
backend/app/api/v1/communications/_helpers/ingest.py:89:    # Fallback heuristic for MVP testing (same account + subject + sender among
backend/app/api/v1/communications/_helpers/ingest.py:152:    # Fallback: same channel + account + sender in recent active threads.
backend/app/api/v1/onboarding.py:98:    # Keep legacy client/counterparty classification from Company.extra for now.
backend/app/api/v1/onboarding.py:126:    # Backward compatibility: if tenant has legacy operating companies but no OwnCompany yet.
backend/app/api/v1/onboarding.py:128:        legacy_company_count_row = await db.execute(
backend/app/api/v1/onboarding.py:133:        legacy_total = int(legacy_company_count_row.scalar_one() or 0)
backend/app/api/v1/onboarding.py:134:        if legacy_total > 0:
backend/app/api/v1/candidate_employments.py:19:except ImportError:  # pragma: no cover - Pydantic v1 fallback
backend/app/api/v1/company_module_settings.py:30:    """Typed modules return schema-shaped JSON; invalid legacy rows coerce to v1 defaults."""
backend/app/api/v1/analytics.py:104:    """Fold legacy enum / label values into canonical stage codes (matches DB `employed`, etc.)."""
backend/app/api/v1/analytics.py:691:    # Mirror frontend deriveDocsMeta() fallback order (minimal subset).
backend/app/api/v1/analytics.py:954:def _candidate_scope_clause_legacy(tenant_id: str, visibility: TenantVisibility | None):
backend/app/api/v1/analytics.py:1812:        # Legacy rows (only ``Candidate.manager`` string, no FK) still
backend/app/api/v1/analytics.py:1814:        # legacy ``?manager=<label>`` path.
backend/app/api/v1/analytics.py:2416:        # Считаем по каноническому коду (employed / employment_pending / …), не по legacy-меткам.
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:13:from backend.app.services.document_catalog import normalize_doc_type
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:36:    non_overridable_doc_types_extra: List[str]
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:37:    effective_non_overridable_doc_types: List[str]
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:46:    non_overridable_doc_types_extra: Optional[List[str]] = None
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:57:        if k == "non_overridable_doc_types_extra":
backend/app/api/v1/settings/hiring_pipeline_gates_impl.py:61:                c = normalize_doc_type(str(item))
backend/app/api/v1/vacancies/rules.py:67:    so legacy aliases (``paused`` → ``on_hold``) and casing/whitespace noise
backend/app/api/v1/vacancies/rules.py:71:    The legacy ``archived`` alias normalises to ``archived`` (passthrough)
backend/app/api/v1/settings/communications.py:125:    fallbackToManual: bool = True
backend/app/api/v1/settings/communications.py:279:            "fallbackToManual": True,
backend/app/api/v1/vacancies/schemas.py:79:    # the row in the database still holds a legacy alias (`paused`). The
backend/app/api/v1/vacancies/schemas.py:124:    # points so legacy clients sending `state=paused` or `stage=paused`
backend/app/api/v1/vacancies/service.py:186:            # status. Treat the legacy alias as "closed + is_archived=True"
backend/app/api/v1/vacancies/service.py:258:                    "paused",  # legacy alias, see Stage A
backend/app/api/v1/settings/billing/schemas.py:148:    # Legacy field name (API compat): whole currency units for monthly list price (§2.16).
backend/app/api/v1/settings/billing/schemas.py:231:    ``checkout_ready`` is a legacy alias of ``effect_ready`` for API consumers.
backend/app/api/v1/utils/own_company.py:21:    db: AsyncSession, *, tenant_id: str, fallback_name: str = "My company"
backend/app/api/v1/utils/own_company.py:34:    name = tenant_row.scalar_one_or_none() or fallback_name
backend/app/api/v1/utils/own_company.py:35:    obj = OwnCompany(tenant_id=tenant_id, name=str(name).strip() or fallback_name)
backend/app/api/v1/settings/billing/_helpers/plans.py:240:    """Yearly Stripe Price id only (no fallback to monthly)."""
backend/app/api/v1/settings/billing/_helpers/plans.py:368:    # monthly_price_usd: legacy key — whole EUR units (§2.16 list prices), not USD.
backend/app/api/v1/settings/billing/_helpers/state.py:13:* **Slots writer** — ``_set_extra_operating_slots`` (normalises legacy keys
backend/app/api/v1/settings/billing/_helpers/state.py:110:    for legacy_key in ("additional_operating_company_slots", "operating_company_addon_slots"):
backend/app/api/v1/settings/billing/_helpers/state.py:111:        if legacy_key in updated:
backend/app/api/v1/settings/billing/_helpers/state.py:112:            del updated[legacy_key]
backend/app/api/scan_stub.py:57:    fallback_shape: Tuple[int, int],
backend/app/api/scan_stub.py:78:    h, w = fallback_shape
backend/app/api/v1/candidates/helpers.py:161:    """Надёжно приводим значение из БД к dict (поддержка legacy-строк)."""
backend/app/api/v1/candidates/router.py:321:        "notes": getattr(c, "note", None),  # alias for legacy consumers
backend/app/api/v1/candidates/router.py:658:            "Legacy filter name for the candidate assignee user id. "
backend/app/api/v1/candidates/router.py:815:    # Row-level state: ``Candidate.status`` only — never mixed into ``stages`` (legacy quirk removed).
backend/app/api/v1/candidates/router.py:877:        filters["manager_id"] = mid  # compatibility with legacy consumers
backend/app/api/v1/candidates/router.py:1186:            # very defensive fallback: assume last is vacancy
backend/app/api/v1/candidates/router.py:1242:            # Вакансия: человекочитаемое название, fallback to company name
backend/app/api/v1/candidates/router.py:1284:                "notes": getattr(c, "note", None),  # alias for legacy consumers
backend/app/api/v1/candidates/router.py:1497:            "Legacy filter name for the candidate assignee user id. "
backend/app/api/v1/candidates/router.py:1563:    # legacy ``manager_id`` names; the OR on ``Candidate.manager`` /
backend/app/api/v1/candidates/router.py:2165:    """Map ORM row → API; tolerate legacy NULL/odd JSON so list endpoint does not 500."""
backend/app/api/v1/candidates/router.py:2364:        candidate_notifications.get_document_display_name(getattr(d, "doc_type", None) or "")
backend/app/api/v1/candidates/router.py:2524:        #   * ``manager``: legacy DB column (shadow-written in lock-step).
backend/app/api/v1/candidates/router.py:2525:        #   * ``manager_id``: legacy frontend alias, mapped to ``manager``
backend/app/api/v1/candidates/router.py:2626:            # the same billing / side-effect gate as the legacy names.
backend/app/api/v1/candidates/repo.py:110:        # trust frontend to send ISO; fallback to first 10 chars
backend/app/api/v1/candidates/repo.py:515:        # legacy rows (where bulk-set-manager wrote only to ``manager``)
backend/app/api/v1/candidates/repo.py:679:            else:  # fallback (e.g. SQLite dev env)
backend/app/api/v1/candidates/repo.py:700:            else:  # fallback (e.g. SQLite dev env)
backend/app/api/v1/candidates/pipeline_overrides_api.py:38:    doc_type_code: str = Field(min_length=1, max_length=128)
backend/app/api/v1/candidates/pipeline_overrides_api.py:55:        "invalid_doc_type": (400, "invalid_doc_type"),
backend/app/api/v1/candidates/pipeline_overrides_api.py:56:        "doc_type_not_overridable": (400, "doc_type_not_overridable"),
backend/app/api/v1/candidates/pipeline_overrides_api.py:61:        "pending_exists": (409, "pending_override_exists_for_doc_type"),
backend/app/api/v1/candidates/pipeline_overrides_api.py:146:            doc_type_code=body.doc_type_code,
backend/app/api/v1/candidates/pipeline_overrides_api.py:162:            "doc_type_code": created["doc_type_code"],
backend/app/api/v1/candidates/pipeline_overrides_api.py:225:            "doc_type_code": updated["doc_type_code"],
backend/app/api/v1/candidates/pipeline_overrides_api.py:285:        payload={"override_id": updated["id"], "doc_type_code": updated["doc_type_code"]},
backend/app/api/v1/candidates/pipeline_overrides_api.py:343:        payload={"override_id": updated["id"], "doc_type_code": updated["doc_type_code"]},
backend/app/api/v1/candidates/schemas.py:204:    # alongside the legacy ``manager*`` fields. The runtime payload built
backend/app/api/v1/candidates/schemas.py:277:        # pull extra once for fallbacks
backend/app/api/v1/candidates/schemas.py:280:        def _fallback(name: str, current: Any) -> Any:
backend/app/api/v1/candidates/schemas.py:287:        country_code_val = _fallback("country_code", getattr(c, "country_code", None))
backend/app/api/v1/candidates/schemas.py:288:        city_val = _fallback("city", getattr(c, "city", None))
backend/app/api/v1/candidates/schemas.py:289:        address_val = _fallback("address", getattr(c, "address", None))
backend/app/api/v1/candidates/pipeline_overrides_service.py:10:from backend.app.services.document_catalog import normalize_doc_type
backend/app/api/v1/candidates/pipeline_overrides_service.py:31:        "doc_type_code": row.doc_type_code,
backend/app/api/v1/candidates/pipeline_overrides_service.py:68:    doc_type_code: str,
backend/app/api/v1/candidates/pipeline_overrides_service.py:77:                CandidatePipelineOverride.doc_type_code == doc_type_code,
backend/app/api/v1/candidates/pipeline_overrides_service.py:91:    doc_type_code: str,
backend/app/api/v1/candidates/pipeline_overrides_service.py:95:    code = normalize_doc_type(doc_type_code)
backend/app/api/v1/candidates/pipeline_overrides_service.py:97:        raise ValueError("invalid_doc_type")
backend/app/api/v1/candidates/pipeline_overrides_service.py:99:    if code in gates.effective_non_overridable_doc_types():
backend/app/api/v1/candidates/pipeline_overrides_service.py:100:        raise ValueError("doc_type_not_overridable")
backend/app/api/v1/candidates/pipeline_overrides_service.py:110:    pending = await _pending_for_doc(db, tenant_id=tenant_id, candidate_id=candidate_id, doc_type_code=code)
backend/app/api/v1/candidates/pipeline_overrides_service.py:117:        doc_type_code=code,
backend/app/api/v1/candidates/pipeline_overrides_service.py:261:        select(CandidatePipelineOverride.doc_type_code).where(
backend/app/api/v1/candidates/pipeline_overrides_service.py:280:        select(CandidatePipelineOverride.doc_type_code).where(
backend/app/api/v1/reminders_v2.py:245:    # legacy `patchCommunicationPlannerEvent({ status, kind, linked_*_id,
backend/app/api/v1/candidates/service.py:95:    """Return current UTC timestamp without tzinfo for legacy naive columns."""
backend/app/api/v1/candidates/service.py:116:    """Compatibility helper for legacy consumers that still build owner doc context."""
backend/app/api/v1/candidates/service.py:532:        # as a user row would pass validation here (legacy behaviour)
backend/app/api/v1/candidates/service.py:662:    # and the latter is a legacy UX hint. When no assignment ran we fall
backend/app/api/v1/candidates/service.py:979:            # Legacy behaviour: empty ``manager`` string was a no-op (not an
backend/app/api/v1/candidate_profiles.py:227:    # Agreements (legacy + new)
backend/app/api/v1/candidate_profiles.py:369:    # Fallback for old profiles without explicit required/optional lists.
backend/app/api/v1/candidate_profiles.py:461:    # 3) Fallback default profile for tenant
backend/app/api/v1/candidate_profiles.py:613:            # Fallback per-tenant with ORM
backend/app/api/v1/document_merge/router.py:50:    doc_type: str
backend/app/api/v1/document_merge/router.py:66:    doc_type: str = Field(default="additional_document", max_length=128)
backend/app/api/v1/document_merge/router.py:79:    doc_type: Optional[str] = Field(default=None, max_length=128)
backend/app/api/v1/document_merge/router.py:111:        doc_type=row.doc_type,
backend/app/api/v1/legal_documents.py:18:from backend.app.legal.billing_terms_templates_v1 import ALL_LEGAL_DOC_TYPES, default_billing_template_items
backend/app/api/v1/legal_documents.py:49:        if s not in ALL_LEGAL_DOC_TYPES:
backend/app/api/v1/schemas_children.py:12:    doc_type: str
backend/app/api/v1/schemas_children.py:20:    doc_type: Optional[str] = None


## 5) Classification

### Allowed infra
1. `backend/app/services/reference_service_facade.py` (boundary service).
2. `backend/app/services/document_applicability_resolver.py` (core resolver internals).
3. `backend/app/services/document_type_runtime_resolver.py` (core resolver internals + fallback).
4. `backend/app/services/document_reference_sync.py` (sync/backfill).

### Temporary compatibility
1. `backend/app/services/document_type_runtime_resolver.py` legacy fallback branches.
2. `backend/app/services/workforce_operational_profile.py` compatibility projections from decision contract.
3. legacy `doc_type` usage in compatibility-oriented paths pending facade cutover.

### Must-cutover consumers
1. `backend/app/services/workforce_eligibility_resolver.py`
: directly calls `DocumentApplicabilityResolver` and `DocumentTypeRuntimeResolver`.
2. `backend/app/services/hr_expected_documents_resolver.py`
: directly reads reference models for expected-document shaping.
3. `backend/app/services/hr_documents_queue.py` (and dependent HR document read paths)
: ensure applicability/reference reads route via facade.

### Violations (enforcement definition)
1. New direct resolver/table usage outside allowlist.
2. New module-local `doc_type` mapping for applicability/metadata decisions.
3. New module-local rule engines duplicating reference/applicability logic.

## 6) Allowlist (owner + milestone)

1. `backend/app/services/document_applicability_resolver.py`
- owner: platform-reference
- milestone: keep (core internal)

2. `backend/app/services/document_type_runtime_resolver.py`
- owner: platform-reference
- milestone: reduce legacy fallback in REF-5+

3. `backend/app/services/document_reference_sync.py`
- owner: platform-reference
- milestone: keep until legacy-column removal phase

4. `backend/app/services/workforce_eligibility_resolver.py` (temporary direct resolver coupling)
- owner: platform-runtime
- milestone: cutover to facade in next consumer wave

## 7) Next Consumer Recommendation

Recommended next cutover consumer:
1. `backend/app/services/workforce_eligibility_resolver.py`

Reason:
1. highest coupling/centrality in current runtime;
2. removing its direct resolver access gives maximum boundary hardening effect.
