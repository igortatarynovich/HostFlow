# Object Storage (Phase 0 #6)

## Why

Historically every HostFlow upload (candidate documents, tenant branding,
scanner artefacts, user avatars) landed under `backend/uploads/<...>` and was
served by a FastAPI route `GET /uploads/<path>`. That layout has three
problems at scale:

1. **No durability guarantee** — a single pod/VM owns the files. Losing the
   disk = losing documents.
2. **Horizontal scaling is blocked** — running a second API replica would
   split reads between nodes.
3. **No presigned access** — we have no way to hand a URL to a client that
   expires and doesn't go through our app.

Phase 0 introduces an S3-compatible storage layer with a **drop-in filesystem
backend** so the migration is feature-flagged and reversible.

## Architecture

```
call site  ──► app.core.object_storage.get_object_storage()
                      │
                      ├── FilesystemObjectStorage  (backend == "fs", default)
                      │     • writes to  $UPLOAD_DIR/<key>
                      │     • URL:       /uploads/<key>
                      │
                      └── S3ObjectStorage          (backend == "s3")
                            • writes via aioboto3.Session().client("s3").upload_fileobj
                            • URL:  presigned GET (TTL = OBJECT_STORAGE_PRESIGN_EXPIRES_SEC)
                                    or public CDN prefix if OBJECT_STORAGE_PUBLIC_BASE_URL set
```

The abstraction is defined in
[`backend/app/core/object_storage.py`](../../../backend/app/core/object_storage.py):

| method | FS | S3 |
| --- | --- | --- |
| `save_stream(key, reader)` | writes to disk, 8 MiB chunks | `upload_fileobj` (multipart for large files) |
| `save_bytes(key, data)` | `Path.write_bytes` in executor | `put_object` |
| `exists(key)` | `Path.is_file` | `head_object` |
| `delete(key)` | `Path.unlink` | `delete_object` |
| `local_path(key)` | resolved path | **None** (never on disk) |
| `public_url(key)` | `/uploads/<key>` | presigned URL or CDN URL |
| `presigned_get_url(key)` | same as `public_url` | signed URL, TTL configurable |

`normalize_key(...)` is the single entry point for key hygiene: POSIX
separators, no leading slash, no `..`. Every call-site converts its legacy
`os.path.join(...)` into a single call.

The factory is cached per process (`get_object_storage`) and can be reset in
tests via `reset_object_storage()`.

## Configuration

All knobs live on `app.core.settings.Settings` and in `.env.example`:

```
OBJECT_STORAGE_BACKEND=fs                          # "fs" | "s3"
OBJECT_STORAGE_BUCKET=hostflow-uploads
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_ACCESS_KEY_ID=hostflow
OBJECT_STORAGE_SECRET_ACCESS_KEY=hostflow-minio
OBJECT_STORAGE_USE_PATH_STYLE=true                 # MinIO / Ceph RGW / Backblaze
OBJECT_STORAGE_PRESIGN_EXPIRES_SEC=900
OBJECT_STORAGE_PUBLIC_BASE_URL=                    # optional CDN in front of bucket
OBJECT_STORAGE_REDIRECT_UPLOADS_ENDPOINT=true
```

Failure-mode: if `OBJECT_STORAGE_BACKEND=s3` but the bucket is empty or
`aioboto3`/`boto3` are missing, the factory **logs a warning and falls back
to the filesystem backend** instead of taking the whole API down. The startup
log carries an explicit `object_storage initialised fs backend root=...`
line so ops can see the effective selection.

## `/uploads/<key>` endpoint

Legacy clients (and `Document.files[*].url`) still resolve through
`/uploads/<key>`. Behaviour after Phase 0:

* **FS backend** → unchanged: `FileResponse` straight from disk, with
  auto-detected MIME type.
* **S3 backend** → 302-redirect to a presigned URL, or 404 when
  `OBJECT_STORAGE_REDIRECT_UPLOADS_ENDPOINT=false`.

Because `documents.storage._build_public_url(key)` now asks the active
backend for the URL at response-build time, existing rows in `Document.files`
automatically start emitting presigned URLs the moment the backend flips —
no bulk DB update required. A rollback to `fs` works symmetrically.

## Adapted call-sites

Phase 0 adapts the single highest-traffic write flow and all read flows:

* Write: `POST /v1/candidate/{id}/documents/upload`
  (`candidate_documents.py:upload_candidate_document`).
* Read: the `/candidate/{id}/documents/{id}/file` endpoint now returns
  `RedirectResponse` on the S3 backend via the new
  `services.document_files.resolve_document_file_ref` helper.
* Root URL builder: `modules.documents.storage._build_public_url` (touches
  every write path that ultimately funnels through `register_document_upload`).
* Serve path: `main.py:/uploads/<path>`.

Remaining call sites (users.py profile photo, tenant_branding, scanners,
settings/leads, communications attachments, platform/tenants) still write
straight to `UPLOAD_DIR`. They continue to work unchanged under the FS
backend; adapting them to the abstraction is a pure mechanical refactor for
later PRs — a template is in `upload_candidate_document`:

```python
storage = get_object_storage()
saved = await storage.save_stream(key, async_chunks_or_fileobj, content_type=...)
```

## MinIO in docker-compose

```
docker compose --profile minio up -d    # or --profile full
```

Services:

* `minio` — single-node server with console on `127.0.0.1:9001`.
* `minio-bootstrap` — idempotent one-shot that creates
  `OBJECT_STORAGE_BUCKET` and enables anonymous download (safe for dev).

Production buckets (AWS S3, R2, Wasabi) are configured by pointing
`OBJECT_STORAGE_*` at the live endpoint — the code path is identical.

## Migration from legacy FS layout

`backend/scripts/migrate_uploads_to_s3.py` walks `UPLOAD_DIR` and uploads
every file to the configured bucket, preserving the relative path as the
object key. Key points:

* Idempotent — re-runnable; existing objects are skipped unless `--force`.
* `--dry-run` lists what would be uploaded without touching S3.
* **Does not** modify `Document.files[*].url` — those are resolved
  through the abstraction at read time, which makes the flip fully
  reversible.

Typical rollout:

```
# 1) Dry run against the local tree.
OBJECT_STORAGE_BACKEND=s3 python -m backend.scripts.migrate_uploads_to_s3 --dry-run

# 2) Real copy.
OBJECT_STORAGE_BACKEND=s3 python -m backend.scripts.migrate_uploads_to_s3

# 3) Flip the running backend.
export OBJECT_STORAGE_BACKEND=s3 && systemctl restart hostflow-backend

# 4) Verify `/uploads/<key>` → 302, presigned URL resolves, documents open.
```

Rollback: unset `OBJECT_STORAGE_BACKEND` (or set back to `fs`) — files remain
on local disk, pre-Phase-0 behaviour is restored.

## Observability

* Startup logs: backend-selection + bucket/endpoint.
* Upload flow: `object_storage uploaded <key>` (DEBUG) + request metrics
  from Prometheus instrumentator.
* Presign failures: WARNING with the offending key (never logs the URL
  itself to avoid token leakage in central logs).

## Tests

* `tests/core/test_object_storage.py` — FS backend roundtrip (save bytes /
  save stream sync + async iter / delete / URL shape / path escape / factory
  semantics).
* `tests/core/test_documents_storage_urls.py` — URL + key extraction contract
  for FS and a stub S3 backend, covering the `_build_public_url` /
  `file_entry_download_url` / `resolve_file_path` triad.

Live MinIO smoke tests are intentionally out-of-scope — they are easy to run
manually against `docker compose --profile minio up` but would make CI
network-dependent. When/if we spin up an integration job, the S3 backend can
be exercised end-to-end with the same `FilesystemObjectStorage` tests
templated against `S3ObjectStorage`.

## Open follow-ups

1. Migrate remaining write call-sites (users profile photo, tenant_branding,
   scanners, communications attachments) onto `get_object_storage()`.
2. Extend `auto_fill_from_file` to pull from S3 via a temp-file download
   helper so the scanner pipeline works when `local_path(...)` is `None`.
3. Add per-tenant prefixes / IAM policies when onboarding the first customer
   that requires data residency.
4. Emit a CloudWatch / Prometheus counter for presign operations so we can
   alert on TTL exhaustion.
