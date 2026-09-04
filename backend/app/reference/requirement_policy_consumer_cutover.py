"""RPM-3 Consumer Cutover Gate — remaining live required-set readers.

3A ∧ 3B remain PASS. Classified consumers already share the R5 required-set.
This close proves the operator write (persisted tenant_delta) is what D4 and
remaining live readers answer. Named leftovers stay leftover-out-of-scope.

Not a second merge. Not Mapping. Not Hiring E2E. Not RPM program close.
"""

from __future__ import annotations

from typing import Final

CONTRACT_ID: Final[str] = "requirement_policy_consumer_cutover.v1"

# Live paths that answer “need document type X for this candidate?” and must
# load the persisted RPM-2 overlay. Importing a helper is not proof — the
# named gate source-scans these files for ``load_persisted_tenant_delta``.
LIVE_TENANT_DELTA_READERS: Final[tuple[str, ...]] = (
    "backend/app/api/v1/platform/documents_public.py",
    "backend/app/modules/documents/router.py",
    "backend/app/services/candidate_doc_pipeline_guard.py",
    "backend/app/services/transfer_policy_resolver.py",
    "backend/app/requirement_rules/facade.py",
    "backend/app/services/hr_expected_documents_resolver.py",
    "backend/app/services/document_applicability_resolver.py",
    "backend/app/api/public/intake.py",
    "backend/app/services/candidate_telegram_notifications.py",
    "backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py",
    "backend/app/api/v1/documents.py",
)

LEFTOVER_OUT_OF_SCOPE: Final[tuple[str, ...]] = (
    "requirement_checker_gates",
    "documents_eta_legacy_codes",
    "D",
)


__all__ = [
    "CONTRACT_ID",
    "LEFTOVER_OUT_OF_SCOPE",
    "LIVE_TENANT_DELTA_READERS",
]
