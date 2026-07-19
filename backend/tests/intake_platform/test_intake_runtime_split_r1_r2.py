"""Intake Runtime Split V1 — R1 fail-closed + R2 destination registry."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT,
    HANDLER_RECRUITMENT_LEAD_DRAFT,
    HANDLER_SALES_INQUIRY_DRAFT,
)
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.forms_platform.handlers import list_registered_handlers, resolve_submission_handler
from backend.app.intake_platform.destination_registry import (
    DESTINATION_REGISTRY_CONTRACT,
    DESTINATION_RECRUITMENT,
    DESTINATION_SALES,
    DestinationDuplicateRegistrationError,
    DestinationIncompatibleSourceProfileError,
    DestinationIncompatibleTargetError,
    DestinationMissingHandlerError,
    DestinationRegistry,
    DestinationRegistryError,
    DestinationUnknownIntentError,
    build_default_destination_registry,
    platform_destination_registry,
    reset_platform_destination_registry_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_platform_destination_registry_for_tests()
    yield
    reset_platform_destination_registry_for_tests()


# --- R1 fail-closed ---


def test_r1_missing_route_intent_raises_unresolved() -> None:
    with pytest.raises(FormsRoutingUnresolvedError) as exc:
        resolve_submission_handler(route_intent=None)
    assert exc.value.code == "forms_routing_unresolved"
    assert exc.value.details.get("reason") == "missing_route_intent"


def test_r1_empty_route_intent_raises_unresolved() -> None:
    with pytest.raises(FormsRoutingUnresolvedError):
        resolve_submission_handler(route_intent="  ")


def test_r1_unknown_route_intent_raises_unresolved() -> None:
    with pytest.raises(FormsRoutingUnresolvedError) as exc:
        resolve_submission_handler(route_intent="not_a_real_intent")
    assert exc.value.code == "forms_routing_unresolved"
    details = exc.value.details or {}
    assert details.get("normalized") == "unknown" or details.get("route_intent") == "not_a_real_intent"


def test_r1_missing_intent_does_not_default_to_candidate_application() -> None:
    with pytest.raises(FormsRoutingUnresolvedError):
        resolve_submission_handler(route_intent=None)
    # Explicit candidate still works — proves missing ≠ candidate
    row = resolve_submission_handler(route_intent="candidate_application")
    assert row["route_intent"] == "candidate_application"
    assert row["destination"] == DESTINATION_RECRUITMENT


# --- R2 destination registry ---


def test_r2_bootstrap_maps_intents_to_destinations() -> None:
    registry = platform_destination_registry()
    cand = registry.resolve("candidate_application")
    assert cand.destination == DESTINATION_RECRUITMENT
    assert cand.handler_id == HANDLER_RECRUITMENT_LEAD_DRAFT
    assert cand.module_owner == DESTINATION_RECRUITMENT

    sales = registry.resolve("sales_inquiry")
    assert sales.destination == DESTINATION_SALES
    assert sales.handler_id == HANDLER_SALES_INQUIRY_DRAFT
    assert sales.module_owner == DESTINATION_SALES
    assert sales.handler_id != HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT


def test_r2_sales_handler_not_recruitment_owned() -> None:
    sales = resolve_submission_handler(route_intent="sales_inquiry")
    assert sales["module_owner"] == "sales"
    assert sales["destination"] == "sales"
    assert sales["handler_id"] == HANDLER_SALES_INQUIRY_DRAFT
    assert sales["creates_on_create"]["sales_inquiry"] is True
    assert sales["creates_on_create"]["application"] is False
    assert "lead" not in sales["creates"]


def test_r2_candidate_handler_recruitment_owned() -> None:
    cand = resolve_submission_handler(route_intent="candidate_application")
    assert cand["module_owner"] == "recruitment"
    assert cand["handler_id"] == HANDLER_RECRUITMENT_LEAD_DRAFT
    assert cand["creates_on_create"]["application"] is True
    assert cand["creates_on_create"]["sales_inquiry"] is False
    assert cand["creates_on_create"]["lead_draft"] is False


def test_r2_list_handlers_exposes_both_destinations() -> None:
    handlers = list_registered_handlers()
    ids = {row["handler_id"] for row in handlers}
    assert HANDLER_RECRUITMENT_LEAD_DRAFT in ids
    assert HANDLER_SALES_INQUIRY_DRAFT in ids
    assert HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT not in ids
    assert all(row.get("registry_contract") == DESTINATION_REGISTRY_CONTRACT for row in handlers)


def test_r2_rejects_duplicate_registration() -> None:
    registry = DestinationRegistry()
    registry.register(
        route_intent="candidate_application",
        destination=DESTINATION_RECRUITMENT,
        handler_id=HANDLER_RECRUITMENT_LEAD_DRAFT,
    )
    with pytest.raises(DestinationDuplicateRegistrationError):
        registry.register(
            route_intent="candidate_application",
            destination=DESTINATION_RECRUITMENT,
            handler_id=HANDLER_RECRUITMENT_LEAD_DRAFT,
        )


def test_r2_rejects_missing_handler_id() -> None:
    registry = DestinationRegistry()
    with pytest.raises(DestinationMissingHandlerError):
        registry.register(
            route_intent="candidate_application",
            destination=DESTINATION_RECRUITMENT,
            handler_id="",
        )


def test_r2_rejects_sales_handler_as_recruitment_owned() -> None:
    registry = DestinationRegistry()
    with pytest.raises(DestinationRegistryError) as exc:
        registry.register(
            route_intent="sales_inquiry",
            destination=DESTINATION_RECRUITMENT,
            handler_id=HANDLER_SALES_INQUIRY_DRAFT,
        )
    assert "recruitment-owned" in str(exc.value.message)


def test_r2_rejects_sales_destination_with_recruitment_handler_prefix() -> None:
    registry = DestinationRegistry()
    with pytest.raises(DestinationRegistryError):
        registry.register(
            route_intent="sales_inquiry",
            destination=DESTINATION_SALES,
            handler_id=HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT,
        )


def test_r2_rejects_unknown_intent_resolve() -> None:
    with pytest.raises(DestinationUnknownIntentError):
        platform_destination_registry().resolve("partner_inquiry")


def test_r2_incompatible_promotion_target() -> None:
    registry = build_default_destination_registry()
    with pytest.raises(DestinationIncompatibleTargetError):
        registry.assert_compatible_promotion_target("candidate_application", "service")
    registry.assert_compatible_promotion_target("candidate_application", "vacancy")
    registry.assert_compatible_promotion_target("sales_inquiry", "client_account")


def test_r2_incompatible_source_profile() -> None:
    registry = build_default_destination_registry()
    with pytest.raises(DestinationIncompatibleSourceProfileError):
        registry.assert_compatible_source_profile(
            "candidate_application",
            profile_route_intent=None,
        )
    with pytest.raises(DestinationIncompatibleSourceProfileError):
        registry.assert_compatible_source_profile(
            "candidate_application",
            profile_route_intent="sales_inquiry",
        )
    registry.assert_compatible_source_profile(
        "sales_inquiry",
        profile_route_intent="sales_inquiry",
    )
