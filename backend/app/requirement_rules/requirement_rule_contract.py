"""Requirement Rule Graph contract types (ADR-018 PR 2A.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional


class CitizenshipSegment(str, Enum):
    poland = "poland"
    eu_eea_swiss = "eu_eea_swiss"
    third_country = "third_country"
    unknown = "unknown"


class RequirementApplicability(str, Enum):
    applicable = "applicable"
    not_applicable = "not_applicable"


class AlternativeDisposition(str, Enum):
    available = "available"
    matched = "matched"
    not_selected = "not_selected"
    excluded = "excluded"
    not_applicable = "not_applicable"


class DependencyRuleKind(str, Enum):
    applicability = "applicability"
    requires = "requires"
    satisfies = "satisfies"
    excludes = "excludes"
    activates = "activates"
    supersedes = "supersedes"


@dataclass(frozen=True)
class PersonContext:
    citizenship: Optional[str] = None
    country_of_residence: Optional[str] = None
    stay_duration_over_3_months: Optional[bool] = None
    international_haulage: bool = False
    community_licence_carrier: bool = False
    employment_country: str = "PL"


@dataclass(frozen=True)
class MatchedAlternative:
    requirement_code: str
    alternative_code: str
    document_id: Optional[str] = None


@dataclass(frozen=True)
class ProcessContext:
    work_authorization_state: Optional[str] = None
    residence_authorization_state: Optional[str] = None
    driver_attestation_state: Optional[str] = None


@dataclass
class StageOwnership:
    source_responsibility: str
    operational_owner: str
    verification_role: str
    acquisition_mode: str
    required_by_stage: str
    blocks_stage: str
    completion_event: str
    document_role: str = "input"


@dataclass
class AlternativePlan:
    alternative_code: str
    disposition: AlternativeDisposition = AlternativeDisposition.available
    reason: str = ""


@dataclass
class RequirementPlan:
    requirement_code: str
    applicability: RequirementApplicability = RequirementApplicability.applicable
    applicability_reason: str = ""
    stage_ownership: Optional[StageOwnership] = None
    alternatives: list[AlternativePlan] = field(default_factory=list)
    activated_by: Optional[str] = None
    excluded_by: Optional[str] = None
    satisfies_also: list[str] = field(default_factory=list)


@dataclass
class RuleGraphPlanningInput:
    policy_ref: str
    person: PersonContext
    target_stage: Optional[str] = None
    evaluation_date: Optional[date] = None
    matched_alternatives: tuple[MatchedAlternative, ...] = ()
    process: ProcessContext = field(default_factory=ProcessContext)


@dataclass
class RuleGraphPlanningResult:
    policy_ref: str
    citizenship_segment: CitizenshipSegment
    decision_path: list[str]
    requirements: dict[str, RequirementPlan]
    dependency_trace: list[str] = field(default_factory=list)


__all__ = [
    "AlternativeDisposition",
    "AlternativePlan",
    "CitizenshipSegment",
    "DependencyRuleKind",
    "MatchedAlternative",
    "PersonContext",
    "ProcessContext",
    "RequirementApplicability",
    "RequirementPlan",
    "RuleGraphPlanningInput",
    "RuleGraphPlanningResult",
    "StageOwnership",
]
