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
Tenant = _load_model_module("tenant").Tenant  # type: ignore[attr-defined]
TenantEmailConfig = _load_model_module("tenant_email_config").TenantEmailConfig  # type: ignore[attr-defined]
Company = _load_model_module("company").Company  # type: ignore[attr-defined]
ClientAccount = _load_model_module("client_account").ClientAccount  # type: ignore[attr-defined]
Vacancy = _load_model_module("vacancy").Vacancy  # type: ignore[attr-defined]
VacancyRecruiter = _load_model_module("vacancy_recruiter").VacancyRecruiter  # type: ignore[attr-defined]
lead_module = _load_model_module("lead")
Lead = lead_module.Lead  # type: ignore[attr-defined]
MetaAdsMap = lead_module.MetaAdsMap  # type: ignore[attr-defined]
MetaLeadCredential = lead_module.MetaLeadCredential  # type: ignore[attr-defined]
MetaLeadSettings = lead_module.MetaLeadSettings  # type: ignore[attr-defined]
MetaLeadFormMapping = lead_module.MetaLeadFormMapping  # type: ignore[attr-defined]
MetaFormRoute = lead_module.MetaFormRoute  # type: ignore[attr-defined]
MetaOAuthPending = lead_module.MetaOAuthPending  # type: ignore[attr-defined]
intake_routing_module = _load_model_module("intake_routing")
IntakeSourceProfile = intake_routing_module.IntakeSourceProfile  # type: ignore[attr-defined]
IntakeSourceBinding = intake_routing_module.IntakeSourceBinding  # type: ignore[attr-defined]
lead_import_module = _load_model_module("lead_import_job")
LeadImportJob = lead_import_module.LeadImportJob  # type: ignore[attr-defined]
LeadImportJobStatus = lead_import_module.LeadImportJobStatus  # type: ignore[attr-defined]
TenantLeadForm = _load_model_module("tenant_lead_form").TenantLeadForm  # type: ignore[attr-defined]
LeadQuestionnaireInvite = _load_model_module("lead_questionnaire_invite").LeadQuestionnaireInvite  # type: ignore[attr-defined]
CommunicationDelivery = _load_model_module("communication_delivery").CommunicationDelivery  # type: ignore[attr-defined]
CommunicationDeliveryAttempt = _load_model_module(
    "communication_delivery_attempt"
).CommunicationDeliveryAttempt  # type: ignore[attr-defined]
CommunicationDeliveryCallbackUnresolved = _load_model_module(
    "communication_delivery_callback_unresolved"
).CommunicationDeliveryCallbackUnresolved  # type: ignore[attr-defined]
Candidate = _load_model_module("candidate").Candidate  # type: ignore[attr-defined]
RecruitmentApplication = _load_model_module("recruitment_application").RecruitmentApplication  # type: ignore[attr-defined]
SalesInquiry = _load_model_module("sales_inquiry").SalesInquiry  # type: ignore[attr-defined]
FlightDispatchLedger = _load_model_module("flight_dispatch_ledger").FlightDispatchLedger  # type: ignore[attr-defined]
CandidateEmployment = _load_model_module("candidate_employment").CandidateEmployment  # type: ignore[attr-defined]
CandidateConsent = _load_model_module("candidate_consent").CandidateConsent  # type: ignore[attr-defined]
CandidateHandoff = _load_model_module("candidate_handoff").CandidateHandoff  # type: ignore[attr-defined]
candidate_evidence_module = _load_model_module("candidate_evidence")
CandidateEvidence = candidate_evidence_module.CandidateEvidence  # type: ignore[attr-defined]
CandidateEvidenceDocument = candidate_evidence_module.CandidateEvidenceDocument  # type: ignore[attr-defined]
ContactAttempt = _load_model_module("contact_attempt").ContactAttempt  # type: ignore[attr-defined]
Stage = _load_model_module("stage").Stage  # type: ignore[attr-defined]
MagicLink = _load_model_module("magic_link").MagicLink  # type: ignore[attr-defined]
OwnCompany = _load_model_module("own_company").OwnCompany  # type: ignore[attr-defined]
WorkforceEmployee = _load_model_module("workforce_employee").WorkforceEmployee  # type: ignore[attr-defined]
WorkforceTaxProfile = _load_model_module("workforce_tax_profile").WorkforceTaxProfile  # type: ignore[attr-defined]
WorkforceInsuranceProfile = _load_model_module("workforce_insurance_profile").WorkforceInsuranceProfile  # type: ignore[attr-defined]
WorkforceComplianceState = _load_model_module("workforce_compliance_state").WorkforceComplianceState  # type: ignore[attr-defined]
WorkforceWorkEligibilityProfile = _load_model_module(
    "workforce_work_eligibility_profile"
).WorkforceWorkEligibilityProfile  # type: ignore[attr-defined]
WorkforceHrDocumentContext = _load_model_module("workforce_hr_document_context").WorkforceHrDocumentContext  # type: ignore[attr-defined]
WorkforceZusWorkspaceTask = _load_model_module("workforce_zus_workspace_task").WorkforceZusWorkspaceTask  # type: ignore[attr-defined]
WorkforceHrDocumentControlTask = _load_model_module("workforce_hr_document_control_task").WorkforceHrDocumentControlTask  # type: ignore[attr-defined]
WorkforceLifecycleEvent = _load_model_module("workforce_lifecycle_event").WorkforceLifecycleEvent  # type: ignore[attr-defined]
WorkforceEmployment = _load_model_module("workforce_employment").WorkforceEmployment  # type: ignore[attr-defined]
AutomationRule = _load_model_module("automation_rule").AutomationRule  # type: ignore[attr-defined]
campaign_module = _load_model_module("campaign")
Campaign = campaign_module.Campaign  # type: ignore[attr-defined]
CampaignRun = campaign_module.CampaignRun  # type: ignore[attr-defined]
CampaignTarget = campaign_module.CampaignTarget  # type: ignore[attr-defined]
CampaignRunForm = campaign_module.CampaignRunForm  # type: ignore[attr-defined]
CampaignRunIntakeSource = campaign_module.CampaignRunIntakeSource  # type: ignore[attr-defined]
FlightAdBinding = campaign_module.FlightAdBinding  # type: ignore[attr-defined]
CampaignResultAttribution = campaign_module.CampaignResultAttribution  # type: ignore[attr-defined]
CampaignOutcome = campaign_module.CampaignOutcome  # type: ignore[attr-defined]
CampaignOutcomeResultLink = campaign_module.CampaignOutcomeResultLink  # type: ignore[attr-defined]
CampaignFlightSpendEntry = campaign_module.CampaignFlightSpendEntry  # type: ignore[attr-defined]
CampaignResultQualification = campaign_module.CampaignResultQualification  # type: ignore[attr-defined]
AcquisitionActivityEvent = _load_model_module(
    "acquisition_activity_event"
).AcquisitionActivityEvent  # type: ignore[attr-defined]
funnel_module = _load_model_module("funnel")
Funnel = funnel_module.Funnel  # type: ignore[attr-defined]
FunnelStage = funnel_module.FunnelStage  # type: ignore[attr-defined]
pe_module = _load_model_module("process_engine")
PeSystemStage = pe_module.PeSystemStage  # type: ignore[attr-defined]
PeStageTemplate = pe_module.PeStageTemplate  # type: ignore[attr-defined]
PeProcessProfile = pe_module.PeProcessProfile  # type: ignore[attr-defined]
PePipelineTemplate = pe_module.PePipelineTemplate  # type: ignore[attr-defined]
PeTransitionRule = pe_module.PeTransitionRule  # type: ignore[attr-defined]
PeHandoffRule = pe_module.PeHandoffRule  # type: ignore[attr-defined]
PeFieldRequirement = pe_module.PeFieldRequirement  # type: ignore[attr-defined]
PeDocumentRequirement = pe_module.PeDocumentRequirement  # type: ignore[attr-defined]
PeOverrideRule = pe_module.PeOverrideRule  # type: ignore[attr-defined]
fr_module = _load_model_module("field_registry")
FrCanonicalField = fr_module.FrCanonicalField  # type: ignore[attr-defined]
FrCardLayoutProfile = fr_module.FrCardLayoutProfile  # type: ignore[attr-defined]
FrCardLayoutField = fr_module.FrCardLayoutField  # type: ignore[attr-defined]
ep_module = _load_model_module("entity_profile")
EpEntityProfile = ep_module.EpEntityProfile  # type: ignore[attr-defined]
EpEntityProfileField = ep_module.EpEntityProfileField  # type: ignore[attr-defined]
EpIntakePresentation = ep_module.EpIntakePresentation  # type: ignore[attr-defined]
module_registry_module = _load_model_module("module_registry")
ModuleRegistry = module_registry_module.ModuleRegistry  # type: ignore[attr-defined]
TenantModuleInstallation = module_registry_module.TenantModuleInstallation  # type: ignore[attr-defined]
ModuleCapability = module_registry_module.ModuleCapability  # type: ignore[attr-defined]
ModuleDependency = module_registry_module.ModuleDependency  # type: ignore[attr-defined]
MergeDocumentTemplate = _load_model_module("merge_document_template").MergeDocumentTemplate  # type: ignore[attr-defined]
MergeDocumentGenerationLog = _load_model_module("merge_document_generation_log").MergeDocumentGenerationLog  # type: ignore[attr-defined]

# История стадий
CandidateStageHistory = _load_model_module("candidate_stage_history").CandidateStageHistory  # type: ignore[attr-defined]
CandidateAssigneeHistory = _load_model_module("candidate_assignee_history").CandidateAssigneeHistory  # type: ignore[attr-defined]

CandidateProfile = _load_model_module("candidate_profile").CandidateProfile  # type: ignore[attr-defined]
candidate_profile_history_module = _load_model_module("candidate_profile_history")
CandidateProfileHistory = candidate_profile_history_module.CandidateProfileHistory  # type: ignore[attr-defined]


# Документы (новые модели из модуля documents)
# ВНИМАНИЕ: не импортируем app.modules.documents.models (во избежание циклов)!
# Грузим конкретные ORM-модули напрямую и регистрируем алиасы.

# ядро таблиц документов
Document              = _load_model_module("document").Document  # type: ignore[attr-defined]
DocumentType          = _load_model_module("document_type").DocumentType  # type: ignore[attr-defined]
ref_document_type_module = _load_model_module("ref_document_type")
RefDocumentType = ref_document_type_module.RefDocumentType  # type: ignore[attr-defined]
RefDocumentTypeI18n = ref_document_type_module.RefDocumentTypeI18n  # type: ignore[attr-defined]
RefDocumentTypeVersion = ref_document_type_module.RefDocumentTypeVersion  # type: ignore[attr-defined]
RefDocumentTypeCountryApplicability = ref_document_type_module.RefDocumentTypeCountryApplicability  # type: ignore[attr-defined]
RefDocumentTypeRequest = ref_document_type_module.RefDocumentTypeRequest  # type: ignore[attr-defined]
TenantDocumentTypeOverride = ref_document_type_module.TenantDocumentTypeOverride  # type: ignore[attr-defined]
RefPack = ref_document_type_module.RefPack  # type: ignore[attr-defined]
RefPackItem = ref_document_type_module.RefPackItem  # type: ignore[attr-defined]
RefPackRule = ref_document_type_module.RefPackRule  # type: ignore[attr-defined]
TenantDocumentPackEnablement = ref_document_type_module.TenantDocumentPackEnablement  # type: ignore[attr-defined]
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
_register_aliases("ref_document_type", _sys.modules[RefDocumentType.__module__])
_register_aliases("document_template", _sys.modules[DocumentTemplate.__module__])
_register_aliases("document_check", _sys.modules[DocumentCheck.__module__])
_register_aliases("scan_session", _sys.modules[ScanSession.__module__])
_register_aliases("scan_page", _sys.modules[ScanPage.__module__])
_register_aliases("document_ruleset", _sys.modules[DocumentRulesetVersion.__module__])
_register_aliases("document_reporting", _sys.modules[BulkOperation.__module__])

# Ensure canonical activity module aliases are registered before any direct
# imports like `backend.app.models.activity` occur in service modules.
_load_model_module("activity")
Reminder = _load_model_module("reminder").Reminder  # type: ignore[attr-defined]
UserNotification = _load_model_module("user_notification").UserNotification  # type: ignore[attr-defined]
CandidateProfile = _load_model_module("candidate_profile").CandidateProfile  # type: ignore[attr-defined]
CommunicationThread = _load_model_module("communication").CommunicationThread  # type: ignore[attr-defined]
CommunicationThreadResultLink = _load_model_module(
    "communication_thread_result_link"
).CommunicationThreadResultLink  # type: ignore[attr-defined]
CommunicationThreadEntityLink = _load_model_module(
    "communication_thread_entity_link"
).CommunicationThreadEntityLink  # type: ignore[attr-defined]
CommunicationInboundUnresolved = _load_model_module(
    "communication_inbound_unresolved"
).CommunicationInboundUnresolved  # type: ignore[attr-defined]
CommunicationThreadNextAction = _load_model_module(
    "communication_thread_next_action"
).CommunicationThreadNextAction  # type: ignore[attr-defined]
CommunicationThreadSlaEvent = _load_model_module(
    "communication_thread_sla_event"
).CommunicationThreadSlaEvent  # type: ignore[attr-defined]
_communication_template_module = _load_model_module("communication_template")
CommunicationTemplate = _communication_template_module.CommunicationTemplate  # type: ignore[attr-defined]
CommunicationTemplateVersion = _communication_template_module.CommunicationTemplateVersion  # type: ignore[attr-defined]
CommunicationTemplateVariable = _communication_template_module.CommunicationTemplateVariable  # type: ignore[attr-defined]
CommunicationTemplateChannelBinding = (
    _communication_template_module.CommunicationTemplateChannelBinding
)  # type: ignore[attr-defined]
CommunicationTemplateIntentBinding = (
    _communication_template_module.CommunicationTemplateIntentBinding
)  # type: ignore[attr-defined]
_communication_automation_module = _load_model_module("communication_automation")
CommunicationAutomationRule = _communication_automation_module.CommunicationAutomationRule  # type: ignore[attr-defined]
CommunicationAutomationRuleVersion = (
    _communication_automation_module.CommunicationAutomationRuleVersion
)  # type: ignore[attr-defined]
CommunicationAutomationTrigger = (
    _communication_automation_module.CommunicationAutomationTrigger
)  # type: ignore[attr-defined]
CommunicationAutomationDecision = (
    _communication_automation_module.CommunicationAutomationDecision
)  # type: ignore[attr-defined]
DocumentPolicy = _load_model_module("document_policy").DocumentPolicy  # type: ignore[attr-defined]

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

__all__ = [
    "Base",
    "Candidate",
    "RecruitmentApplication",
    "SalesInquiry",
    "FlightDispatchLedger",
    "CandidateHandoff",
    "CandidateEvidence",
    "CandidateEvidenceDocument",
    "ContactAttempt",
    "Document",
    "DocumentType",
    "RefDocumentType",
    "RefDocumentTypeI18n",
    "RefDocumentTypeVersion",
    "RefDocumentTypeCountryApplicability",
    "RefDocumentTypeRequest",
    "TenantDocumentTypeOverride",
    "RefPack",
    "RefPackItem",
    "RefPackRule",
    "TenantDocumentPackEnablement",
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
    "CandidateAssigneeHistory",
    "CandidateProfile",
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
    "OwnCompany",
    "WorkforceEmployee",
    "WorkforceTaxProfile",
    "WorkforceInsuranceProfile",
    "WorkforceComplianceState",
    "WorkforceWorkEligibilityProfile",
    "WorkforceHrDocumentContext",
    "WorkforceZusWorkspaceTask",
    "WorkforceHrDocumentControlTask",
    "WorkforceLifecycleEvent",
    "WorkforceEmployment",
    "AutomationRule",
    "Campaign",
    "CampaignRun",
    "CampaignTarget",
    "CampaignRunForm",
    "CampaignRunIntakeSource",
    "FlightAdBinding",
    "CampaignResultAttribution",
    "CampaignOutcome",
    "CampaignOutcomeResultLink",
    "CampaignFlightSpendEntry",
    "CampaignResultQualification",
    "AcquisitionActivityEvent",
    "UserCompanyAccess",
    "VacancyRecruiter",
    "Lead",
    "IntakeSourceProfile",
    "IntakeSourceBinding",
    "MetaAdsMap",
    "MetaLeadCredential",
    "MetaLeadSettings",
    "MetaOAuthPending",
    "LeadImportJob",
    "LeadImportJobStatus",
    "TenantLeadForm",
    "LeadQuestionnaireInvite",
    "CommunicationDelivery",
    "CommunicationDeliveryAttempt",
    "CommunicationDeliveryCallbackUnresolved",
    "CandidateDeleteRequest",
    "UserInvite",
    "UserAuditLog",
    "ActivityLog",
    "AuthRefreshToken",
    "UserSession",
    "Tenant",
    "TenantEmailConfig",
    "Company",
    "Vacancy",
    "Funnel",
    "FunnelStage",
    "PeSystemStage",
    "PeStageTemplate",
    "PeProcessProfile",
    "PePipelineTemplate",
    "PeTransitionRule",
    "PeHandoffRule",
    "PeFieldRequirement",
    "PeDocumentRequirement",
    "PeOverrideRule",
    "FrCanonicalField",
    "FrCardLayoutProfile",
    "FrCardLayoutField",
    "EpEntityProfile",
    "EpEntityProfileField",
    "EpIntakePresentation",
    "MergeDocumentTemplate",
    "MergeDocumentGenerationLog",
    "Reminder",
    "UserNotification",
    "CandidateProfile",
    "CommunicationThread",
    "CommunicationThreadResultLink",
    "CommunicationThreadEntityLink",
    "CommunicationInboundUnresolved",
    "CommunicationThreadNextAction",
    "CommunicationThreadSlaEvent",
    "CommunicationTemplate",
    "CommunicationTemplateVersion",
    "CommunicationTemplateVariable",
    "CommunicationTemplateChannelBinding",
    "CommunicationTemplateIntentBinding",
    "CommunicationAutomationRule",
    "CommunicationAutomationRuleVersion",
    "CommunicationAutomationTrigger",
    "CommunicationAutomationDecision",
    "DocumentPolicy",
    "Stage",
    "MagicLink",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "Refund",
]
