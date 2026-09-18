"""Boundary public process contracts.

Narrow ownership: accept Recruitment public output, handoff/traceability,
deliver Ready-for-Employment input to Employment.

Does **not** own Recruitment Ready, Employment Admit, Documents rules,
or Workforce lifecycle. Foreign modules import **submodules** only.
"""

from __future__ import annotations

__all__: list[str] = []
