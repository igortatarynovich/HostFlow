"""C0.0/C0.1 — Intent + resolver seams (contract alignment, not product features)."""

from __future__ import annotations

import pytest

from backend.app.communications.capability_resolver import resolve_communication_capabilities
from backend.app.communications.command import CommunicationCommand, CommunicationOrigin
from backend.app.communications.intent import CommunicationIntent, resolve_intent_policy
from backend.app.communications.link_resolver import (
    LinkResolveRequest,
    QuestionnaireLinkResolver,
    absolute_public_url,
)
from backend.app.communications.template_resolver import SeedTemplateResolver
from backend.app.services.communication_deliveries.questionnaire_email import (
    absolute_questionnaire_url,
)


def test_intent_policy_drives_questionnaire_templates_and_links() -> None:
    policy = resolve_intent_policy(CommunicationIntent.REQUEST_QUESTIONNAIRE)
    assert "email" in policy.allowed_channels
    assert "questionnaire_invite_email_v1" in policy.allowed_template_keys
    assert "sales_questionnaire" in policy.link_intents
    assert policy.allows_automation is True


@pytest.mark.asyncio
async def test_capability_resolver_covers_candidate_and_sales_inquiry() -> None:
    cand = await resolve_communication_capabilities(
        tenant_id="t1", entity_type="candidate", entity_id="c1"
    )
    assert "email" in cand.allowed_channels
    assert CommunicationIntent.REQUEST_QUESTIONNAIRE.value in cand.allowed_intents

    si = await resolve_communication_capabilities(
        tenant_id="t1", entity_type="sales_inquiry", entity_id="s1"
    )
    assert CommunicationIntent.REQUEST_QUESTIONNAIRE.value in si.allowed_intents
    assert si.bulk_allowed is False


def test_template_resolver_for_intent_hides_registry() -> None:
    resolved = SeedTemplateResolver().resolve_for_intent(
        CommunicationIntent.REQUEST_QUESTIONNAIRE, channel="email"
    )
    assert resolved.key == "questionnaire_invite_email_v1"
    rendered = SeedTemplateResolver().render(
        resolved,
        locale="en",
        variables={"contact_name": "Ann", "questionnaire_url": "https://x.test/a"},
    )
    assert "Ann" in rendered["body"]
    assert "https://x.test/a" in rendered["body"]


@pytest.mark.asyncio
async def test_link_resolver_questionnaire_intent() -> None:
    link = await QuestionnaireLinkResolver().resolve(
        LinkResolveRequest(
            tenant_id="t1",
            link_intent="sales_questionnaire",
            entity_type="lead",
            entity_id="l1",
            apply_path_or_url="/public/apply/tok123?lang=pl",
        )
    )
    assert link.link_intent == "sales_questionnaire"
    assert link.token == "tok123"
    assert link.variable_name == "questionnaire_url"
    assert link.public_url.endswith("/public/apply/tok123?lang=pl")


def test_absolute_questionnaire_url_delegates_to_link_helper() -> None:
    assert absolute_questionnaire_url("/public/apply/x") == absolute_public_url(
        "/public/apply/x"
    )


def test_communication_command_is_send_request_alias() -> None:
    from backend.app.communications.command import SendCommunicationRequest

    assert SendCommunicationRequest is CommunicationCommand
    cmd = CommunicationCommand(
        tenant_id="t",
        origin=CommunicationOrigin(entity_type="lead", entity_id="1"),
        recipients=(),
        channel="email",
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
    )
    assert cmd.normalized_intent() is CommunicationIntent.REQUEST_QUESTIONNAIRE
