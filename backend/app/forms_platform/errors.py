"""Forms Adapter / publication error taxonomy (Sprint 2)."""

from __future__ import annotations

from typing import Any


class FormsAdapterError(Exception):
    """Typed Forms Sprint 2 adapter error."""

    code: str = "forms_adapter_error"
    http_status: int = 400
    default_message: str = "Forms adapter error"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        msg = message if message is not None else self.default_message
        super().__init__(msg)
        self.message = msg
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "http_status": self.http_status,
        }


class FormsNotFoundError(FormsAdapterError):
    code = "forms_publication_not_found"
    http_status = 404
    default_message = "Form publication not found"


class FormsInactiveError(FormsAdapterError):
    code = "forms_endpoint_inactive"
    http_status = 409
    default_message = "Form endpoint is inactive"


class FormsArchivedError(FormsAdapterError):
    code = "forms_publication_archived"
    http_status = 409
    default_message = "Form publication is archived"


class FormsStaleVersionError(FormsAdapterError):
    code = "forms_stale_published_version"
    http_status = 409
    default_message = "Submission published_version does not match pin"


class FormsAmbiguousKeyError(FormsAdapterError):
    code = "forms_publication_key_ambiguous"
    http_status = 422
    default_message = "Provide form_id or public_slug, not both conflicting"


class FormsMissingKeyError(FormsAdapterError):
    code = "forms_publication_key_required"
    http_status = 422
    default_message = "form_id or public_slug is required"


class FormsBuilderLockedError(FormsAdapterError):
    code = "forms_builder_locked"
    http_status = 403
    default_message = "Forms Builder is locked"


class FormsVersionPinnedError(FormsAdapterError):
    code = "forms_publication_version_pinned"
    http_status = 409
    default_message = "Publication version has submission pins and cannot be mutated or deleted"


class FormsVersionNotFoundError(FormsAdapterError):
    code = "forms_publication_version_not_found"
    http_status = 404
    default_message = "Publication version not found"


class FormsEnvelopeNotFoundError(FormsAdapterError):
    code = "forms_submission_envelope_not_found"
    http_status = 404
    default_message = "Submission envelope not found"


class FormsEnvelopeImmutableError(FormsAdapterError):
    code = "forms_submission_envelope_immutable"
    http_status = 409
    default_message = "Submission envelope content is immutable"


class FormsEnvelopeStatusError(FormsAdapterError):
    code = "forms_submission_envelope_status_invalid"
    http_status = 422
    default_message = "Invalid submission envelope processing status"


# --- Field Catalog P1.1 ---


class FormsCatalogComponentDuplicateError(FormsAdapterError):
    code = "forms_catalog_component_duplicate"
    http_status = 409
    default_message = "Component version already registered"


class FormsCatalogComponentNotFoundError(FormsAdapterError):
    code = "forms_catalog_component_not_found"
    http_status = 404
    default_message = "Catalog component not found"


class FormsCatalogVersionIncompatibleError(FormsAdapterError):
    code = "forms_catalog_version_incompatible"
    http_status = 409
    default_message = "Catalog component version is incompatible"


class FormsCatalogVersionInvalidError(FormsAdapterError):
    code = "forms_catalog_version_invalid"
    http_status = 422
    default_message = "Catalog component version must be semver MAJOR.MINOR.PATCH"


# --- Field Catalog P1.2 ---


class FormsCatalogDescriptorMissingError(FormsAdapterError):
    code = "forms_catalog_descriptor_missing"
    http_status = 404
    default_message = "Catalog component descriptor is missing"


class FormsCatalogDescriptorInvalidError(FormsAdapterError):
    code = "forms_catalog_descriptor_invalid"
    http_status = 422
    default_message = "Catalog component descriptor is invalid"


class FormsCatalogDescriptorUnsupportedError(FormsAdapterError):
    code = "forms_catalog_descriptor_unsupported"
    http_status = 422
    default_message = "Catalog component descriptor kind is unsupported"


# --- Field Catalog P1.4 ---


class FormsCatalogBasicOverrideError(FormsAdapterError):
    code = "forms_catalog_basic_override_forbidden"
    http_status = 409
    default_message = "Basic Standard Library components cannot be overridden"


class FormsCatalogExtensionModuleInvalidError(FormsAdapterError):
    code = "forms_catalog_extension_module_invalid"
    http_status = 422
    default_message = "Extension module_id is invalid"


# --- Builder P2.2 Composition ---


class FormsBuilderCompositionInvalidError(FormsAdapterError):
    code = "forms_builder_composition_invalid"
    http_status = 422
    default_message = "Builder composition is invalid"


class FormsBuilderCompositionConfigError(FormsAdapterError):
    code = "forms_builder_composition_config_invalid"
    http_status = 422
    default_message = "Builder instance config is invalid"


class FormsBuilderCompositionCommandError(FormsAdapterError):
    code = "forms_builder_composition_command_invalid"
    http_status = 422
    default_message = "Builder composition command is invalid"


# --- Builder P2.4 Draft Persistence ---


class FormsBuilderDraftNotFoundError(FormsAdapterError):
    code = "forms_builder_draft_not_found"
    http_status = 404
    default_message = "Builder draft not found"


class FormsBuilderDraftConflictError(FormsAdapterError):
    code = "forms_builder_draft_revision_conflict"
    http_status = 409
    default_message = "Builder draft revision conflict"


class FormsBuilderDraftArchivedError(FormsAdapterError):
    code = "forms_builder_draft_archived"
    http_status = 409
    default_message = "Builder draft is archived"


class FormsBuilderStateError(FormsAdapterError):
    """Illegal Builder state-machine transition (C3). Not an Adapter error surface."""

    code = "forms_builder_state_invalid"
    http_status = 409
    default_message = "Builder draft state transition is not allowed"


# --- Intake Runtime Split R1 ---


class FormsRoutingUnresolvedError(FormsAdapterError):
    """Fail-closed: missing/unknown route_intent — no Recruitment/Sales dispatch."""

    code = "forms_routing_unresolved"
    http_status = 422
    default_message = "Submission route_intent is unresolved (fail-closed)"


# --- Forms Platform C2 — runtime contract ---


class FormsIdentityIncompleteError(FormsAdapterError):
    code = "forms_contract_identity_incomplete"
    http_status = 422
    default_message = "Publication version is missing Contract Identity"


class FormsIdentityIncompatibleError(FormsAdapterError):
    code = "forms_contract_identity_incompatible"
    http_status = 409
    default_message = "Contract Identity combination is not declared compatible"


class FormsSchemaHashMismatchError(FormsAdapterError):
    code = "forms_schema_hash_mismatch"
    http_status = 409
    default_message = "schema_hash does not match canonical frozen field_schema"


class FormsPublicationVersionImmutableError(FormsAdapterError):
    code = "forms_publication_version_immutable"
    http_status = 409
    default_message = "Publication version schema and Contract Identity cannot be mutated"


class FormsIdentityUnreconstructableError(FormsAdapterError):
    code = "forms_contract_identity_unreconstructable"
    http_status = 422
    default_message = "Legacy publication snapshot cannot reconstruct Contract Identity"


# --- Forms Platform C4 — Form Runtime ---


class FormsRuntimeNotPublicationError(FormsAdapterError):
    code = "forms_runtime_not_publication"
    http_status = 422
    default_message = "Form Runtime serves a frozen FormPublicationVersion only"


# --- Forms Platform C5 — Form Execution ---


class FormsExecutionRequiresRuntimeModelError(FormsAdapterError):
    code = "forms_execution_requires_runtime_model"
    http_status = 422
    default_message = "Form Execution requires a Runtime Model"
