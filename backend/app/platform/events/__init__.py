"""Platform domain event outbox (ADR-019 PR 3A-1)."""

from backend.app.platform.events.envelope import EventEnvelope
from backend.app.platform.events.registry import EventContractRegistry, get_event_contract_registry
from backend.app.platform.events.outbox.publisher import publish_domain_event
from backend.app.platform.events.outbox.dispatcher import dispatch_outbox_batch
from backend.app.platform.events.consumer.skeleton import ReactionOrchestratorSkeleton

__all__ = [
    "EventEnvelope",
    "EventContractRegistry",
    "get_event_contract_registry",
    "publish_domain_event",
    "dispatch_outbox_batch",
    "ReactionOrchestratorSkeleton",
]
