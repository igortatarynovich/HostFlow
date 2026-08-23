from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.reference_foundation import validate_reference_code
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
    RefPack,
    TenantDocumentPackEnablement,
)
from backend.app.reference.core_immutable_catalogs import (
    CATALOG_VERSION as CORE_IMMUTABLE_CATALOG_VERSION,
    get_country_by_alpha2,
    list_countries_immutable,
    list_languages_immutable,
)
from backend.app.reference.country_registry import (
    CATALOG_VERSION as COUNTRY_REGISTRY_CATALOG_VERSION,
    list_country_registry_entries,
)
from backend.app.reference.legal_document_catalogs import (
    CATALOG_VERSION as LEGAL_DOCUMENT_CATALOG_VERSION,
    get_citizenship_by_alpha2,
    list_citizenships_canonical,
    list_document_categories_canonical,
    list_document_types_canonical,
    list_legal_statuses_canonical,
    list_permit_types_canonical,
    list_visa_types_canonical,
)
from backend.app.reference.reference_field_schema_registry import (
    CATALOG_VERSION as FIELD_SCHEMA_CATALOG_VERSION,
    list_reference_field_schemas,
)
from backend.app.reference.workforce_transport_catalogs import (
    CATALOG_VERSION as WORKFORCE_TRANSPORT_CATALOG_VERSION,
    list_driver_capability_classes_canonical,
    list_employment_types_canonical,
    list_transport_modes_canonical,
    list_transport_qualification_types_canonical,
    list_workforce_categories_canonical,
)
from backend.app.reference.reference_tenant_override_foundation import (
    CATALOG_VERSION as TENANT_OVERRIDE_FOUNDATION_CATALOG_VERSION,
    TENANT_OVERLAY_SCHEMA_CONTRACT,
    is_tenant_override_allowed,
    list_tenant_override_domains,
    list_tenant_override_rules,
    list_tenant_override_types,
)
from backend.app.reference.reference_rule_pack_foundation import (
    CATALOG_VERSION as RULE_PACK_FOUNDATION_CATALOG_VERSION,
    list_rule_pack_domain_targets,
    list_rule_pack_metadata,
    list_rule_pack_types,
    list_rule_pack_version_markers,
)
from backend.app.reference.reference_seed_manifest import (
    CATALOG_VERSION as SEED_MANIFEST_CATALOG_VERSION,
    MIGRATION_BOUNDARY_DESCRIPTION,
    compose_deterministic_seed_checksum,
    get_reference_version_manifest,
    list_seed_manifest_entries,
)
from backend.app.services.document_applicability_resolver import (
    DocumentApplicabilityContext,
    DocumentApplicabilityResolver,
)
from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver


@dataclass
class ReferenceContext:
    tenant_id: str
    module: str = "other"
    entity_type: str = "candidate"
    entity_id: Optional[str] = None
    candidate_id: Optional[str] = None
    employee_id: Optional[str] = None
    work_country: Optional[str] = None
    citizenship: Optional[str] = None
    residence_status: Optional[str] = None
    position_category: Optional[str] = None
    stage: Optional[str] = None
    employment_type: Optional[str] = None
    client_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    locale: str = "en"
    as_of: Optional[str] = None


@dataclass
class ReferenceSource:
    type: str
    code: str


@dataclass
class ReferenceRule:
    code: str
    scope: str
    priority: int
    condition: dict[str, Any] = field(default_factory=dict)
    effect: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReferenceItem:
    item_type: str
    code: str
    label: str
    visible: bool = True
    required: bool = False
    reason: str = ""
    source: ReferenceSource = field(default_factory=lambda: ReferenceSource(type="system", code="catalog"))
    rules: list[ReferenceRule] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReferenceVersion:
    contract_version: str
    reference_version: str
    calculated_at: str


@dataclass
class ReferenceBundleResponse:
    version: ReferenceVersion
    context_echo: dict[str, Any]
    items: list[ReferenceItem] = field(default_factory=list)
    applicability: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["version"] = {
            "contract_version": self.version.contract_version,
            "reference_version": self.version.reference_version,
            "calculated_at": self.version.calculated_at,
        }
        return d


class ReferenceServiceFacade:
    """REF-3 boundary facade for reference data and applicability reads."""

    CONTRACT_VERSION = "ref-facade-v1"
    REFERENCE_VERSION = (
        f"{CORE_IMMUTABLE_CATALOG_VERSION}"
        f"+{LEGAL_DOCUMENT_CATALOG_VERSION}"
        f"+{FIELD_SCHEMA_CATALOG_VERSION}"
        f"+{WORKFORCE_TRANSPORT_CATALOG_VERSION}"
        f"+{TENANT_OVERRIDE_FOUNDATION_CATALOG_VERSION}"
        f"+{RULE_PACK_FOUNDATION_CATALOG_VERSION}"
        f"+{SEED_MANIFEST_CATALOG_VERSION}"
    )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def normalize_reference_code(*, domain: str, value: str) -> str:
        """Facade boundary helper for canonical code normalization."""
        return validate_reference_code(domain, value)

    @classmethod
    def normalize_country_alpha2(cls, value: str | None) -> str | None:
        """Facade boundary helper for canonical country (ISO alpha-2) normalization."""
        _ = cls
        item = get_country_by_alpha2(value)
        return item.code_alpha2 if item else None

    @classmethod
    def normalize_citizenship_alpha2(cls, value: str | None) -> str | None:
        """Facade boundary helper for canonical citizenship (ISO alpha-2) normalization."""
        _ = cls
        item = get_citizenship_by_alpha2(value)
        return item.code_alpha2 if item else None

    @classmethod
    def get_core_immutable_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": CORE_IMMUTABLE_CATALOG_VERSION,
            "countries": [
                {
                    "code_alpha2": item.code_alpha2,
                    "code_alpha3": item.code_alpha3,
                    "code_numeric": item.code_numeric,
                    "name": item.name,
                }
                for item in list_countries_immutable()
            ],
            "languages": [
                {
                    "code": item.code,
                    "name": item.name,
                }
                for item in list_languages_immutable()
            ],
        }

    @classmethod
    def compatibility_check_core_immutable_snapshot(cls) -> dict[str, Any]:
        snapshot = cls.get_core_immutable_snapshot()
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        countries = snapshot.get("countries") or []
        languages = snapshot.get("languages") or []

        seen_country_alpha2: set[str] = set()
        for row in countries:
            alpha2 = str(row.get("code_alpha2") or "").strip().upper()
            alpha3 = str(row.get("code_alpha3") or "").strip().upper()
            numeric = str(row.get("code_numeric") or "").strip()
            name = str(row.get("name") or "").strip()
            if not alpha2 or not alpha3 or not numeric or not name:
                errors.append({"code": "country_row_incomplete", "detail": str(row)})
                continue
            if alpha2 in seen_country_alpha2:
                errors.append({"code": "country_alpha2_duplicate", "detail": alpha2})
            seen_country_alpha2.add(alpha2)

        seen_lang_codes: set[str] = set()
        for row in languages:
            code = str(row.get("code") or "").strip().lower()
            name = str(row.get("name") or "").strip()
            if not code or not name:
                errors.append({"code": "language_row_incomplete", "detail": str(row)})
                continue
            if code in seen_lang_codes:
                errors.append({"code": "language_code_duplicate", "detail": code})
            seen_lang_codes.add(code)

        if not countries:
            warnings.append({"code": "countries_empty", "detail": "No immutable countries in snapshot"})
        if not languages:
            warnings.append({"code": "languages_empty", "detail": "No immutable languages in snapshot"})

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
        }

    @classmethod
    def get_country_registry_snapshot(cls) -> dict[str, Any]:
        """Reference R1 Country Registry snapshot.

        Contract blocks: ``identity`` | ``classifications`` | ``labels``.
        Runtime catalogs are unchanged — this is definition, not cutover.
        """
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": COUNTRY_REGISTRY_CATALOG_VERSION,
            "countries": [
                {
                    "identity": {
                        "alpha2": item.identity.alpha2,
                        "alpha3": item.identity.alpha3,
                        "numeric": item.identity.numeric,
                    },
                    "classifications": {
                        "dial_code": item.classifications.dial_code,
                        "eu_member": item.classifications.eu_member,
                        "schengen_member": item.classifications.schengen_member,
                    },
                    "labels": {
                        "en": item.labels.en,
                        "pl": item.labels.pl,
                        "ru": item.labels.ru,
                    },
                }
                for item in list_country_registry_entries()
            ],
        }

    @classmethod
    def compatibility_check_country_registry_snapshot(cls) -> dict[str, Any]:
        snapshot = cls.get_country_registry_snapshot()
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        countries = snapshot.get("countries") or []
        seen_alpha2: set[str] = set()
        dial_codes: list[str] = []

        for row in countries:
            identity = row.get("identity") or {}
            classifications = row.get("classifications") or {}
            labels = row.get("labels") or {}
            alpha2 = str(identity.get("alpha2") or "").strip().upper()
            alpha3 = str(identity.get("alpha3") or "").strip().upper()
            numeric = str(identity.get("numeric") or "").strip()
            dial = str(classifications.get("dial_code") or "").strip()
            if not alpha2 or not alpha3 or not numeric:
                errors.append({"code": "country_identity_incomplete", "detail": str(row)})
                continue
            if alpha2 in seen_alpha2:
                errors.append({"code": "country_alpha2_duplicate", "detail": alpha2})
            seen_alpha2.add(alpha2)
            if alpha2 in {"XK", "UK", "OTHER"}:
                errors.append({"code": "forbidden_identity_code", "detail": alpha2})
            for locale in ("en", "pl", "ru"):
                if not str(labels.get(locale) or "").strip():
                    errors.append({"code": "country_label_missing", "detail": f"{alpha2}:{locale}"})
            if "immutable" in row or "immutable" in identity or "immutable" in classifications:
                errors.append({"code": "immutable_in_public_contract", "detail": alpha2})
            if dial:
                dial_codes.append(dial)

        if len(countries) < 249:
            errors.append(
                {
                    "code": "iso_set_incomplete",
                    "detail": f"expected ISO 3166-1 assigned set (249), got {len(countries)}",
                }
            )
        if dial_codes and len(dial_codes) == len(set(dial_codes)):
            errors.append(
                {
                    "code": "dial_code_uniqueness_forbidden",
                    "detail": "dial_code must not be a unique identity key",
                }
            )
        if not countries:
            warnings.append({"code": "countries_empty", "detail": "No country registry rows in snapshot"})

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
        }

    @classmethod
    def get_legal_document_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": LEGAL_DOCUMENT_CATALOG_VERSION,
            "citizenships": [
                {"code_alpha2": item.code_alpha2, "label": item.label}
                for item in list_citizenships_canonical()
            ],
            "legal_statuses": [{"code": item.code, "label": item.label} for item in list_legal_statuses_canonical()],
            "permit_types": [{"code": item.code, "label": item.label} for item in list_permit_types_canonical()],
            "visa_types": [{"code": item.code, "label": item.label} for item in list_visa_types_canonical()],
            "document_categories": [
                {"code": item.code, "label": item.label}
                for item in list_document_categories_canonical()
            ],
            "document_types": [
                {
                    "code": item.code,
                    "label": item.label,
                    "category_code": item.category_code,
                    "expiry_track_required": bool(item.expiry_track_required),
                }
                for item in list_document_types_canonical()
            ],
        }

    @classmethod
    def get_reference_field_schema_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": FIELD_SCHEMA_CATALOG_VERSION,
            "fields": [
                {
                    "field_key": item.field_key,
                    "field_type": item.field_type,
                    "group": item.group,
                    "label": item.label,
                    "description": item.description,
                    "reference_domain": item.reference_domain,
                }
                for item in list_reference_field_schemas()
            ],
        }

    @classmethod
    def get_workforce_transport_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": WORKFORCE_TRANSPORT_CATALOG_VERSION,
            "workforce_categories": [
                {"code": item.code, "label": item.label}
                for item in list_workforce_categories_canonical()
            ],
            "employment_types": [
                {"code": item.code, "label": item.label}
                for item in list_employment_types_canonical()
            ],
            "transport_modes": [
                {"code": item.code, "label": item.label}
                for item in list_transport_modes_canonical()
            ],
            "transport_qualification_types": [
                {"code": item.code, "label": item.label}
                for item in list_transport_qualification_types_canonical()
            ],
            "driver_capability_classes": [
                {"code": item.code, "label": item.label}
                for item in list_driver_capability_classes_canonical()
            ],
        }

    @classmethod
    def get_tenant_override_foundation_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": TENANT_OVERRIDE_FOUNDATION_CATALOG_VERSION,
            "override_types": [{"code": item.code, "label": item.label} for item in list_tenant_override_types()],
            "allowed_domains": [{"code": item.code, "label": item.label} for item in list_tenant_override_domains()],
            "immutable_rules": [
                {
                    "domain_code": item.domain_code,
                    "override_type_code": item.override_type_code,
                    "allowed": bool(item.allowed),
                    "immutable_reason": item.immutable_reason,
                }
                for item in list_tenant_override_rules()
            ],
            "overlay_schema_contract": dict(TENANT_OVERLAY_SCHEMA_CONTRACT),
        }

    @classmethod
    def compatibility_check_tenant_override_foundation_snapshot(cls) -> dict[str, Any]:
        snapshot = cls.get_tenant_override_foundation_snapshot()
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        types = snapshot.get("override_types") or []
        domains = snapshot.get("allowed_domains") or []
        rules = snapshot.get("immutable_rules") or []
        schema_contract = snapshot.get("overlay_schema_contract") or {}

        if not types:
            errors.append({"code": "override_types_empty", "detail": "No override types defined"})
        if not domains:
            errors.append({"code": "allowed_domains_empty", "detail": "No allowed override domains defined"})
        if not rules:
            warnings.append({"code": "override_rules_empty", "detail": "No immutable override rules defined"})

        expected_contract_keys = {"tenant_id", "domain", "override_type", "target_code", "value"}
        if set(schema_contract.keys()) != expected_contract_keys:
            errors.append({"code": "overlay_schema_contract_mismatch", "detail": str(sorted(schema_contract.keys()))})

        for row in rules:
            domain_code = str(row.get("domain_code") or "").strip().lower()
            override_type_code = str(row.get("override_type_code") or "").strip().lower()
            if not domain_code or not override_type_code:
                errors.append({"code": "override_rule_incomplete", "detail": str(row)})
                continue
            facade_allowed = is_tenant_override_allowed(domain=domain_code, override_type=override_type_code)
            if facade_allowed != bool(row.get("allowed")):
                errors.append({"code": "override_rule_resolution_mismatch", "detail": f"{domain_code}:{override_type_code}"})

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
        }

    @classmethod
    def get_rule_pack_foundation_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": RULE_PACK_FOUNDATION_CATALOG_VERSION,
            "rule_pack_types": [{"code": item.code, "label": item.label} for item in list_rule_pack_types()],
            "rule_pack_metadata": [
                {
                    "pack_code": item.pack_code,
                    "pack_type": item.pack_type,
                    "title": item.title,
                    "description": item.description,
                    "lifecycle_state": item.lifecycle_state,
                }
                for item in list_rule_pack_metadata()
            ],
            "allowed_target_domains": [
                {"pack_code": item.pack_code, "target_domain": item.target_domain}
                for item in list_rule_pack_domain_targets()
            ],
            "rule_pack_versions": [
                {
                    "pack_code": item.pack_code,
                    "schema_version": item.schema_version,
                    "compatibility_marker": item.compatibility_marker,
                }
                for item in list_rule_pack_version_markers()
            ],
        }

    @classmethod
    def compatibility_check_rule_pack_foundation_snapshot(cls) -> dict[str, Any]:
        snapshot = cls.get_rule_pack_foundation_snapshot()
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        types = snapshot.get("rule_pack_types") or []
        metadata = snapshot.get("rule_pack_metadata") or []
        target_domains = snapshot.get("allowed_target_domains") or []
        versions = snapshot.get("rule_pack_versions") or []

        if not types:
            errors.append({"code": "rule_pack_types_empty", "detail": "No rule pack types defined"})
        if not metadata:
            errors.append({"code": "rule_pack_metadata_empty", "detail": "No rule pack metadata defined"})
        if not target_domains:
            warnings.append({"code": "rule_pack_target_domains_empty", "detail": "No target domains defined"})
        if not versions:
            errors.append({"code": "rule_pack_versions_empty", "detail": "No version markers defined"})

        known_pack_codes = {str(row.get("pack_code") or "").strip() for row in metadata}
        for row in versions:
            pack_code = str(row.get("pack_code") or "").strip()
            marker = str(row.get("compatibility_marker") or "").strip()
            if not pack_code:
                errors.append({"code": "rule_pack_version_incomplete", "detail": str(row)})
                continue
            if pack_code not in known_pack_codes:
                errors.append({"code": "rule_pack_version_unknown_pack", "detail": pack_code})
            if marker != "skeleton-only":
                errors.append({"code": "rule_pack_compatibility_marker_invalid", "detail": marker})

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
        }

    @classmethod
    def get_reference_seed_manifest_snapshot(cls) -> dict[str, Any]:
        return {
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
            "catalog_version": SEED_MANIFEST_CATALOG_VERSION,
            "seed_manifest": [
                {
                    "domain": item.domain,
                    "seed_id": item.seed_id,
                    "source": item.source,
                    "deterministic": bool(item.deterministic),
                }
                for item in list_seed_manifest_entries()
            ],
            "reference_versions": get_reference_version_manifest(),
            "deterministic_checksum": compose_deterministic_seed_checksum(),
            "migration_boundary": dict(MIGRATION_BOUNDARY_DESCRIPTION),
        }

    @classmethod
    def compatibility_check_reference_seed_manifest_snapshot(cls) -> dict[str, Any]:
        snapshot = cls.get_reference_seed_manifest_snapshot()
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        seed_manifest = snapshot.get("seed_manifest") or []
        reference_versions = snapshot.get("reference_versions") or {}
        checksum = str(snapshot.get("deterministic_checksum") or "").strip()
        migration_boundary = snapshot.get("migration_boundary") or {}

        if not seed_manifest:
            errors.append({"code": "seed_manifest_empty", "detail": "No seed manifest entries defined"})
        if not reference_versions:
            errors.append({"code": "reference_versions_empty", "detail": "No reference versions defined"})
        if len(checksum) != 64:
            errors.append({"code": "checksum_invalid", "detail": checksum})

        expected_boundary_keys = {"phase_scope", "allowed", "blocked"}
        if set(migration_boundary.keys()) != expected_boundary_keys:
            errors.append({"code": "migration_boundary_mismatch", "detail": str(sorted(migration_boundary.keys()))})

        manifest_domains = {str(item.get("domain") or "").strip() for item in seed_manifest}
        if manifest_domains != set(reference_versions.keys()):
            warnings.append({"code": "manifest_versions_domain_mismatch", "detail": "Domain set mismatch"})

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "contract_version": cls.CONTRACT_VERSION,
            "reference_version": cls.REFERENCE_VERSION,
        }

    @classmethod
    def _version(cls) -> ReferenceVersion:
        return ReferenceVersion(
            contract_version=cls.CONTRACT_VERSION,
            reference_version=cls.REFERENCE_VERSION,
            calculated_at=cls._now_iso(),
        )

    @classmethod
    async def get_reference_bundle(
        cls,
        db: AsyncSession,
        *,
        context: ReferenceContext,
    ) -> dict[str, Any]:
        applicability = await cls.get_applicable_documents(db, context=context)
        country_items = [
            ReferenceItem(
                item_type="country",
                code=item.code_alpha2,
                label=item.name,
                source=ReferenceSource(type="system", code="core_immutable_catalogs"),
                validation={
                    "alpha3": item.code_alpha3,
                    "numeric": item.code_numeric,
                },
            )
            for item in list_countries_immutable()
        ]
        language_items = [
            ReferenceItem(
                item_type="language",
                code=item.code,
                label=item.name,
                source=ReferenceSource(type="system", code="core_immutable_catalogs"),
            )
            for item in list_languages_immutable()
        ]
        bundle = ReferenceBundleResponse(
            version=cls._version(),
            context_echo=asdict(context),
            items=[*country_items, *language_items],
            applicability={"expected_documents": applicability},
            errors=[],
        )
        return bundle.to_dict()

    @classmethod
    async def get_applicable_documents(
        cls,
        db: AsyncSession,
        *,
        context: ReferenceContext,
    ) -> list[dict[str, Any]]:
        rows = await DocumentApplicabilityResolver.resolve_expected_documents(
            db,
            context=DocumentApplicabilityContext(
                tenant_id=str(context.tenant_id),
                candidate_id=context.candidate_id,
                employee_id=context.employee_id,
                citizenship=context.citizenship,
                work_country=context.work_country,
                residence_status=context.residence_status,
                position_category=context.position_category,
                employment_type=context.employment_type,
                stage=context.stage,
                client_id=context.client_id,
                vacancy_id=context.vacancy_id,
            ),
        )
        return rows

    @classmethod
    async def get_document_type_profile(
        cls,
        db: AsyncSession,
        *,
        code: str,
        context: ReferenceContext,
    ) -> dict[str, Any]:
        doc_type = (
            await db.execute(select(RefDocumentType).where(RefDocumentType.code == str(code).strip().lower()))
        ).scalars().first()
        if not doc_type:
            return {
                "version": asdict(cls._version()),
                "context_echo": asdict(context),
                "profile": None,
                "errors": [{"code": "document_type_not_found", "message": str(code)}],
            }

        ver = (
            await db.execute(
                select(RefDocumentTypeVersion)
                .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
                .order_by(RefDocumentTypeVersion.valid_from.desc())
            )
        ).scalars().first()

        return {
            "version": asdict(cls._version()),
            "context_echo": asdict(context),
            "profile": {
                "document_code": str(doc_type.code),
                "category": str(doc_type.category_code or ""),
                "criticality": str(doc_type.criticality or ""),
                "document_type_id": str(doc_type.id),
                "document_type_version_id": str(ver.id) if ver else None,
                "required_fields": list((ver.schema_json or {}).get("required") or []) if ver else [],
                "verification_profile": dict(ver.verification_profile_json or {}) if ver else {},
                "expiry_rules": dict(ver.expiry_rules_json or {}) if ver else {},
            },
            "errors": [],
        }

    @classmethod
    async def get_country_profile(
        cls,
        db: AsyncSession,
        *,
        country_code: str,
        context: ReferenceContext,
    ) -> dict[str, Any]:
        _ = db
        cc = str(country_code or "").strip().upper()
        item = get_country_by_alpha2(cc)
        if not item:
            return {
                "version": asdict(cls._version()),
                "context_echo": asdict(context),
                "profile": None,
                "errors": [{"code": "country_not_found", "message": cc}],
            }
        eu = {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE",
            "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        }
        return {
            "version": asdict(cls._version()),
            "context_echo": asdict(context),
            "profile": {
                "country_code": cc,
                "label": item.name,
                "alpha3": item.code_alpha3,
                "numeric": item.code_numeric,
                "groups": {
                    "eu": cc in eu,
                    "non_eu": cc not in eu,
                },
            },
            "errors": [],
        }

    @classmethod
    async def list_enabled_document_pack_codes(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
    ) -> list[str]:
        tid = str(tenant_id).strip()
        rows = (
            await db.execute(
                select(RefPack.code)
                .join(
                    TenantDocumentPackEnablement,
                    TenantDocumentPackEnablement.pack_id == RefPack.id,
                )
                .where(TenantDocumentPackEnablement.tenant_id == tid)
                .where(TenantDocumentPackEnablement.enabled.is_(True))
                .where(RefPack.status == "active")
                .order_by(RefPack.code.asc())
            )
        ).all()
        return [str(row[0]) for row in rows]

    @classmethod
    async def get_document_runtime_profile(
        cls,
        db: AsyncSession,
        *,
        document: Any,
        context: ReferenceContext,
    ) -> dict[str, Any]:
        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(db, document)
        return {
            "version": asdict(cls._version()),
            "context_echo": asdict(context),
            "profile": {
                "document_id": str(getattr(document, "id", "") or ""),
                "canonical_code": resolved.canonical_code,
                "category": resolved.category_code,
                "criticality": resolved.compliance_criticality,
                "document_type_id": resolved.canonical_document_type_id,
                "document_type_version_id": resolved.document_type_version_id,
                "fallback_used": bool(resolved.fallback_used),
                "fallback_source": resolved.fallback_source,
            },
            "errors": [],
        }
