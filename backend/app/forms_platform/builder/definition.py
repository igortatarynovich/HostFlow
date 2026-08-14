"""Forms Platform C3 — FormDefinition (the only model Builder may mutate)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.forms_platform.builder.composition import FormDraftComposition
from backend.app.forms_platform.errors import FormsBuilderCompositionInvalidError

BUILDER_DEFINITION_CONTRACT = "forms.builder.form_definition.v1"


@dataclass(frozen=True, slots=True)
class FormDefinition:
    """Mutable definition document. Not a publication. No Contract Identity."""

    definition_id: str
    composition: FormDraftComposition

    def __post_init__(self) -> None:
        did = str(self.definition_id or "").strip()
        if not did:
            raise FormsBuilderCompositionInvalidError(details={"reason": "empty_definition_id"})
        if self.composition.draft_id != did:
            raise FormsBuilderCompositionInvalidError(
                details={
                    "reason": "definition_id_mismatch",
                    "definition_id": did,
                    "composition_draft_id": self.composition.draft_id,
                },
            )
        object.__setattr__(self, "definition_id", did)

    def replace_composition(self, composition: FormDraftComposition) -> FormDefinition:
        return FormDefinition(definition_id=self.definition_id, composition=composition)
