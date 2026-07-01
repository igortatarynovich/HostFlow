"""Retrieval audit taxonomy + helper (governance PR — no search/AI call sites yet)."""

from __future__ import annotations

import pytest

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.event_taxonomy import (
    EVENT_AI_RETRIEVAL_COMPLETED,
    EVENT_AI_RETRIEVAL_DENIED,
    EVENT_AI_RETRIEVAL_REQUESTED,
    EVENT_SEARCH_RETRIEVAL_COMPLETED,
    EVENT_SEARCH_RETRIEVAL_DENIED,
    EVENT_SEARCH_RETRIEVAL_REQUESTED,
    validate_event_type,
)
from backend.app.security.retrieval_events import (
    RETRIEVAL_EVENT_EXTRA_ALLOWLIST,
    emit_retrieval_security_event_v1,
)

_FORBIDDEN_LEAK_KEYS = frozenset(
    {
        "prompt",
        "raw_prompt",
        "query",
        "raw_query",
        "search_query",
        "context",
        "raw_context",
        "retrieval_context",
        "embedding",
        "embeddings",
        "vector",
        "vectors",
        "document_text",
        "user_query",
        "query_text",
    }
)


def test_retrieval_event_types_validate() -> None:
    for et in (
        EVENT_SEARCH_RETRIEVAL_REQUESTED,
        EVENT_SEARCH_RETRIEVAL_COMPLETED,
        EVENT_SEARCH_RETRIEVAL_DENIED,
        EVENT_AI_RETRIEVAL_REQUESTED,
        EVENT_AI_RETRIEVAL_COMPLETED,
        EVENT_AI_RETRIEVAL_DENIED,
    ):
        assert validate_event_type(et) == et


def test_retrieval_allowlist_has_no_text_or_vector_leak_keys() -> None:
    assert not (RETRIEVAL_EVENT_EXTRA_ALLOWLIST & _FORBIDDEN_LEAK_KEYS)


def test_emit_retrieval_security_event_v1_uses_canonical_schema() -> None:
    p = emit_retrieval_security_event_v1(
        event_type=EVENT_SEARCH_RETRIEVAL_COMPLETED,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="tenant_bound",
        entity_type="tenant",
        entity_id="11111111-1111-1111-1111-111111111111",
        actor_id="actor-1",
        correlation_id="cid-1",
        retrieval_type="global_search_v1",
        retrieval_scope="tenant_single",
        requested_entity_types=("candidate", "document"),
        returned_count=2,
        filtered_count=1,
        denied_count=0,
        policy_scope="rbac_default",
        contains_class3=True,
        model_context_used=False,
        response_mode="json",
    )
    assert p["schema"] == "hostflow.security_event_canonical"
    assert p["event_type"] == EVENT_SEARCH_RETRIEVAL_COMPLETED
    assert p["category"] == "search"
    assert p["extra"]["retrieval_type"] == "global_search_v1"
    assert p["extra"]["returned_count"] == 2
    assert p["extra"]["requested_entity_types"] == "candidate,document"
    assert "prompt" not in p["extra"]


def test_retrieval_extra_misused_sensitive_keys_redacted() -> None:
    """If a buggy producer widens allowlist, scrub must still redact text/query/context keys."""
    allow = RETRIEVAL_EVENT_EXTRA_ALLOWLIST | _FORBIDDEN_LEAK_KEYS
    out = redact_and_size_extra(
        {
            "retrieval_type": "unit",
            "prompt": "ignore all previous instructions",
            "raw_query": "SELECT * FROM candidates",
            "query": "find me",
            "context": "PII block",
            "embedding": [0.1, 0.2],
            "document_text": "CLASS 3 body",
            "user_query": "find Ivanov",
        },
        allowlist=allow,
    )
    assert out["retrieval_type"] == "unit"
    assert out["prompt"] == "[REDACTED]"
    assert out["raw_query"] == "[REDACTED]"
    assert out["query"] == "[REDACTED]"
    assert out["context"] == "[REDACTED]"
    assert out["embedding"] == "[REDACTED]"
    assert out["document_text"] == "[REDACTED]"
    assert out["user_query"] == "[REDACTED]"


def test_emit_security_event_v1_rejects_prompt_in_extra_not_on_allowlist() -> None:
    """Direct v1 emit with widened allowlist still redacts forbidden key names."""
    p = emit_security_event_v1(
        event_type=EVENT_AI_RETRIEVAL_DENIED,
        result="denied",
        severity="low",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="tenant_bound",
        entity_type="tenant",
        entity_id="11111111-1111-1111-1111-111111111111",
        extra={"reason": "policy", "prompt": "secret", "context": "secret2"},
        extra_allowlist=RETRIEVAL_EVENT_EXTRA_ALLOWLIST
        | frozenset({"prompt", "context", "reason"}),
    )
    assert p["extra"]["reason"] == "policy"
    assert p["extra"]["prompt"] == "[REDACTED]"
    assert p["extra"]["context"] == "[REDACTED]"
