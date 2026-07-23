# GENERATED FILE — do not edit by hand.
# Source: shared/crm_app_paths.json
# Regenerate: python3 scripts/codegen/generate_crm_app_paths.py

"""
Canonical SPA paths under /app (generated from shared/crm_app_paths.json).

Human-oriented rules and docs: docs/SSOT.md §1.6.
"""

APP_PREFIX = "/app"
LEADS = "/app/leads"
TASKS = "/app/work/tasks"
CANDIDATES = "/app/candidates"
CANDIDATES_NO_NEXT_ACTION_PAGE = "/app/candidates/no-next-action"
CLIENTS = "/app/clients"
VACANCIES = "/app/vacancies"
SETTINGS_BILLING = "/app/settings/billing"
SETTINGS_BILLING_CHECKOUT_SUCCESS = "/app/settings/billing?checkout=success"
SETTINGS_BILLING_CHECKOUT_CANCEL = "/app/settings/billing?checkout=cancel"
SETTINGS_INTEGRATIONS = "/app/settings/integrations"
SETTINGS_EMAIL = "/app/settings/email"
SETTINGS_INTEGRATIONS_META = "/app/settings/integrations/meta"
OVERVIEW = "/app/overview"
MESSAGES_LEGACY = "/app/messages"
EMAIL_LEGACY = "/app/email"
INBOX_MESSAGES_SCOPED = "/app/inbox?channel=messages"
INBOX_EMAIL_SCOPED = "/app/inbox?channel=email"
INBOX_THREADS_BASE = "/app/inbox/threads"
ONBOARDING_COMPANY = "/app/onboarding/company"
SETUP_CLIENT = "/app/setup/client"
SETUP_VACANCY = "/app/setup/vacancy"
SETUP_PROCESS = "/app/setup/process"
SETUP_INTAKE = "/app/setup/intake"
SETTINGS_USERS = "/app/settings/users"
RECRUITMENT_SEARCHES = "/app/recruitment/searches"
RECRUITMENT_INBOX = "/app/recruitment/inbox"
MARKETING = "/app/marketing"
MARKETING_NEW = "/app/marketing/new"
MARKETING_SOURCES = "/app/marketing/sources"
SETTINGS_LEAD_FORMS = "/app/settings/lead-forms"

def spa_candidate(candidate_id: str) -> str:
    return f"{CANDIDATES}/{candidate_id}"


def spa_candidate_documents(candidate_id: str) -> str:
    return f"{CANDIDATES}/{candidate_id}/documents"


def spa_client(company_id: str) -> str:
    return f"{CLIENTS}/{company_id}"


def spa_lead(lead_id: str) -> str:
    return f"{LEADS}/{lead_id}"


def spa_vacancy(vacancy_id: str) -> str:
    return f"{VACANCIES}/{vacancy_id}"


def spa_inbox_thread(thread_id: str) -> str:
    return f"{INBOX_THREADS_BASE}/{thread_id}"
