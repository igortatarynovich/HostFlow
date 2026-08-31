#!/usr/bin/env bash
# Measure the backend known-failure baseline (QB-1) reproducibly: fresh scratch DB, full suite,
# sorted failure list. See docs/specs/tasks/stabilize-integration-pytest-baseline.md.
#
# Reusing a database changes the answer: some tests need state an earlier run left behind and
# others assert it is absent, so the count only matches when every run starts from one schema.
# The schema is cloned from an already-migrated database because `alembic upgrade heads` does not
# apply to an empty database yet (owned by OL-2 in docs/specs/tasks/operate-and-launch.md).
#
# Usage: scripts/testing/measure-known-failures.sh [output-file]
#   SOURCE_DB   database to clone the schema from   (default: hostflow)
#   SCRATCH_DB  database to create and test against (default: hostflow_baseline_test)
set -euo pipefail

cd "$(dirname "$0")/../.."

OUTPUT="${1:-/tmp/known-failures-$(date +%Y%m%d-%H%M%S).txt}"
SOURCE_DB="${SOURCE_DB:-hostflow}"
SCRATCH_DB="${SCRATCH_DB:-hostflow_baseline_test}"

# backend/tests/conftest.py refuses to run against a database whose name does not look like a
# test database; fail here with a clear message rather than deep inside collection.
case "$SCRATCH_DB" in
  *test*) ;;
  *) echo "SCRATCH_DB must contain 'test' (got '$SCRATCH_DB')" >&2; exit 2 ;;
esac
if [[ "$SCRATCH_DB" == "$SOURCE_DB" ]]; then
  echo "SCRATCH_DB must differ from SOURCE_DB ('$SOURCE_DB')" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1091
[[ -f .env ]] && . ./.env
set +a

PGHOST="${PGHOST:-localhost}"
PGUSER="${PGUSER:-hostflow}"
export PGHOST PGUSER PGPASSWORD="${PGPASSWORD:-hostflow}"

echo "Recreating $SCRATCH_DB from the schema of $SOURCE_DB ..."
psql -q -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH_DB;" -c "CREATE DATABASE $SCRATCH_DB OWNER $PGUSER;"
pg_dump --schema-only --no-owner --no-privileges -d "$SOURCE_DB" | psql -q -d "$SCRATCH_DB"
pg_dump --data-only --table=alembic_version -d "$SOURCE_DB" | psql -q -d "$SCRATCH_DB"

for var in DATABASE_URL ASYNC_DATABASE_URL SYNC_DATABASE_URL ALEMBIC_DATABASE_URL; do
  value="${!var:-}"
  [[ -n "$value" ]] && export "$var=${value%/$SOURCE_DB}/$SCRATCH_DB"
done

echo "Running the full suite (expect ~11 minutes) ..."
PYTHONPATH="$PWD:$PWD/backend" COLUMNS=400 \
  python3 -m pytest -q --tb=no -rf -p no:cacheprovider -c backend/pytest.ini backend/tests \
  > "$OUTPUT" 2>&1 || true

tail -1 "$OUTPUT"
grep '^FAILED ' "$OUTPUT" | sed 's/^FAILED //; s/ - .*//' | sort -u > "$OUTPUT.ids"
echo "Full log: $OUTPUT"
echo "Failure ids ($(wc -l < "$OUTPUT.ids")): $OUTPUT.ids"
