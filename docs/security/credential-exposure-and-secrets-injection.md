# Credential exposure — measured finding and rotation contract

**Status:** **OPEN — P0**
**Opened:** 2026-08-31
**Owner:** Security owner (rotation) + Engineering lead (injection mechanism)
**Parents:** [security-ssot.md](./security-ssot.md) · [README.md](./README.md) · [Operate & Launch](../specs/tasks/operate-and-launch.md) (OL-2 owns the deploy-time injection mechanism)

> This document records **exposure paths and credential classes only**. It contains no secret values,
> no prefixes and no fragments, and nothing added to it may contain them. Everything below was
> established without printing a single value.

---

## 1. Finding

Two environment files on the production host carry live third-party credentials, and one of them is
copied into an immutable container image layer.

| # | Exposure path | Measured how | Severity |
|---|---|---|---|
| **E-1** | `backend/.env` is **baked into the `hostflow-backend` image**. `backend/Dockerfile` runs `COPY . /app`; `docker-compose.yml` builds with `context: ./backend`; Docker resolves `.dockerignore` relative to the build context, so the repo-root `.dockerignore` (which does exclude `.env`) never applied. | Ran the built image with **no bind mounts**: `/app/.env` present inside the image. | **Critical** — an image layer is immutable and travels with every copy, export and registry push |
| **E-2** | `backend/.env` sits inside `/opt/HostFlow/backend`, which is bind-mounted **read-write** into the running container at `/app`. | `docker inspect` mount table; `ls` inside the running container. | High — application process can read *and rewrite* its own secret store |
| **E-3** | Both `.env` and `backend/.env` are mode **644** (world-readable) on a public-facing host. | `stat` on each file. | High — any local account or any process can read them |
| **E-4** | The trusted-base checkout is the production runtime, so the secret files share a directory tree with development work and 50+ worktrees. | Recorded in [Operate & Launch § Starting point](../specs/tasks/operate-and-launch.md). | Medium — widens who and what can reach the files |

**Not exposed (checked, negative):** the frontend. `hostflow-frontend/.env.production*` define only
`VITE_API_BASE` / `VITE_AUTH_BASE`, and no secret material was found in the built `dist/`. Vite embeds
`VITE_*` into the browser bundle, so this must be re-checked whenever a `VITE_` variable is added.

## 2. Credential classes in scope

Classes only — see the files themselves for names, and never quote values.

| Class | Present in | Rotation authority |
|---|---|---|
| Payment provider secret key (**live mode**) | `.env`, `backend/.env` | Payment provider dashboard |
| Payment webhook signing secret | `.env`, `backend/.env` | Payment provider dashboard |
| Messaging provider access token (**live**, test mode disabled) | `.env`, `backend/.env` | Messaging provider console |
| Messaging callback secret | `.env`, `backend/.env` | Messaging provider console |
| SMTP account password | `backend/.env` | Mail provider |
| Two calendar OAuth client secrets | `backend/.env` | Each identity provider |
| Social lead-integration app secret | `backend/.env` | Integration provider |
| Web-push VAPID private key | `backend/.env` | Regenerate locally; invalidates existing push subscriptions |
| Application signing secrets (JWT / session / webhook verify) | `.env`, `backend/.env` | Regenerate locally; invalidates issued tokens |
| Database password | `.env` | Rotate in PostgreSQL |

Live mode was established from the provider's documented key-class prefix and from the messaging
provider's test-mode flag being disabled — **by counting matches, not by printing them**.

## 3. Decision: treat as exposed

Per the operating rule for this finding: where credentials are reachable by processes and artefacts
that do not need them, they are **potentially exposed**, and the response is rotation. Do not attempt
to prove after the fact that nobody read them — image layers, host accounts and any registry copy are
not auditable to that standard.

## 4. Remediation sequence (order matters)

| Step | Action | State |
|---|---|---|
| **R-1** | Stop future builds from baking the file — add `backend/.dockerignore`. | **DONE** 2026-08-31 (`2408a5a0`). Verified: `/app/.env` absent from a rebuilt image, `.env.example` retained, app code intact |
| **R-2** | Move secrets out of the checkout to a path outside every build context and bind mount, readable only by the runtime account (`0600`), referenced by compose `env_file:` with an absolute path or injected by the orchestrator. | **TODO** — OL-2 owns the mechanism; production-affecting, needs a restart window |
| **R-3** | Tighten permissions on whatever remains: `chmod 600`, correct ownership. | **DONE** 2026-08-31 — `.env`, `backend/.env`, `.env.local` moved 644 → 600. No process restart needed (permissions do not affect an already-running process; Docker reads the files as root). Verified after: all five containers up, `/healthz` 200. Ownership is still UID 501 / GID 50, an account that does not exist on this host — correcting that belongs with R-2 |
| **R-4** | Rebuild and redeploy the backend image so no running artefact contains the file. | **TODO** — requires R-2; production-affecting |
| **R-5** | **Rotate every class in § 2**, in provider dashboards where applicable. Rotation is only meaningful after R-2/R-4, or the new values land in the same exposed places. | **TODO** — requires provider access the repository does not have |
| **R-6** | Invalidate old values at the provider (revoke, not merely replace) and confirm the application still functions on the new ones. | **TODO** |
| **R-7** | Purge or re-tag local/registry images built before R-1 that contain the file. | **TODO** — enumerate before deleting |

**Ordering trap to avoid:** rotating first (R-5 before R-2/R-4) writes fresh live credentials into the
same world-readable file inside the same build context, and the new values are exposed the moment the
image is rebuilt. R-2 and R-4 must precede R-5.

## 5. What this document does not claim

- It does not claim the credentials were read by anyone. That is unprovable and is not the bar.
- It does not claim R-1 remediates the exposure. R-1 only stops it recurring; existing image layers
  are unchanged.
- It does not schedule OL-2. The injection mechanism is OL-2's to build; the rotation is the security
  owner's to execute, and neither is closed by this record.

## 6. History

- 2026-08-31: Opened. E-1…E-4 measured on the production host without printing values; R-1 landed and
  verified; R-3 applied (644 → 600 on three files, production verified healthy afterwards);
  R-2, R-4…R-7 outstanding. E-3 is reduced but **not closed** — the files are still inside the build
  context and the bind mount, which is what R-2 addresses.
