"""Recruitment public process contracts.

Foreign modules may import **submodules** of this package only
(``recruitment.public.access``, ``.ready``, ``.models``, …).

Do not eagerly re-export here — that creates import cycles with Boundary/handoff.
Internal evaluators, R5/slots/confirmations, and Ready machinery stay private.
"""

from __future__ import annotations

__all__: list[str] = []
