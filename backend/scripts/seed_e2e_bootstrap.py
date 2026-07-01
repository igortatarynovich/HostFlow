#!/usr/bin/env python3
"""Seed pytest bootstrap tenant/users for Playwright HR API e2e (idempotent)."""

from __future__ import annotations

import asyncio
import json
import sys


async def _run() -> dict[str, str]:
    from backend.tests.conftest import _init_data

    return await _init_data()


def main() -> int:
    data = asyncio.run(_run())
    print(json.dumps({k: str(v) for k, v in data.items() if v is not None}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
