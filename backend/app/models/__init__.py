from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Iterable

_DOCUMENTS_DISABLED = bool(int(os.environ.get("DOCUMENTS_DISABLED", "0")))

# База
from ..db.base import Base  # noqa: F401


def _register_aliases(module_name: str, module: ModuleType) -> None:
    """Ensure both `app.models.<name>` and `backend.app.models.<name>` map to the same module."""
    aliases: Iterable[str] = (
        f"app.models.{module_name}",
        f"backend.app.models.{module_name}",
    )
    for alias in aliases:
        sys.modules.setdefault(alias, module)


def _load_model_module(module_name: str) -> ModuleType:
    """
    Import a model submodule, reusing whichever alias (app.* or backend.app.*) is already loaded
    to avoid triggering SQLAlchemy metadata re-definitions.
    """
    candidates = (
        f"backend.app.models.{module_name}",
        f"app.models.{module_name}",
    )
    for idx, candidate in enumerate(candidates):
        module = sys.modules.get(candidate)
        if module is not None:
            # Ensure the alternative alias points to the same module object.
            other = candidates[1 - idx]
            sys.modules.setdefault(other, module)
            return module

    module = importlib.import_module(f".{module_name}", __name__)
    _register_aliases(module_name, module)
    return module


# Базовые модели (сначала Company и Vacancy, затем Candidate)
_tenant_mod = _load_model_module("tenant")
Tenant = _tenant_mod.Tenant  # type: ignore[attr-defined]
TenantLink = _tenant_mod.TenantLink  # type: ignore[attr-defined]
OwnCompany = _load_model_module("own_company").OwnCompany  # type: ignore[attr-defined]
ClientCompany = _load_model_module("client_company").ClientCompany  # type: ignore[attr-defined]
Company = _load_model_module("company").Company  # type: ignore[attr-defined]
Vacancy = _load_model_module("vacancy").Vacancy  # type: ignore[attr-defined]
VacancyRecruiter = _load_model_module("vacancy_recruiter").VacancyRecruiter  # type: ignore[attr-defined]
lead_module = _load_model_module("lead")
Lead = lead_module.Lead  # type: ignore[attr-defined]
MetaAdsMap = lead_module.MetaAdsMap  # type: ignore[attr-defined]
MetaLeadCredential = lead_module.MetaLeadCredential  # type: ignore[attr-defined]
MetaLeadSettings = lead_module.MetaLeadSettings  # type: ignore[attr-defined]
MetaOAuthPending = lead_module.MetaOAuthPending  # type: ignore[attr-defined]
lead_import_module = _load_model_module("lead_import_job")
LeadImportJob = lead_import_module.LeadImportJob  # type: ignore[attr-defined]
LeadImportJobStatus = lead_import_module.LeadImportJobStatus  # type: ignore[attr-defined]
Candidate = _load_model_module("candidate").Candidate  # type: ignore[attr-defined]
CandidateEmployment = _load_model_module("candidate_employment").CandidateEmployment  # type: ignore[attr-defined]
CandidateConsent = _load_model_module("candidate_consent").CandidateConsent  # type: ignore[attr-defined]
Stage = _load_model_module("stage").Stage  # type: ignore[attr-defined]
MagicLink = _load_model_module("magic_link").MagicLink  # type: ignore[attr-defined]

# Universal Funnel model
funnel_module = _load_model_module("funnel")
Funnel = funnel_module.Funnel  # type: ignore[attr-defined]
FunnelStage = funnel_module.FunnelStage  # type: ignore[attr-defined]

# История стадий
CandidateStageHistory = _load_model_module("candidate_stage_history").CandidateStageHistory  # type: ignore[attr-defined]

RecruitmentApplication = _load_model_module("recruitment_application").RecruitmentApplication  # type: ignore[attr-defined]



# Документы (новые модели из модуля documents)
# ВНИМАНИЕ: не импортируем app.modules.documents.models (во избежание циклов)!
# Грузим конкретные ORM-модули напрямую и регистрируем алиасы.

# ядро таблиц документов
Document              = _load_model_module("document").Document  # type: ignore[attr-defined]
DocumentType          = _load_model_module("document_type").DocumentType  # type: ignore[attr-defined]
DocumentTemplate      = _load_model_module("document_template").DocumentTemplate  # type: ignore[attr-defined]
DocumentCheck         = _load_model_module("document_check").DocumentCheck  # type: ignore[attr-defined]
ScanSession          = _load_model_module("scan_session").ScanSession  # type: ignore[attr-defined]
ScanPage             = _load_model_module("scan_page").ScanPage  # type: ignore[attr-defined]

# ruleset/версии
_document_ruleset_mod = _load_model_module("document_ruleset")
DocumentRulesetVersion = _document_ruleset_mod.DocumentRulesetVersion  # type: ignore[attr-defined]
DocumentRulesetUsage   = _document_ruleset_mod.DocumentRulesetUsage    # type: ignore[attr-defined]
DocumentRulesetDiff    = _document_ruleset_mod.DocumentRulesetDiff     # type: ignore[attr-defined]

# отчёты/метрики/батчи
_document_reporting_mod = _load_model_module("document_reporting")
BulkOperation         = _document_reporting_mod.BulkOperation          # type: ignore[attr-defined]
BulkOperationItem     = _document_reporting_mod.BulkOperationItem      # type: ignore[attr-defined]
DocumentComplianceLog = _document_reporting_mod.DocumentComplianceLog  # type: ignore[attr-defined]
DocumentMetricsDaily  = _document_reporting_mod.DocumentMetricsDaily   # type: ignore[attr-defined]
ReportExport          = _document_reporting_mod.ReportExport           # type: ignore[attr-defined]
ReportSummary         = _document_reporting_mod.ReportSummary          # type: ignore[attr-defined]

# алиасы для «app.models.<name>» и «backend.app.models.<name>»
import sys as _sys
_register_aliases("document", _sys.modules[Document.__module__])
_register_aliases("document_type", _sys.modules[DocumentType.__module__])
_register_aliases("document_template", _sys.modules[DocumentTemplate.__module__])
_register_aliases("document_check", _sys.modules[DocumentCheck.__module__])
_register_aliases("scan_session", _sys.modules[ScanSession.__module__])
_register_aliases("scan_page", _sys.modules[ScanPage.__module__])
_register_aliases("document_ruleset", _sys.modules[DocumentRulesetVersion.__module__])
_register_aliases("document_reporting", _sys.modules[BulkOperation.__module__])

# Phase 1.3 / Phase 2.1 (ADR-012): canonical Activity / ActivityEvent /
# Notification ORMs — these MUST be loaded through ``_load_model_module``
# before any code can do ``from backend.app.models.activity import …``,
# otherwise the legacy ``reminder.py`` / ``reminder_event.py`` /
# ``user_notification.py`` re-export modules pull them in via a relative
# ``from .activity import …`` that registers them under the
# ``app.models.activity`` alias only, leaving ``backend.app.models.activity``
# absent from ``sys.modules``. Any later import via the
# ``backend.app.models.X`` path then re-executes the file under a second
# module identity and SQLAlchemy raises "Table 'activities' is already
# defined for this MetaData instance" (Docker reproduces this every
# startup because the ``app/__init__.py`` aliasing layer wires
# ``backend.app`` to ``app`` but does NOT wire each submodule).
_activity_mod = _load_model_module("activity")
Activity = _activity_mod.Activity  # type: ignore[attr-defined]
ActivityStatus = _activity_mod.ActivityStatus  # type: ignore[attr-defined]
ActivityEvent = _load_model_module("activity_event").ActivityEvent  # type: ignore[attr-defined]
Notification = _load_model_module("notification").Notification  # type: ignore[attr-defined]

Reminder = _load_model_module("reminder").Reminder  # type: ignore[attr-defined]
ReminderEvent = _load_model_module("reminder_event").ReminderEvent  # type: ignore[attr-defined]
UserNotification = _load_model_module("user_notification").UserNotification  # type: ignore[attr-defined]
AutomationRule = _load_model_module("automation_rule").AutomationRule  # type: ignore[attr-defined]
TenantLeadForm = _load_model_module("tenant_lead_form").TenantLeadForm  # type: ignore[attr-defined]

# Услуги (на кандидате)
CandidateService = _load_model_module("service").CandidateService  # type: ignore[attr-defined]
additional_service_module = _load_model_module("additional_service")
Service = additional_service_module.Service  # type: ignore[attr-defined]
ServiceAttachment = additional_service_module.ServiceAttachment  # type: ignore[attr-defined]
ServiceItem = additional_service_module.ServiceItem  # type: ignore[attr-defined]
ServiceOrder = additional_service_module.ServiceOrder  # type: ignore[attr-defined]
ServiceSchedule = additional_service_module.ServiceSchedule  # type: ignore[attr-defined]

try:
    candidate_children_module = _load_model_module("candidate_children")
    CandidatePermit = candidate_children_module.CandidatePermit  # type: ignore[attr-defined]
    CandidateVisa = candidate_children_module.CandidateVisa  # type: ignore[attr-defined]
    CandidateTask = candidate_children_module.CandidateTask  # type: ignore[attr-defined]
except Exception:
    if not _DOCUMENTS_DISABLED:
        raise
    CandidatePermit = CandidateVisa = CandidateTask = None  # type: ignore[assignment]

# Пользователь и RBAC
User = _load_model_module("user").User  # type: ignore[attr-defined]
session_module = _load_model_module("session")
AuthRefreshToken = session_module.AuthRefreshToken  # type: ignore[attr-defined]
UserSession = session_module.UserSession  # type: ignore[attr-defined]
audit_module = _load_model_module("audit")
UserAuditLog = audit_module.UserAuditLog  # type: ignore[attr-defined]
ActivityLog = audit_module.ActivityLog  # type: ignore[attr-defined]
UserInvite = _load_model_module("invite").UserInvite  # type: ignore[attr-defined]
UserCompanyAccess = _load_model_module("access").UserCompanyAccess  # type: ignore[attr-defined]
CandidateDeleteRequest = _load_model_module("candidate_delete_request").CandidateDeleteRequest  # type: ignore[attr-defined]

# Invoicing models
Invoice = _load_model_module("invoice").Invoice  # type: ignore[attr-defined]
InvoiceItem = _load_model_module("invoice").InvoiceItem  # type: ignore[attr-defined]
Payment = _load_model_module("invoice").Payment  # type: ignore[attr-defined]
Refund = _load_model_module("invoice").Refund  # type: ignore[attr-defined]
StripeWebhookEventLog = _load_model_module("stripe_webhook_event").StripeWebhookEventLog  # type: ignore[attr-defined]

# Document policies & custom fields
DocumentPolicy = _load_model_module("document_policy").DocumentPolicy  # type: ignore[attr-defined]
document_policy_module = _load_model_module("document_policy")
DocumentPolicyScope = document_policy_module.DocumentPolicyScope  # type: ignore[attr-defined]
RequirementLevel = document_policy_module.RequirementLevel  # type: ignore[attr-defined]
RequirementTypeDefinition = _load_model_module("requirement_type").RequirementTypeDefinition  # type: ignore[attr-defined]
Gate = _load_model_module("gate").Gate  # type: ignore[attr-defined]
CandidateProfile = _load_model_module("candidate_profile").CandidateProfile  # type: ignore[attr-defined]
candidate_profile_history_module = _load_model_module("candidate_profile_history")
CandidateProfileHistory = candidate_profile_history_module.CandidateProfileHistory  # type: ignore[attr-defined]
ProcessTemplate = _load_model_module("process_template").ProcessTemplate  # type: ignore[attr-defined]

custom_field_module = _load_model_module("custom_field")
CustomFieldDefinition = custom_field_module.CustomFieldDefinition  # type: ignore[attr-defined]
CustomFieldValue = custom_field_module.CustomFieldValue  # type: ignore[attr-defined]
CustomFieldScope = custom_field_module.CustomFieldScope  # type: ignore[attr-defined]
CustomFieldEntityType = custom_field_module.CustomFieldEntityType  # type: ignore[attr-defined]
CustomFieldType = custom_field_module.CustomFieldType  # type: ignore[attr-defined]

# RODO / Legal documents
LegalDocument = _load_model_module("legal_document").LegalDocument  # type: ignore[attr-defined]
RodoNotification = _load_model_module("rodo_notification").RodoNotification  # type: ignore[attr-defined]

# Contact attempts
ContactAttempt = _load_model_module("contact_attempt").ContactAttempt  # type: ignore[attr-defined]
FinalNoContactNotification = _load_model_module("final_no_contact_notification").FinalNoContactNotification  # type: ignore[attr-defined]

# Handoff
CandidateHandoff = _load_model_module("candidate_handoff").CandidateHandoff  # type: ignore[attr-defined]
CandidateHandoffSnapshot = _load_model_module(
    "candidate_handoff_snapshot"
).CandidateHandoffSnapshot  # type: ignore[attr-defined]

# Pipeline document overrides (recruiter request / manager approval)
CandidatePipelineOverride = _load_model_module(
    "candidate_pipeline_override"
).CandidatePipelineOverride  # type: ignore[attr-defined]

# Tenant email (SMTP)
TenantEmailConfig = _load_model_module("tenant_email_config").TenantEmailConfig  # type: ignore[attr-defined]

# Communications hub (omnichannel threads/messages/accounts)
communication_module = _load_model_module("communication")
CommunicationThread = communication_module.CommunicationThread  # type: ignore[attr-defined]
CommunicationMessage = communication_module.CommunicationMessage  # type: ignore[attr-defined]
CommunicationChannelAccount = communication_module.CommunicationChannelAccount  # type: ignore[attr-defined]

# Risk intelligence (hourly aggregates + shadow cohort rows)
_risk_intel_mod = _load_model_module("risk_intel")
RiskIntelTenantHourly = _risk_intel_mod.RiskIntelTenantHourly  # type: ignore[attr-defined]
RiskIntelEntityShadow = _risk_intel_mod.RiskIntelEntityShadow  # type: ignore[attr-defined]

# Password reset tokens (self-service)
PasswordResetToken = _load_model_module("password_reset_token").PasswordResetToken  # type: ignore[attr-defined]

# Countries (ISO2 reference)
Country = _load_model_module("country").Country  # type: ignore[attr-defined]

# Candidate recruiter assignee audit (Phase 2.6.G-5)
CandidateAssigneeHistory = _load_model_module("candidate_assignee_history").CandidateAssigneeHistory  # type: ignore[attr-defined]

# Workforce HR (employee root + satellite profiles)
WorkforceEmployee = _load_model_module("workforce_employee").WorkforceEmployee  # type: ignore[attr-defined]
WorkforceEmployment = _load_model_module("workforce_employment").WorkforceEmployment  # type: ignore[attr-defined]
WorkforcePayrollProfile = _load_model_module("workforce_payroll_profile").WorkforcePayrollProfile  # type: ignore[attr-defined]
WorkforceZusProfile = _load_model_module("workforce_zus_profile").WorkforceZusProfile  # type: ignore[attr-defined]
WorkforceAbsence = _load_model_module("workforce_absence").WorkforceAbsence  # type: ignore[attr-defined]
WorkforceLeaveRequest = _load_model_module("workforce_leave_request").WorkforceLeaveRequest  # type: ignore[attr-defined]
WorkforceOnboardingTask = _load_model_module("workforce_onboarding_task").WorkforceOnboardingTask  # type: ignore[attr-defined]
WorkforceTaxProfile = _load_model_module("workforce_tax_profile").WorkforceTaxProfile  # type: ignore[attr-defined]
WorkforceInsuranceProfile = _load_model_module("workforce_insurance_profile").WorkforceInsuranceProfile  # type: ignore[attr-defined]
WorkforceHrDocumentContext = _load_model_module("workforce_hr_document_context").WorkforceHrDocumentContext  # type: ignore[attr-defined]
WorkforceComplianceState = _load_model_module("workforce_compliance_state").WorkforceComplianceState  # type: ignore[attr-defined]
WorkforceZusWorkspaceTask = _load_model_module("workforce_zus_workspace_task").WorkforceZusWorkspaceTask  # type: ignore[attr-defined]
WorkforceWorkEligibilityProfile = _load_model_module(
    "workforce_work_eligibility_profile"
).WorkforceWorkEligibilityProfile  # type: ignore[attr-defined]
WorkPermitSubmissionChannel = _load_model_module(
    "workforce_work_eligibility_profile"
).WorkPermitSubmissionChannel  # type: ignore[attr-defined]
WorkforceWorkEligibilityPaymentRequirement = _load_model_module(
    "workforce_work_eligibility_payment_requirement"
).WorkforceWorkEligibilityPaymentRequirement  # type: ignore[attr-defined]
WorkforceHrReview = _load_model_module("workforce_hr_review").WorkforceHrReview  # type: ignore[attr-defined]

# Merge-document templates and generation logs
MergeDocumentTemplate = _load_model_module("merge_document_template").MergeDocumentTemplate  # type: ignore[attr-defined]
MergeDocumentGenerationLog = _load_model_module(
    "merge_document_generation_log"
).MergeDocumentGenerationLog  # type: ignore[attr-defined]

# Fleet (transport operations)
FleetOperatingLine = _load_model_module("fleet_operating_line").FleetOperatingLine  # type: ignore[attr-defined]
FleetVehicle = _load_model_module("fleet_vehicle").FleetVehicle  # type: ignore[attr-defined]
FleetTrailer = _load_model_module("fleet_trailer").FleetTrailer  # type: ignore[attr-defined]
FleetDriver = _load_model_module("fleet_driver").FleetDriver  # type: ignore[attr-defined]

__all__ = [
    "Base",
    "Candidate",
    "CandidateAssigneeHistory",
    "Document",
    "DocumentType",
    "DocumentCheck",
    "DocumentRulesetVersion",
    "DocumentRulesetUsage",
    "DocumentRulesetDiff",
    "ScanSession",
    "ScanPage",
    "DocumentComplianceLog",
    "DocumentMetricsDaily",
    "DocumentTemplate",
    "ReportSummary",
    "ReportExport",
    "BulkOperation",
    "BulkOperationItem",
    "CandidateStageHistory",
    "CandidateProfileHistory",
    "CandidateService",
    "CandidateEmployment",
    "CandidateConsent",
    "Service",
    "ServiceOrder",
    "ServiceItem",
    "ServiceSchedule",
    "ServiceAttachment",
    "CandidatePermit",
    "CandidateVisa",
    "CandidateTask",
    "User",
    "UserCompanyAccess",
    "VacancyRecruiter",
    "Lead",
    "MetaAdsMap",
    "MetaLeadCredential",
    "MetaLeadSettings",
    "MetaOAuthPending",
    "LeadImportJob",
    "LeadImportJobStatus",
    "RecruitmentApplication",
    "CandidateDeleteRequest",
    "UserInvite",
    "UserAuditLog",
    "ActivityLog",
    "AuthRefreshToken",
    "UserSession",
    "Tenant",
    "TenantLink",
    "Company",
    "Vacancy",
    "Activity",
    "ActivityEvent",
    "ActivityStatus",
    "Notification",
    "Reminder",
    "ReminderEvent",
    "UserNotification",
    "Stage",
    "MagicLink",
    "MergeDocumentGenerationLog",
    "MergeDocumentTemplate",
    "FleetDriver",
    "FleetOperatingLine",
    "FleetTrailer",
    "FleetVehicle",
    "Funnel",
    "FunnelStage",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "Refund",
    "StripeWebhookEventLog",
    "DocumentPolicy",
    "DocumentPolicyScope",
    "RequirementLevel",
    "RequirementTypeDefinition",
    "Gate",
    "CandidateProfile",
    "ProcessTemplate",
    "CustomFieldDefinition",
    "CustomFieldValue",
    "CustomFieldScope",
    "CustomFieldEntityType",
    "CustomFieldType",
    "LegalDocument",
    "RodoNotification",
    "ContactAttempt",
    "FinalNoContactNotification",
    "CandidateHandoff",
    "CandidateHandoffSnapshot",
    "CandidatePipelineOverride",
    "TenantEmailConfig",
    "CommunicationThread",
    "CommunicationMessage",
    "CommunicationChannelAccount",
    "RiskIntelTenantHourly",
    "RiskIntelEntityShadow",
    "Country",
    "WorkforceAbsence",
    "WorkforceEmployee",
    "WorkforceEmployment",
    "WorkforceLeaveRequest",
    "WorkforceOnboardingTask",
    "WorkforcePayrollProfile",
    "WorkforceZusProfile",
    "WorkforceTaxProfile",
    "WorkforceInsuranceProfile",
    "WorkforceHrDocumentContext",
    "WorkforceComplianceState",
    "WorkforceWorkEligibilityProfile",
    "WorkPermitSubmissionChannel",
    "WorkforceWorkEligibilityPaymentRequirement",
    "WorkforceHrReview",
]
