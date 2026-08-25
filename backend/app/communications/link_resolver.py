"""LinkResolver — mint/resolve public action URLs from link intents (C0.0 extension point).

Full PublicActionLinkService (token store, reuse policy, audit) is later.
This interface is the seam; questionnaire uses one concrete implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from backend.app.core.settings import settings


@dataclass(frozen=True, slots=True)
class LinkResolveRequest:
    tenant_id: str
    link_intent: str
    entity_type: str
    entity_id: str
    locale: str | None = None
    # Temporary bridge until PublicActionLinkService owns token minting.
    apply_path_or_url: str | None = None
    actor_id: str | None = None
    meta: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ResolvedPublicLink:
    link_intent: str
    public_url: str
    token: str | None = None
    expires_at: str | None = None
    variable_name: str = "public_action_url"


class LinkResolver(Protocol):
    async def resolve(self, request: LinkResolveRequest) -> ResolvedPublicLink: ...


def _trim(value: Any) -> str:
    return str(value or "").strip()


def absolute_public_url(path_or_url: str) -> str:
    """Normalize a relative apply path into an absolute frontend URL."""
    url = _trim(path_or_url)
    if not url:
        return ""
    if re.match(r"^https?://", url, flags=re.I):
        return url
    base = _trim(getattr(settings, "frontend_url", None) or "") or "https://hostflow.cc"
    base = base.rstrip("/")
    return f"{base}{url if url.startswith('/') else '/' + url}"


# Intent → template variable name (templates still use legacy names until catalog migrates).
_LINK_VARIABLE_NAMES: dict[str, str] = {
    "sales_questionnaire": "questionnaire_url",
    "candidate_questionnaire": "questionnaire_url",
    "document_upload": "document_upload_url",
    "unsubscribe": "unsubscribe_url",
    "privacy_notice": "privacy_notice_url",
    "meeting_booking": "meeting_booking_url",
    "offer_review": "offer_review_url",
    "proposal_review": "proposal_review_url",
    "client_onboarding": "client_onboarding_url",
}


class QuestionnaireLinkResolver:
    """First LinkResolver implementation — sales/candidate questionnaire apply links."""

    SUPPORTED = frozenset({"sales_questionnaire", "candidate_questionnaire"})

    async def resolve(self, request: LinkResolveRequest) -> ResolvedPublicLink:
        intent = _trim(request.link_intent)
        if intent not in self.SUPPORTED:
            raise ValueError(f"unsupported link_intent for QuestionnaireLinkResolver: {intent}")
        path = _trim(request.apply_path_or_url)
        if not path:
            raise ValueError("apply_path_or_url is required for questionnaire links")
        url = absolute_public_url(path)
        token = None
        # /public/apply/{token}…
        m = re.search(r"/public/apply/([^/?#]+)", path)
        if m:
            token = m.group(1)
        return ResolvedPublicLink(
            link_intent=intent,
            public_url=url,
            token=token,
            variable_name=_LINK_VARIABLE_NAMES.get(intent, "questionnaire_url"),
        )


_default_link_resolver: LinkResolver = QuestionnaireLinkResolver()


def get_link_resolver() -> LinkResolver:
    return _default_link_resolver
