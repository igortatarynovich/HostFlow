"""Inventory of writers that still store professional facts in legacy fields.

A writer stays ``still_required`` until its retirement condition is met.
``removable`` means the compatibility reason no longer holds and the write
must be deleted. Calculated experience is not cached by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

DECLARED_CE_FROM_RESOLVER = False
CANDIDATE_PROFILE_ON_RESOLVER = True
CE_CONSUMERS_MIGRATED = False
EU_CONSUMERS_MIGRATED = False
CARD_READS_RESOLVER = False
LEAD_ORIGIN_SPLIT = False
OPERATION_SCOPES_ON_PROFILE = False

CE_EU_BRIDGE = (
    "Remove when professional_profile returns declared CE from the correct provenance, "
    "Candidate Profile reads that projection, consumers that need CE use CE semantics, "
    "and consumers that need EU experience use the calculated EU aggregate. "
    "min_experience_eu_years is a vacancy criterion and is not retired by this condition."
)

REPO_ROOT = Path(__file__).resolve().parents[3]

LEGACY_FIELDS = (
    "experience_eu_years",
    "experience_ce_total",
    "experience_years",
    "experience_non_eu_years",
    "intl_experience",
    "trailer_types",
    "route_types",
)

_FIELDS = "|".join(LEGACY_FIELDS)
_WRITE_RE = re.compile(
    rf"""(?x)
    (?:
        \[\s*['"](?P<bracket>{_FIELDS})['"]\s*\]\s*=(?!=)
      | \.(?P<attr>{_FIELDS})\s*=(?!=)
      | (?:^|[,{{])\s*(?P<key>{_FIELDS})\s*:
    )
    """
)

_TYPE_VALUE_RE = re.compile(
    r"""(?x)
    :\s*(?:number|string|boolean|null|any|unknown|Record|Array|string\[\]|number\[\]|boolean\|null)
    \b
    """
)

# Company fleet vocabulary and the vacancy criterion are not candidate-experience writers.
OUT_OF_SCOPE_PARTS = (
    "backend/app/modules/companies/",
    "hostflow-frontend/src/modules/companies/",
    "hostflow-frontend/src/pages/Companies.tsx",
    "hostflow-frontend/src/components/vacancies/",
)

SCAN_ROOTS = (
    "backend/app",
    "hostflow-frontend/src",
)


@dataclass(frozen=True)
class LegacyWriter:
    owner: str
    semantic_intent: str
    source_value: str
    target_legacy_field: str
    compatibility_reason: str
    retirement_condition: str
    marker: str

    @property
    def retirement_status(self) -> str:
        if self.retirement_condition == CE_EU_BRIDGE and _ce_bridge_complete():
            return "removable"
        if self.retirement_condition == "card_reads_resolver" and CARD_READS_RESOLVER:
            return "removable"
        if self.retirement_condition == "lead_origin_split" and LEAD_ORIGIN_SPLIT:
            return "removable"
        if self.retirement_condition == "operation_scopes_on_profile" and OPERATION_SCOPES_ON_PROFILE:
            return "removable"
        return "still_required"


def _ce_bridge_complete() -> bool:
    return all(
        (
            DECLARED_CE_FROM_RESOLVER,
            CANDIDATE_PROFILE_ON_RESOLVER,
            CE_CONSUMERS_MIGRATED,
            EU_CONSUMERS_MIGRATED,
        )
    )


def _writer(
    owner: str,
    field: str,
    intent: str,
    source: str,
    reason: str,
    condition: str,
    marker: str,
) -> LegacyWriter:
    return LegacyWriter(
        owner=owner,
        semantic_intent=intent,
        source_value=source,
        target_legacy_field=field,
        compatibility_reason=reason,
        retirement_condition=condition,
        marker=marker,
    )


LEGACY_WRITERS: tuple[LegacyWriter, ...] = (
    _writer(
        "backend/app/api/public/intake.py",
        "experience_eu_years",
        "declared_ce_written_as_eu",
        "experience.years_ce",
        "Existing readers still consume the stored number.",
        CE_EU_BRIDGE,
        'extra["experience_eu_years"] = merged_years_ce',
    ),
    _writer(
        "backend/app/api/public/intake.py",
        "intl_experience",
        "declared_international_flag",
        "experience.intl_experience",
        "Profile still shows the declared flag.",
        "operation_scopes_on_profile",
        'extra["intl_experience"] = merged_intl_experience',
    ),
    _writer(
        "backend/app/api/public/intake.py",
        "trailer_types",
        "questionnaire_trailer_list",
        "experience.trailer_types",
        "Questionnaire answer stays on extra until a mapping layer exists.",
        "card_reads_resolver",
        'extra["trailer_types"] = _normalize_string_list(merged_trailer_types)',
    ),
    _writer(
        "backend/app/api/public/intake.py",
        "route_types",
        "questionnaire_route_list",
        "experience.route_types",
        "Questionnaire answer stays on extra until a mapping layer exists.",
        "card_reads_resolver",
        'extra["route_types"] = _normalize_string_list(merged_route_types)',
    ),
    _writer(
        "backend/app/api/v1/communications/_helpers/telegram_intake/intake_state.py",
        "experience_eu_years",
        "declared_ce_written_as_eu",
        "telegram step years_ce",
        "Existing readers still consume the stored number.",
        CE_EU_BRIDGE,
        'extra["experience_eu_years"] = int(value)',
    ),
    _writer(
        "backend/app/api/v1/communications/_helpers/telegram_intake/intake_state.py",
        "intl_experience",
        "declared_international_flag",
        "telegram step intl_experience",
        "Profile still shows the declared flag.",
        "operation_scopes_on_profile",
        'extra["intl_experience"] = bool(value)',
    ),
    _writer(
        "backend/app/modules/leads/conversion_mapping.py",
        "experience_eu_years",
        "declared_ce_written_as_eu",
        "recruitment.candidate.experience.years_ce",
        "Lead conversion still lands on the legacy field.",
        CE_EU_BRIDGE,
        '{"extra": "experience_eu_years"}',
    ),
    _writer(
        "backend/app/modules/leads/conversion_mapping.py",
        "intl_experience",
        "declared_international_flag",
        "recruitment.candidate.experience.intl_experience",
        "Lead conversion still lands on the legacy flag.",
        "operation_scopes_on_profile",
        '{"extra": "intl_experience"}',
    ),
    _writer(
        "backend/app/modules/leads/normalizer.py",
        "experience_eu_years",
        "mixed_europe_and_ce_tokens",
        "normalized driving-experience tokens",
        "Europe and C+E tokens still share one stored number.",
        "lead_origin_split",
        'normalized["experience_eu_years"] = experience_years',
    ),
    _writer(
        "backend/app/modules/leads/service/_processing.py",
        "experience_eu_years",
        "copy_normalized_legacy_number",
        "normalized experience_eu_years or years",
        "Lead processing still copies the contaminated number onto extra.",
        "lead_origin_split",
        'extra["experience_eu_years"] = experience_eu_years',
    ),
    _writer(
        "backend/app/modules/leads/service/_processing.py",
        "experience_eu_years",
        "copy_normalized_legacy_number",
        "years_val",
        "Lead processing still copies a years fallback onto the EU field.",
        "lead_origin_split",
        'extra["experience_eu_years"] = years_val',
    ),
    _writer(
        "backend/app/modules/leads/service/_reroute.py",
        "experience_eu_years",
        "copy_normalized_legacy_number",
        "normalized experience_eu_years",
        "Reroute still copies the contaminated number.",
        "lead_origin_split",
        'extra_fields["experience_eu_years"] = experience_eu_years',
    ),
    _writer(
        "backend/app/services/hr_recruitment_transfer.py",
        "experience_eu_years",
        "copy_stored_number",
        "extra.experience_eu_years",
        "Handoff still copies the stored number onward.",
        CE_EU_BRIDGE,
        'target["experience_eu_years"] = extra.get("experience_eu_years")',
    ),
    _writer(
        "backend/app/requirement_rules/readiness_bridge.py",
        "experience_eu_years",
        "project_stored_number_as_years_ce",
        "years_ce already read from the legacy field",
        "Readiness still compares the stored number.",
        CE_EU_BRIDGE,
        'payload["experience_eu_years"] = years_ce',
    ),
    _writer(
        "backend/app/api/v1/candidates/repo.py",
        "trailer_types",
        "response_materialization",
        "stored extra.trailer_types",
        "List payload still exposes the stored questionnaire list.",
        "card_reads_resolver",
        'extra["trailer_types"] = trailer',
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_eu_years",
        "operator_write_under_eu_label",
        "card EU years input",
        "The card still edits the stored number.",
        "card_reads_resolver",
        "result.experience_eu_years = euYears",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_eu_years",
        "operator_write_under_eu_label",
        "card save payload",
        "The card still persists the stored number.",
        "card_reads_resolver",
        "extraForPayload.experience_eu_years = euYears",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_non_eu_years",
        "declared_non_eu_years",
        "card non-EU years input",
        "Declared non-EU years stay on the card.",
        "card_reads_resolver",
        "result.experience_non_eu_years = nonEuYears",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_non_eu_years",
        "declared_non_eu_years",
        "card save payload",
        "Declared non-EU years stay on the card.",
        "card_reads_resolver",
        "extraForPayload.experience_non_eu_years = nonEuYears",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_ce_total",
        "sum_of_eu_and_non_eu_labels",
        "experience_eu_years + experience_non_eu_years",
        "The card still persists the misnamed sum.",
        "card_reads_resolver",
        "result.experience_ce_total =",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_ce_total",
        "sum_of_eu_and_non_eu_labels",
        "card save payload",
        "The card still persists the misnamed sum.",
        "card_reads_resolver",
        "extraForPayload.experience_ce_total =",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "experience_years",
        "legacy_total_fallback",
        "empty default on the card draft",
        "The card still keeps the legacy total key.",
        "card_reads_resolver",
        "experience_years: null",
    ),
    _writer(
        "hostflow-frontend/src/utils/requirementFieldPatch.ts",
        "experience_eu_years",
        "operator_patch_under_years_ce",
        "years_ce patch value",
        "Requirement patches still write the stored number.",
        CE_EU_BRIDGE,
        "experience_eu_years: years",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "trailer_types",
        "questionnaire_trailer_list",
        "card extra trailer chips",
        "The card still edits the questionnaire list.",
        "card_reads_resolver",
        "result.trailer_types =",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "route_types",
        "questionnaire_route_list",
        "card extra route chips",
        "The card still edits the questionnaire list.",
        "card_reads_resolver",
        "result.route_types =",
    ),
    _writer(
        "hostflow-frontend/src/pages/CandidateCard.tsx",
        "intl_experience",
        "declared_international_flag",
        "card extra flag",
        "The card still edits the declared flag.",
        "operation_scopes_on_profile",
        "result.intl_experience =",
    ),
    _writer(
        "hostflow-frontend/src/components/candidate/CandidateExperienceSection.tsx",
        "trailer_types",
        "questionnaire_trailer_list",
        "experience section chips",
        "The section still writes the questionnaire list into extra.",
        "card_reads_resolver",
        "onExtraChange({ trailer_types: vals })",
    ),
    _writer(
        "hostflow-frontend/src/components/candidate/CandidateExperienceSection.tsx",
        "route_types",
        "questionnaire_route_list",
        "experience section chips",
        "The section still writes the questionnaire list into extra.",
        "card_reads_resolver",
        "onExtraChange({ route_types: vals })",
    ),
    _writer(
        "hostflow-frontend/src/modules/public-intake/usePublicIntake.ts",
        "trailer_types",
        "questionnaire_trailer_list",
        "public intake draft",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "trailer_types: []",
    ),
    _writer(
        "hostflow-frontend/src/modules/public-intake/usePublicIntake.ts",
        "route_types",
        "questionnaire_route_list",
        "public intake draft",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "route_types: []",
    ),
    _writer(
        "hostflow-frontend/src/modules/public-intake/usePublicIntake.ts",
        "intl_experience",
        "declared_international_flag",
        "public intake draft",
        "The public form still submits the declared flag.",
        "operation_scopes_on_profile",
        "intl_experience: input.experience?.intl_experience",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicApplyPage.tsx",
        "trailer_types",
        "questionnaire_trailer_list",
        "public apply form",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "trailer_types: [...(base?.trailer_types ?? [])]",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicApplyPage.tsx",
        "route_types",
        "questionnaire_route_list",
        "public apply form",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "route_types: [...(base?.route_types ?? [])]",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicApplyPage.tsx",
        "intl_experience",
        "declared_international_flag",
        "public apply form",
        "The public form still submits the declared flag.",
        "operation_scopes_on_profile",
        "intl_experience: e.target.value",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicIntakeNew.tsx",
        "trailer_types",
        "questionnaire_trailer_list",
        "public intake form",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "trailer_types: trailerTypes",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicIntakeNew.tsx",
        "route_types",
        "questionnaire_route_list",
        "public intake form",
        "The public form still submits the questionnaire list.",
        "card_reads_resolver",
        "route_types: []",
    ),
    _writer(
        "hostflow-frontend/src/pages/public/PublicIntakeNew.tsx",
        "intl_experience",
        "declared_international_flag",
        "public intake form",
        "The public form still submits the declared flag.",
        "operation_scopes_on_profile",
        "intl_experience: intlValue",
    ),
)


@dataclass(frozen=True)
class ObservedWrite:
    path: str
    field: str
    line: str


def _ignored(relative: str) -> bool:
    if relative.endswith("professional_profile_legacy_writers.py"):
        return True
    return any(part in relative for part in OUT_OF_SCOPE_PARTS)


def _line_is_type_declaration(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith(("*", "//", "#", "import ", "export type", "export interface", "if ", "elif ", "for ", "while ")):
        return True
    if any(token in stripped for token in ("mapped_column", "Field(", "Optional[", "List[", "Mapped[", "tuple[")):
        return True
    if "?" in stripped.split(":", 1)[0]:
        return True
    return bool(_TYPE_VALUE_RE.search(stripped))


def observe_legacy_writes(root: Path | None = None) -> list[ObservedWrite]:
    base = root or REPO_ROOT
    found: list[ObservedWrite] = []
    for scan_root in SCAN_ROOTS:
        directory = base / scan_root
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
                continue
            relative = path.relative_to(base).as_posix()
            if _ignored(relative) or "/__tests__/" in relative or "/tests/" in relative:
                continue
            text = path.read_text(encoding="utf-8")
            for raw_line in text.splitlines():
                if _line_is_type_declaration(raw_line):
                    continue
                match = _WRITE_RE.search(raw_line)
                if match is None:
                    continue
                field = match.group("bracket") or match.group("attr") or match.group("key")
                found.append(ObservedWrite(relative, field, raw_line.strip()))
    return found


def _owner_text(owner: str, root: Path | None = None) -> str:
    return ((root or REPO_ROOT) / owner).read_text(encoding="utf-8")


def classify_writes(
    observed: list[ObservedWrite] | None = None,
    root: Path | None = None,
) -> tuple[list[ObservedWrite], list[LegacyWriter], list[LegacyWriter]]:
    rows = observed if observed is not None else observe_legacy_writes(root)
    unclassified: list[ObservedWrite] = []
    for row in rows:
        if not any(writer.owner == row.path and writer.target_legacy_field == row.field for writer in LEGACY_WRITERS):
            unclassified.append(row)
    removable_still_present: list[LegacyWriter] = []
    missing_required: list[LegacyWriter] = []
    for writer in LEGACY_WRITERS:
        present = writer.marker in _owner_text(writer.owner, root)
        if writer.retirement_status == "removable" and present:
            removable_still_present.append(writer)
        if writer.retirement_status == "still_required" and not present:
            missing_required.append(writer)
    return unclassified, missing_required, removable_still_present


__all__ = [
    "CE_EU_BRIDGE",
    "LEGACY_WRITERS",
    "LegacyWriter",
    "classify_writes",
    "observe_legacy_writes",
]
