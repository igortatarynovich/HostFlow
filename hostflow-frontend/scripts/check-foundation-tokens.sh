#!/usr/bin/env bash
# FOUNDATION_V1 enforcement: block new deprecated Tailwind foundation tokens in PR diffs.
# Full codebase scan (--scan) is informational only (migration backlog).
#
# Spec: docs/specs/frontend/FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md
#
# Usage:
#   ./scripts/check-foundation-tokens.sh              # diff vs base (CI default)
#   ./scripts/check-foundation-tokens.sh --diff       # same
#   ./scripts/check-foundation-tokens.sh --scan       # full src scan (non-blocking)
#   FOUNDATION_DIFF_BASE=origin/develop ./scripts/check-foundation-tokens.sh
#
# Suppress only with reason: foundation-allow: <why, min 8 chars> (same line or line above).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep '^#' "$0" | head -14 | sed 's/^# \{0,1\}//'
  exit 0
fi

if [[ "${1:-}" == "--scan" ]]; then
  exec python3 "$ROOT/scripts/check_foundation_tokens_scan.py"
fi

export FOUNDATION_DIFF_BASE="${FOUNDATION_DIFF_BASE:-origin/main}"
exec python3 "$ROOT/scripts/check_foundation_tokens_diff.py"
