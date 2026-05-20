#!/usr/bin/env bash
# PR15 backend regression (hybrid approve gate; run after PR-INFRA for safe email).
set -euo pipefail
cd "$(dirname "$0")/../backend"
export PYTHONPATH="${PYTHONPATH:-}:$(dirname "$PWD")"
export EMAIL_DELIVERY_MODE="${EMAIL_DELIVERY_MODE:-mock}"
python3 -m pytest \
  tests/services/test_hr_verification_plan.py \
  tests/services/test_hr_verification_waiver_gate.py \
  tests/services/test_hr_review_document_resolution.py \
  tests/api/test_hr_review_document_sot.py \
  tests/api/test_hr_verification_pr15_e2e.py \
  -q "$@"
