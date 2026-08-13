#!/usr/bin/env python3
"""ADR-043 P0 — lower-only UI kit ratchet.

Freezes today's violation counts. A PR may only lower a metric (or keep it
equal). Hard-fails (not ratcheted):

  * `@tabler/icons-react` inside `src/components/ui/`
  * `.app-ui` descendant `border-radius: 0 !important`

Usage:
  python3 scripts/check_ui_kit_ratchet.py              # CI default
  python3 scripts/check_ui_kit_ratchet.py --write       # refresh baseline
  python3 scripts/check_ui_kit_ratchet.py --report      # print counts, exit 0

Suppress a line with: ui-kit-allow: <reason, min 8 chars>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
SRC = FRONTEND_ROOT / "src"
CSS = FRONTEND_ROOT / "src" / "styles" / "components.css"
BASELINE_PATH = FRONTEND_ROOT / "scripts" / "ui-kit-ratchet-baseline.json"

SRC_SUFFIXES = {".ts", ".tsx", ".css"}
SKIP_DIR_PARTS = {"__tests__", "node_modules", "__generated__"}

TABLER_RE = re.compile(r"""from\s+['"]@tabler/icons-react['"]|require\(\s*['"]@tabler/icons-react['"]""")
HEX_RE = re.compile(r"(?<![0-9A-Fa-f])#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
BUTTON_RE = re.compile(r"<button\b")
TABLE_RE = re.compile(r"<table\b")
GRADIENT_RE = re.compile(r"\bbg-gradient-")
ROUNDED_RE = re.compile(r"\brounded-(?:none|sm|md|lg|xl|2xl|3xl)\b")
ALLOW_RE = re.compile(r"ui-kit-allow:\s*\S{8,}")
IMPORTANT_RADIUS_RE = re.compile(
    r"\.app-ui\s+\*:not\(\[class\*='rounded-full'\]\)\s*\{[^}]*border-radius:\s*0\s*!important",
    re.S,
)

HEX_ALLOW_PREFIXES = (
    "platform/icons/visualAssets.generated.ts",
    "assets/",
    "App.css",
    "pages/public/",
    "pages/Login.tsx",
    "pages/SignupPage.tsx",
    "pages/ForgotPasswordPage.tsx",
    "pages/ResetPasswordPage.tsx",
    "pages/InviteAcceptPage.tsx",
)

TABLER_ALLOW_PREFIXES = ("platform/icons/",)

PRODUCT_PREFIXES = ("pages/", "modules/")
KIT_PREFIX = "components/ui/"


def rel(path: Path) -> str:
    return path.relative_to(SRC).as_posix()


def is_skipped(path: Path) -> bool:
    if path.suffix not in SRC_SUFFIXES or not path.is_file():
        return True
    if any(part in SKIP_DIR_PARTS for part in path.parts):
        return True
    name = path.name
    if name.endswith(".test.ts") or name.endswith(".test.tsx") or name.endswith(".d.ts"):
        return True
    return False


def strip_allowed_lines(text: str) -> str:
    kept: list[str] = []
    prev = ""
    for line in text.splitlines():
        if ALLOW_RE.search(line) or ALLOW_RE.search(prev):
            prev = line
            continue
        kept.append(line)
        prev = line
    return "\n".join(kept)


def starts_with(rel_path: str, prefixes: tuple[str, ...]) -> bool:
    return any(rel_path == p.rstrip("/") or rel_path.startswith(p) for p in prefixes)


def iter_src_files() -> list[Path]:
    return [p for p in sorted(SRC.rglob("*")) if not is_skipped(p)]


def count_matches(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text))


def scan() -> dict[str, int]:
    tabler_outside = 0
    hex_outside = 0
    product_buttons = 0
    product_tables = 0
    gradients = 0
    rounded_product = 0

    for path in iter_src_files():
        key = rel(path)
        text = strip_allowed_lines(path.read_text(encoding="utf-8", errors="ignore"))

        if not starts_with(key, TABLER_ALLOW_PREFIXES):
            tabler_outside += count_matches(TABLER_RE, text)

        if not starts_with(key, HEX_ALLOW_PREFIXES):
            hex_outside += count_matches(HEX_RE, text)

        if starts_with(key, PRODUCT_PREFIXES):
            product_buttons += count_matches(BUTTON_RE, text)
            product_tables += count_matches(TABLE_RE, text)
            rounded_product += count_matches(ROUNDED_RE, text)

        if not starts_with(key, ("pages/public/", "styles/")):
            gradients += count_matches(GRADIENT_RE, text)

    return {
        "tabler_imports_outside_registry": tabler_outside,
        "raw_hex_outside_allowlist": hex_outside,
        "product_intrinsic_button": product_buttons,
        "product_handwritten_table": product_tables,
        "gradients_outside_allowlist": gradients,
        "product_rounded_utility": rounded_product,
    }


def kit_tabler_violations() -> list[str]:
    hits: list[str] = []
    kit = SRC / "components" / "ui"
    if not kit.is_dir():
        return hits
    for path in sorted(kit.rglob("*")):
        if is_skipped(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if TABLER_RE.search(text):
            hits.append(rel(path))
    return hits


def load_baseline() -> dict[str, int]:
    if not BASELINE_PATH.is_file():
        print(f"check_ui_kit_ratchet: baseline missing: {BASELINE_PATH}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("check_ui_kit_ratchet: baseline must be a JSON object", file=sys.stderr)
        sys.exit(2)
    return {k: int(v) for k, v in data.items()}


def write_baseline(counts: dict[str, int]) -> None:
    BASELINE_PATH.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_counts(counts: dict[str, int], title: str) -> None:
    print(title)
    width = max(len(k) for k in counts)
    for key in sorted(counts):
        print(f"  {key.ljust(width)}  {counts[key]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite baseline to current counts")
    parser.add_argument("--report", action="store_true", help="print counts and exit 0")
    args = parser.parse_args()

    hard_errors: list[str] = []

    css_text = CSS.read_text(encoding="utf-8") if CSS.is_file() else ""
    if IMPORTANT_RADIUS_RE.search(css_text):
        hard_errors.append("components.css still contains .app-ui descendant border-radius: 0 !important")

    kit_tabler = kit_tabler_violations()
    if kit_tabler:
        hard_errors.append("UI kit imports @tabler/icons-react: " + ", ".join(kit_tabler))

    counts = scan()

    if hard_errors:
        print("check_ui_kit_ratchet: HARD FAIL")
        for item in hard_errors:
            print(f"  - {item}")
        return 1

    if args.write:
        write_baseline(counts)
        print_counts(counts, "Wrote UI kit ratchet baseline:")
        print(f"  → {BASELINE_PATH.relative_to(FRONTEND_ROOT)}")
        return 0

    if args.report:
        print_counts(counts, "UI kit ratchet (current):")
        return 0

    baseline = load_baseline()
    missing = [k for k in counts if k not in baseline]
    extra = [k for k in baseline if k not in counts]
    if missing or extra:
        print("check_ui_kit_ratchet: baseline keys drifted")
        if missing:
            print("  missing in baseline:", ", ".join(missing))
        if extra:
            print("  extra in baseline:", ", ".join(extra))
        print("  Re-run with --write after review.")
        return 1

    regressions = []
    improvements = []
    for key, current in counts.items():
        floor = baseline[key]
        if current > floor:
            regressions.append(f"{key}: {current} > baseline {floor}")
        elif current < floor:
            improvements.append(f"{key}: {floor} → {current} (ratchet down with --write)")

    print_counts(counts, "UI kit ratchet (ADR-043 P0):")
    if improvements:
        print("Lower than baseline (update with --write when intentional):")
        for item in improvements:
            print(f"  {item}")

    if regressions:
        print("FAIL — counts rose (migrate-on-touch; do not add new violations):")
        for item in regressions:
            print(f"  {item}")
        return 1

    print("OK — no metric rose.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
