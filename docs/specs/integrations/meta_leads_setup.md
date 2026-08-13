# Meta → HostFlow Leads Integration

This guide describes how to connect Facebook (Meta) Lead Ads to HostFlow so every submitted lead becomes a candidate without Graph API errors. Follow the checklist end‑to‑end whenever you onboard a new Facebook page or rotate credentials.

---

## 1. Architecture Overview

- Facebook Lead Ads fire a webhook to **HostFlow Leads** (Meta app ID `1102404865044655`).
- HostFlow exposes the callback at `https://hostflow.cc/api/v1/leads/meta/webhook?verify_token=hostflow123`.
- Credentials are stored per tenant in `meta_lead_credentials` with the page access token, app secret, and ad account metadata. Mapping between `ad_id` and HostFlow vacancies lives in `meta_ads_map`.
- The ingestion pipeline normalises the payload, enriches it through Graph when needed, deduplicates, and either creates or updates candidates.

---

## 2. Prerequisites

1. Facebook page admin rights (e.g. **Work Host**).
2. Access to **Graph API Explorer** (Facebook for Developers).
3. HostFlow admin account (`admin@hostflow.dev`).
4. App credentials:
   - App ID: `1102404865044655`
   - App Secret: `84f2797ffc4cfe3befc36b2e23e4913b`
   - Verify token: `hostflow123`
   - Webhook URL: `https://hostflow.cc/api/v1/leads/meta/webhook?verify_token=hostflow123`

Keep the App Secret in `meta_lead_credentials.secret` (encrypted in storage) and use the verify token only for webhook handshakes.

---

## 3. Obtain Long‑Lived Tokens

1. In Graph API Explorer choose the **HostFlow Leads** app.
2. Enable permissions: `pages_read_engagement`, `pages_manage_metadata`, `pages_show_list`, `leads_retrieval`, `business_management` (needed for Business Suite / New Pages so `/me/accounts` returns pages).
3. Generate a short‑lived **User Access Token** and exchange it for a long‑lived token (`fb_exchange_token`).
4. Verify the token via `/debug_token` – it must belong to App ID `1102404865044655`.
5. With that user token, request a **Page Access Token** for the target page. If Meta returns “Provide valid app ID (200)” the wrong app is selected.

Store the resulting page token and app secret in the HostFlow credential record (see §5).

---

## 4. Subscribe the Page to Leadgen Events

1. Using Graph API Explorer or cURL, call:

   ```bash
   POST /{page-id}/subscribed_apps?subscribed_fields=leadgen
   ```

   with the page token.
2. Confirm **HostFlow Leads** appears in the page’s *Advanced Messaging* / *Leads Access* panel.

Without the subscription Meta will never deliver new leads to HostFlow.

---

## 5. HostFlow Configuration

Create or update credentials in **Settings → Integrations → Meta Leads** for each Facebook page.

| Field | Value |
| --- | --- |
| `label` | Friendly name (e.g. `Citronex Leads`) |
| `page_id` | Facebook page ID |
| `secret` | App Secret `84f2797ffc4cfe3befc36b2e23e4913b` |
| `access_token` | Long‑lived Page Access Token |
| `ad_account_id` | Optional for reference |
| `status` | `active` |

Ensure `has_secret = true`, `last_verified_at` updates after webhook delivery, and `last_rotation_at` reflects the latest secret rotation. Two default credentials exist:

- **Citronex Leads** → Work Host page
- **Poltrakt Leads** → Poltrakt page

---

## 6. Mapping Ads to Vacancies

Populate `meta_ads_map` so HostFlow routes each lead to the correct vacancy.

| Ad ID | Vacancy | Notes |
| --- | --- | --- |
| `120234308359530475` | `807759e4-dbb7-4b7e-9a29-4219a97dab09` | Citronex RU CE Drivers |
| `120235023955160475` | `807759e4-dbb7-4b7e-9a29-4219a97dab09` | Citronex ENG CE Drivers |

Use the admin endpoint `/api/v1/admin/meta-leads/mapping` or the UI to create/update mappings. Leads without matches land in `needs_routing`.

---

## 7. Forms and Lead Validation

- Keep required forms published and active (e.g. IDs `1993507098109989`, `3066022813608950`).
- Each Meta payload should include `id`, `ad_id`, `form_id`, `created_time`, and `field_data` with contact information.
- HostFlow stores raw and normalised data; PII is masked in logs when `mask_pii_in_logs` is true.

---

## 8. Error Handling & Recovery

Common statuses:

| Status | Meaning | Fix |
| --- | --- | --- |
| `GRAPH_190` | Invalid or expired token | Refresh the page token (see §3) |
| `GRAPH_NO_TOKEN` | HostFlow credential missing page token | Update credential’s `access_token` |
| `NEEDS_ROUTING` | No vacancy mapping or auto-create disabled | Add mapping or enable auto-create |

After fixing credentials or mappings, reprocess historical leads:

1. **Admin API** — `POST /api/v1/admin/meta-leads/leads/retry`
   ```json
   {
     "statuses": ["failed", "needs_routing"],
     "limit": 50
   }
   ```
   The response lists each lead with before/after status and candidate reference.

2. **CLI helper** — `python scripts/retry_meta_leads.py --tenant <tenant> --status failed`
   - Defaults to retrying `failed` and `needs_routing` leads.
   - Use `--lead` to target explicit lead IDs or `--no-graph` to skip Graph hydration during maintenance windows.

Both paths reuse the webhook enrichment pipeline, so skeleton payloads are automatically filled with fresh Graph data when `pull_field_data_from_graph` is enabled.

---

## 9. Verification Checklist

- `GET /api/v1/leads/meta/webhook` returns the `hub.challenge` when called with `verify_token=hostflow123`.
- Admin panel shows credentials with status **active**, `has_secret = true`, and a recent `last_verified_at`.
- `meta_lead_settings.webhook_url` matches `https://hostflow.cc/api/v1/leads/meta/webhook` and `webhook_verify_token = hostflow123`.
- Send a test submission from the Facebook form: a candidate should appear in HostFlow without errors.

---

## 10. Troubleshooting Facebook Side

1. Page settings → Leads Access → CRM Access must list **HostFlow Leads** with read permissions.
2. Ensure you operate within the correct Business Manager; otherwise the Graph API refuses to mint a page token.
3. If signature mismatches persist, remove the app from *Business Integrations* and connect it again.

---

## 11. Database & RLS Notes

- Every row stores `tenant_id`; RLS enforces isolation. `set_config('app.tenant_id', ...)` is applied automatically in the ingestion pipeline and during retries.
- Seeds (`backend/app/db/seeds/dev_full_seed.py`) create placeholder mappings and settings for local development. Run `make seed` after adjusting docs or schema.

---

## 12. Self-service onboarding (deployment env)

Paid tenants can connect Meta without operator hand-holding when the UI **Meta Leads admin** shows the “Connect Meta (self-service)” block. That panel reads from `GET /api/v1/settings/leads/meta/self-serve-onboarding` and requires correct server configuration:

| Variable | Purpose |
| --- | --- |
| `META_LEADS_APP_ID` | Facebook App ID shown to customers for Webhooks / token setup. |
| `META_LEADS_APP_DISPLAY_NAME` | Optional display label in the API response. |
| `META_LEADS_DOCS_URL` | Optional URL for the “Documentation” link in the panel. |
| `META_GRAPH_API_VERSION` | Graph version string (e.g. `v24.0`) shown next to the permission list. |
| `META_LEADS_SHARED_APP_SECRET` | Optional. If set, **workspace administrators** see this secret in the panel when the Meta app uses a shared app secret. |
| `PUBLIC_API_BASE_URL` or `FRONTEND_URL` | Public origin used to build the webhook callback: `{base}/api/v1/leads/meta/webhook?verify_token=…`. The verify token must be saved in tenant Meta Leads settings before the full URL appears. |
| `META_LEADS_OPERATIONAL_TENANT_ID` | Optional. By default the API uses the canonical **Focus Personnel** tenant id from code (`backend/app/constants/hostflow_canonical_tenants.py`). Set this env to **another UUID** to override, or to **`off`**, **`disable`**, **`none`**, **`false`**, or **`0`** to disable remapping (e.g. forks). Restart backend after change. |

Supervisors see the same panel but **not** the shared app secret.

### 12.1 Facebook Login (quick connect)

On **Team-tier plans and above**, workspace **administrators** can use **Connect with Meta** in the Meta Leads admin UI:

1. `POST /api/v1/settings/leads/meta/oauth/start` — returns a Facebook Login `authorize_url` and signed `state`.
2. After redirect back to `{FRONTEND_URL}/app/settings/integrations/meta?code=…&state=…`, the UI calls `POST /api/v1/settings/leads/meta/oauth/complete` with `{ code, state }`. The server exchanges the code, fetches `/me/accounts`, and stores page tokens in **`meta_oauth_pending`** (encrypted, short TTL).
3. `POST /api/v1/settings/leads/meta/oauth/finalize` with `{ pending_id, page_id, label, subscribe_leadgen }` creates a normal **`meta_lead_credentials`** row (shared app secret + page token) and, by default, calls Graph **`/{page-id}/subscribed_apps?subscribed_fields=leadgen`**.

| Variable | Purpose |
| --- | --- |
| `META_LEADS_OAUTH_REDIRECT_URI` | Optional. Overrides the redirect URI (must match Meta app **Valid OAuth Redirect URIs** exactly). Default: `{FRONTEND_URL}/app/settings/integrations/meta`. |

Starter / trial / solo tenants receive **403** with `code: plan_meta_leads_oauth`.

---

## 13. References

- Module spec: `docs/specs/modules/leads.md`
- REST endpoints: `backend/app/api/v1/leads/meta`, `backend/app/api/v1/admin/meta-leads/*`
- Retry script: `scripts/retry_meta_leads.py`
- Self-serve API: `GET /api/v1/settings/leads/meta/self-serve-onboarding`
- Meta OAuth: `POST /api/v1/settings/leads/meta/oauth/start`, `.../complete`, `.../finalize`
