#!/usr/bin/env bash
# Back-compat wrapper. Caddy serves ./hostflow-frontend/dist via bind-mount,
# not the host path /var/www/hostflow-frontend. Delegates to the live deploy.
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/scripts/deploy/deploy-live.sh" --frontend-only "$@"
