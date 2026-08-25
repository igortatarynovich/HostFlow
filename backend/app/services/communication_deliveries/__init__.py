"""Communication delivery services.

Keep package import light: do not eagerly import questionnaire_email (it pulls
the Communications Intent stack). Import symbols from submodule paths instead.
"""

from __future__ import annotations

__all__ = [
    "QuestionnaireEmailError",
    "compose_questionnaire_invite_email",
    "send_questionnaire_invite_email",
]


def __getattr__(name: str):
    if name in __all__:
        from backend.app.services.communication_deliveries import questionnaire_email as _mod

        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
