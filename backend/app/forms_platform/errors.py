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
