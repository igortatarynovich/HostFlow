#!/usr/bin/env python3
"""
Phase 0 #7: coverage ratchet gate for the backend test suite.

Why a custom script (instead of ``--cov-fail-under=X``):

*   Makes the baseline explicit in the repo (``.coverage-baseline``) so
    bumping the floor is a reviewable commit rather than a change nobody
    notices.
*   Gives clear ratchet semantics: "never drop below the committed baseline
    (minus a tiny tolerance)" — the number can be raised whenever a PR lands
    genuinely new tests.
*   Works with either ``coverage.xml`` or ``.coverage`` (SQLite) emitted by
    ``coverage.py``/``pytest-cov``.
*   Prints the gap to the aspirational target so CI readers see both the
    hard floor and the north star.

Usage::

    python backend/scripts/check_coverage.py                   # default paths
    python backend/scripts/check_coverage.py --coverage path.xml --baseline 0.40
    python backend/scripts/check_coverage.py --write-baseline  # ratchet up
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
REPO_ROOT = BACKEND_ROOT.parent

# Defaults mirror `backend/.coveragerc` + layout.
DEFAULT_COVERAGE_XML = BACKEND_ROOT / "coverage.xml"
DEFAULT_BASELINE_FILE = BACKEND_ROOT / ".coverage-baseline"
DEFAULT_TOLERANCE_PP = 0.5  # percentage-points — absorbs rounding / minor flake.
DEFAULT_TARGET_PERCENT = 60.0  # audit plan aspirational backend target.


def _read_baseline(path: Path) -> float:
    if not path.is_file():
        raise SystemExit(f"[check_coverage] baseline file not found: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise SystemExit(f"[check_coverage] baseline file is empty: {path}")
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(
            f"[check_coverage] baseline file must contain a single float "
            f"(got {raw!r}): {path}"
        ) from exc


def _measure_from_xml(xml_path: Path) -> float:
    """Return overall coverage as a percentage (0-100) from Cobertura XML."""
    if not xml_path.is_file():
        raise SystemExit(
            f"[check_coverage] coverage report not found: {xml_path}\n"
            "Run `pytest --cov=backend/app --cov-report=xml:backend/coverage.xml` first."
        )
    tree = ET.parse(xml_path)
    root = tree.getroot()
    rate = root.get("line-rate")
    if rate is None:
        raise SystemExit(
            f"[check_coverage] 'line-rate' attribute missing from {xml_path}"
        )
    try:
        return float(rate) * 100.0
    except ValueError as exc:
        raise SystemExit(
            f"[check_coverage] malformed line-rate={rate!r} in {xml_path}"
        ) from exc


def _measure_from_coverage_db(db_path: Path) -> Optional[float]:
    """Fallback: read percentage straight from coverage.py's SQLite file."""
    try:
        import coverage  # type: ignore
    except ImportError:
        return None
    if not db_path.exists():
        return None
    cov = coverage.Coverage(data_file=str(db_path))
    cov.load()
    return cov.report(show_missing=False, file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage",
        default=str(DEFAULT_COVERAGE_XML),
        help="Path to coverage.xml (Cobertura format). Default: backend/coverage.xml",
    )
    parser.add_argument(
        "--baseline-file",
        default=str(DEFAULT_BASELINE_FILE),
        help="Path to the committed baseline file. Default: backend/.coverage-baseline",
    )
    parser.add_argument(
        "--baseline",
        type=float,
        default=None,
        help="Override the baseline percentage explicitly (overrides --baseline-file).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE_PP,
        help=f"Allowed drop below baseline, in percentage points. Default: {DEFAULT_TOLERANCE_PP}",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=DEFAULT_TARGET_PERCENT,
        help=f"Aspirational target (informational only). Default: {DEFAULT_TARGET_PERCENT}",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="When current coverage exceeds the baseline, rewrite the baseline file.",
    )
    args = parser.parse_args(argv)

    xml_path = Path(args.coverage)
    baseline_file = Path(args.baseline_file)

    baseline = args.baseline if args.baseline is not None else _read_baseline(baseline_file)
    measured = _measure_from_xml(xml_path)

    status = "OK"
    floor = baseline - args.tolerance
    dropped = measured + 1e-9 < floor

    # Pretty summary — one line per field so CI log search is easy.
    print("=" * 60)
    print("Phase 0 #7 — backend coverage gate")
    print("-" * 60)
    print(f"measured : {measured:6.2f} %")
    print(f"baseline : {baseline:6.2f} %  (from {baseline_file.name})")
    print(f"floor    : {floor:6.2f} %  (baseline - tolerance {args.tolerance}pp)")
    print(f"target   : {args.target:6.2f} %  (audit plan north star)")
    print("=" * 60)

    if dropped:
        status = "FAIL"
        print(
            f"[check_coverage] FAIL — coverage {measured:.2f}% dropped below "
            f"the floor {floor:.2f}% (baseline {baseline:.2f}%)."
        )
        print(
            "  → Either add tests to restore coverage, or if the drop is "
            "intentional (e.g. large refactor removed dead code), explicitly "
            "lower the baseline in a reviewable commit."
        )
        return 1

    if args.write_baseline and measured > baseline + args.tolerance:
        # Ratchet: commit the improved floor so future PRs cannot slide back.
        new_baseline = round(measured - args.tolerance, 2)
        baseline_file.write_text(f"{new_baseline:.2f}\n", encoding="utf-8")
        print(
            f"[check_coverage] ratcheted baseline {baseline:.2f}% → "
            f"{new_baseline:.2f}% in {baseline_file.name}"
        )

    if measured + 1e-9 < args.target:
        gap = args.target - measured
        print(
            f"[check_coverage] {status} — {gap:.2f}pp below the audit-plan "
            f"target of {args.target:.2f}%."
        )
    else:
        print(f"[check_coverage] {status} — target {args.target:.2f}% met or exceeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
