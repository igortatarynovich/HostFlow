#!/usr/bin/env python3
"""CL1 — observe-only Candidate composition inventory (driver_ce path).

Regenerates docs/specs/tasks/entity-field-composition-cl1-inventory.tsv.
Does not canonize document types or country codes — observation only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl1-inventory.tsv"

COLUMNS = (
    "kind",
    "code",
    "source",
    "tenant_module",
    "enabled",
    "required_as_found",
    "storage_path",
    "consumers",
    "legacy_usage",
    "notes",
)

QUALIFICATION_FIELD_SUFFIXES = (
    "years_ce",
    "trailer_types",
    "route_types",
    "qualifications",
    "experience_eu_years",
    "experience_non_eu_years",
)


def _bootstrap_imports() -> None:
    import os

    # Standalone --check must not require a loaded .env (subprocess gate / local regen).
    default_db = "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
    os.environ.setdefault("DATABASE_URL", default_db)
    os.environ.setdefault("ASYNC_DATABASE_URL", default_db)
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class InventoryRow:
    kind: str
    code: str
    source: str
    tenant_module: str
    enabled: str
    required_as_found: str
    storage_path: str
    consumers: str
    legacy_usage: str
    notes: str

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "code": self.code,
            "source": self.source,
            "tenant_module": self.tenant_module,
            "enabled": self.enabled,
            "required_as_found": self.required_as_found,
            "storage_path": self.storage_path,
            "consumers": self.consumers,
            "legacy_usage": self.legacy_usage,
            "notes": self.notes,
        }


def _is_screening_field(code: str) -> bool:
    lowered = code.lower()
    return any(token in lowered for token in QUALIFICATION_FIELD_SUFFIXES)


def _screening_note(code: str, level: str) -> str:
    if level == "required" and _is_screening_field(code):
        return "screening_as_required_observed"
    return ""


def collect_inventory_rows() -> list[InventoryRow]:
    from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
    from backend.app.field_registry.manifests.recruitment import recruitment_candidate_fields
    from backend.app.requirement_rules.manifests.recruitment import recruitment_driver_ce_document_pack
    from backend.app.seed_candidate_profiles import FULL_DOCUMENT_CONFIGS, FULL_FIELD_CONFIGS

    rows: list[InventoryRow] = []

    seed_consumers = "backend/app/seed_candidate_profiles.py"
    for item in FULL_FIELD_CONFIGS:
        key = str(item.get("field_key") or "").strip()
        required = bool(item.get("required"))
        visible = bool(item.get("visible", True))
        rows.append(
            InventoryRow(
                kind="field",
                code=key,
                source="candidate_profile.config.field_configs",
                tenant_module="platform_seed",
                enabled="true" if visible else "false",
                required_as_found="required" if required else "optional",
                storage_path="column|extra|personal_data",
                consumers=seed_consumers,
                legacy_usage="driver_ce_default_seed",
                notes=_screening_note(key, "required" if required else "optional"),
            )
        )

    for item in FULL_DOCUMENT_CONFIGS:
        doc_code = str(item.get("document_type_id") or "").strip()
        required = bool(item.get("required"))
        rows.append(
            InventoryRow(
                kind="document",
                code=doc_code,
                source="candidate_profile.config.document_configs",
                tenant_module="platform_seed",
                enabled="true",
                required_as_found="required" if required else "optional",
                storage_path="config_blob",
                consumers="backend/app/services/candidate_document_checklist.py;hostflow-frontend/src/utils/profileUtils.ts",
                legacy_usage="driver_ce_default_seed",
                notes="observed_code_not_canonized",
            )
        )

    registry_codes = {item["qualified_code"] for item in recruitment_candidate_fields()}
    for item in recruitment_candidate_fields():
        storage = item.get("storage") or {}
        rows.append(
            InventoryRow(
                kind="field",
                code=item["qualified_code"],
                source="field_registry.manifest",
                tenant_module="recruitment",
                enabled="true",
                required_as_found="n/a",
                storage_path=f"{storage.get('kind', '')}:{storage.get('path', '')}",
                consumers="backend/app/field_registry/manifests/recruitment.py",
                legacy_usage="canonical_registry",
                notes="",
            )
        )

    profile = recruitment_candidate_driver_ce_profile()
    for field in profile.get("fields") or []:
        code = str(field.get("qualified_code") or "").strip()
        intake = str(field.get("intake_level") or "optional")
        card_save = str(field.get("card_save_level") or "optional")
        transition = str(field.get("transition_level") or "optional")
        notes = _screening_note(code, card_save) or _screening_note(code, intake)
        if transition == "required":
            notes = (notes + ";transition_level_required").strip(";")
        rows.append(
            InventoryRow(
                kind="field",
                code=code,
                source="entity_profile.manifest",
                tenant_module="recruitment",
                enabled="true",
                required_as_found=f"intake={intake};card_save={card_save};transition={transition}",
                storage_path="entity_profile_membership",
                consumers="backend/app/entity_profile/manifests/recruitment.py;backend/app/requirement_rules/registry.py",
                legacy_usage="mapped_entity_profile",
                notes=notes,
            )
        )
        if code not in registry_codes and not code.startswith("platform.identity."):
            rows.append(
                InventoryRow(
                    kind="ui_hole",
                    code=code,
                    source="entity_profile.manifest",
                    tenant_module="recruitment",
                    enabled="true",
                    required_as_found="n/a",
                    storage_path="membership_without_field_registry_row",
                    consumers="backend/app/entity_profile/manifests/recruitment.py",
                    legacy_usage="profile_field_not_in_recruitment_registry",
                    notes="observe_only",
                )
            )

    pack = recruitment_driver_ce_document_pack()
    for slot in pack.get("required_slots") or []:
        rows.append(
            InventoryRow(
                kind="document",
                code=str(slot.get("slot_code") or ""),
                source="requirement_rules.document_pack.slots",
                tenant_module="recruitment",
                enabled="true",
                required_as_found=str(slot.get("level") or "blocking"),
                storage_path="slot",
                consumers="backend/app/requirement_rules/manifests/recruitment.py",
                legacy_usage="requirement_pack_slot",
                notes="observed_slot_code",
            )
        )
    for doc in pack.get("required_documents") or []:
        rows.append(
            InventoryRow(
                kind="document",
                code=str(doc.get("document_type_code") or ""),
                source="requirement_rules.document_pack.documents",
                tenant_module="recruitment",
                enabled="true",
                required_as_found=str(doc.get("level") or "blocking"),
                storage_path="document_type_code",
                consumers="backend/app/requirement_rules/manifests/recruitment.py",
                legacy_usage="requirement_pack_document",
                notes="observed_code_not_canonized",
            )
        )

    seed_keys = {str(item.get("field_key") or "") for item in FULL_FIELD_CONFIGS}
    for item in recruitment_candidate_fields():
        aliases = item.get("legacy_aliases") or []
        for alias in aliases:
            if alias not in seed_keys:
                rows.append(
                    InventoryRow(
                        kind="ui_hole",
                        code=alias,
                        source="field_registry.legacy_aliases",
                        tenant_module="recruitment",
                        enabled="true",
                        required_as_found="n/a",
                        storage_path=item["qualified_code"],
                        consumers="backend/app/field_registry/manifests/recruitment.py",
                        legacy_usage="registry_alias_not_in_seed_field_configs",
                        notes="observe_only",
                    )
                )

    rows.append(
        InventoryRow(
            kind="field",
            code="validateRequiredFields",
            source="frontend.profileUtils",
            tenant_module="recruitment",
            enabled="true",
            required_as_found="save_time_required_map",
            storage_path="hardcoded",
            consumers="hostflow-frontend/src/utils/profileUtils.ts;hostflow-frontend/src/pages/CandidateCard.tsx",
            legacy_usage="frontend_hardcode",
            notes="screening_as_required_observed",
        )
    )
    rows.append(
        InventoryRow(
            kind="field",
            code="launchSearchIntakeFields",
            source="frontend.launchSearchIntakeFields",
            tenant_module="recruitment",
            enabled="true",
            required_as_found="intake_required_levels",
            storage_path="hardcoded",
            consumers="hostflow-frontend/src/utils/launchSearchIntakeFields.ts",
            legacy_usage="frontend_hardcode",
            notes="screening_as_required_observed",
        )
    )

    return sorted(rows, key=lambda row: (row.kind, row.code, row.source))


def render_tsv(rows: list[InventoryRow]) -> str:
    lines: list[str] = []
    lines.append("\t".join(COLUMNS))
    for row in rows:
        lines.append("\t".join(row.as_dict()[col] for col in COLUMNS))
    return "\n".join(lines) + "\n"


def read_committed_tsv() -> str:
    return OUTPUT.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if committed TSV drifts")
    parser.add_argument("--write", action="store_true", help="Write inventory TSV to docs path")
    args = parser.parse_args(argv)

    _bootstrap_imports()
    rendered = render_tsv(collect_inventory_rows())

    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"Wrote {OUTPUT}")
        return 0

    if args.check:
        committed = read_committed_tsv()
        if committed != rendered:
            print("CL1 inventory drift: regenerate with --write", file=sys.stderr)
            return 1
        print("CL1 inventory check: OK")
        return 0

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
