"""In-process counters for recruitment funnel resolver usage (deprecation telemetry)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict

_lock = threading.Lock()


@dataclass
class RecruitmentFunnelMetricsSnapshot:
    total_resolves: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    legacy_strangler_hits: int = 0
    analytics_by_pipeline: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, int | dict[str, int]]:
        return {
            "total_resolves": self.total_resolves,
            "by_source": dict(self.by_source),
            "legacy_strangler_hits": self.legacy_strangler_hits,
            "analytics_by_pipeline": dict(self.analytics_by_pipeline),
        }


_counters: dict[str, int] = {}
_total = 0
_legacy_strangler = 0
_analytics_by_pipeline: dict[str, int] = {}


def record_recruitment_funnel_resolve(*, source: str, used_legacy_strangler: bool) -> None:
    key = str(source or "unknown").strip() or "unknown"
    global _total, _legacy_strangler
    with _lock:
        _total += 1
        _counters[key] = _counters.get(key, 0) + 1
        if used_legacy_strangler:
            _legacy_strangler += 1


def record_recruitment_funnel_analytics(*, pipeline_type: str, scope: str) -> None:
    """Track /analytics/funnel usage by pipeline and scope (company vs legacy)."""
    pipe = str(pipeline_type or "unknown").strip() or "unknown"
    sc = str(scope or "unknown").strip() or "unknown"
    key = f"{pipe}:{sc}"
    global _analytics_by_pipeline
    with _lock:
        _analytics_by_pipeline[key] = _analytics_by_pipeline.get(key, 0) + 1


def get_recruitment_funnel_metrics_snapshot() -> RecruitmentFunnelMetricsSnapshot:
    with _lock:
        return RecruitmentFunnelMetricsSnapshot(
            total_resolves=_total,
            by_source=dict(_counters),
            legacy_strangler_hits=_legacy_strangler,
            analytics_by_pipeline=dict(_analytics_by_pipeline),
        )


def reset_recruitment_funnel_metrics() -> None:
    """Test helper only."""
    global _total, _legacy_strangler, _analytics_by_pipeline
    with _lock:
        _total = 0
        _legacy_strangler = 0
        _counters.clear()
        _analytics_by_pipeline.clear()
