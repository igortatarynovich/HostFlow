# GENERATED FILE — do not edit by hand.
# Source: shared/crm_app_paths.json
# Regenerate: python3 scripts/codegen/generate_crm_app_paths.py

"""
Canonical SPA paths under /app (generated from shared/crm_app_paths.json).

Human-oriented rules and docs: docs/SSOT.md §1.6.
"""

APP_PREFIX = "/app"
LEADS = "/app/leads"
TASKS = "/app/tasks"
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
