# Frontend error-handling contract

_Status:_ stable since Phase 0 #4 (2026-04)  
_Owner:_ frontend platform  
_Scope:_ `hostflow-frontend/*` and every workspace that mounts inside it.

This document defines **how HostFlow surfaces errors to the user**. The goal is simple: *no white screens, no cryptic tracebacks, always an explicit next step.*

---

## 1. Building blocks

| Layer               | File                                                | Purpose                                                                              |
| ------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------ |
| API-error mapping   | `src/utils/friendlyError.ts`                        | Pure function `getFriendlyErrorInfo(err)` → `FriendlyErrorInfo` (title/hint/CTA).    |
| Toast / transient   | `src/components/Toast.tsx` + `src/utils/toastFromError.ts` | Top-of-screen notification stack. Use for actions the user just triggered. |
| Inline banner       | `src/components/ErrorRecoveryBanner.tsx`            | Persistent banner with Retry / secondary CTA. Use for loaders that failed.           |
| Section boundary    | `src/components/SectionErrorBoundary.tsx`           | Mid-tree React error boundary for widgets / tabs / modals; reports to Sentry.        |
| App boundary        | `src/components/AppErrorBoundary.tsx`               | Root-level React error boundary — absolute last-resort fallback.                     |

### Hierarchy

```
<AppErrorBoundary>          ← root; catches fatal bundle crashes, plain JSX
  <Router>
    <Page>
      <SectionErrorBoundary> ← one per tab / panel / modal / dashboard widget
        <Widget />
      </SectionErrorBoundary>
    </Page>
  </Router>
</AppErrorBoundary>
```

A section-level failure must **not** take the whole page down. A page-level failure must **not** take the whole app down.

---

## 2. When to use which UI

| Symptom                                          | UI                             | Why                                                    |
| ------------------------------------------------ | ------------------------------ | ------------------------------------------------------ |
| The user just clicked / submitted and it failed  | **Toast** (error variant)      | Transient, ties the feedback to the just-performed action. |
| Something the page needs to render did not load | **ErrorRecoveryBanner**        | Persistent, offers Retry + contextual CTA.             |
| A child component threw during render           | **SectionErrorBoundary**       | Keeps the rest of the page alive; reports to Sentry.   |
| The whole app exploded at module load / router  | **AppErrorBoundary**           | Renders without any providers.                         |

Rule of thumb: **toast ≠ banner**. A toast is ephemeral (4–7 s). A banner is the place to retry.

---

## 3. Toast contract (`useToast().notify`)

```ts
notify({
  title: string,                // required, ≤ 60 chars
  description?: ReactNode,      // optional, can contain inline links
  variant?: 'info' | 'success' | 'error' | 'warning',
  action?: { label: string; onClick: () => void }, // e.g. Retry / Open Billing
  ttlMs?: number,               // 0 = keep until dismissed
})
```

Default TTLs: 4 s (success / info / warning), 7 s (error). Always at least one action per error toast if there is a meaningful retry path — otherwise the "×" close button is the only way out.

---

## 4. Mapping API errors

Every API error must be funnelled through `getFriendlyErrorInfo(err, fallbackTitle, t?)`. The helper handles:

* **Network / offline / timeout** (`ERR_NETWORK`, `ECONNABORTED`)
* **400 `captcha_failed`** → "Bot check failed"
* **401 / 403 access** → "Access denied"
* **403 plan-gate codes** (`PORTAL_LINK_LIMIT_REACHED`, `BILLING_PAST_DUE`, `BILLING_TRIAL_EXPIRED`, `PLAN_REQUIRES_TEAM`, `SEAT_LIMIT_REACHED`, `PLAN_META_*`, `PLAN_LEAD_CUSTOM_FIELDS_LIMIT`) → billing CTA
* **402 quota codes** (`MONTHLY_LEADS_LIMIT_REACHED`, `CANDIDATE_LIMIT_REACHED`, `OPEN_VACANCY_LIMIT_REACHED`, `DOCUMENT_LIMIT_REACHED`, `STORAGE_LIMIT_REACHED`, `AUTOMATION_RULES_LIMIT_REACHED`, `LEAD_FORMS_LIMIT_REACHED`, `PORTAL_ACTIVE_CANDIDATES_LIMIT_REACHED`, `COMMUNICATION_CHANNELS_LIMIT_REACHED`, `FUNNEL_DEFINITIONS_LIMIT_REACHED`, `USAGE_LIMIT_EXCEEDED`, `OPERATING-COMPANY-LIMIT`) → billing CTA
* **404 / 409** → refresh-retry copy
* **429** → "Too many requests", includes `Please retry in {N} seconds` when the backend returned `detail.retry_after` (set by `enforce_rate_limit`) or a `Retry-After` header
* **≥ 500** → "Server is temporarily unavailable"

The returned `FriendlyErrorInfo` also carries transport-layer fields:

```ts
type FriendlyErrorInfo = {
  title: string
  detail?: string
  hint: string
  secondaryTo?: string          // billing CTA href
  secondaryLabel?: string
  status?: number               // HTTP status (0 if network)
  code?: string                 // best-known error code (detail.code / error_code / requestCode)
  retryAfterSec?: number        // 429 retry budget
}
```

Consumers rendering the UI can ignore `status` / `code` / `retryAfterSec`. Telemetry (`toastFromError`) uses them to tag Sentry events.

---

## 5. `toastFromError` — single entry point

For 95 % of action callbacks, you do not need to hand-craft a toast:

```ts
import { useToast } from '@/components/Toast'
import { toastFromError, toastSuccess } from '@/utils/toastFromError'

const { notify } = useToast()
const { t } = useTranslation()

async function onCreateLead() {
  try {
    const lead = await createLead(payload)
    toastSuccess(notify, t('leads.created_title'), lead.title)
  } catch (err) {
    toastFromError(notify, err, {
      fallbackTitle: t('leads.create_failed'),
      t,
      onRetry: onCreateLead,                        // adds "Retry" button
      sentryTags: { feature: 'leads.create' },      // optional
    })
  }
}
```

`toastFromError`:

* Runs `getFriendlyErrorInfo` and renders the error toast.
* Forwards unexpected / 5xx errors to Sentry with `http.status`, `error.code` and any caller-supplied `sentryTags`.
* **Does not** report user-facing expected errors (validation, plan-gate, 404, 429, captcha) to Sentry. Keep the dashboard signal clean.

---

## 6. Error-boundary usage

Wrap any widget / modal / detail drawer that loads its own data:

```tsx
import { SectionErrorBoundary } from '@/components/SectionErrorBoundary'

<SectionErrorBoundary sectionTag="dashboard.pipeline_card">
  <PipelineStageHealthCard />
</SectionErrorBoundary>
```

Sentry events from this boundary carry `boundary.scope = section` and (when provided) `boundary.section = dashboard.pipeline_card` — useful for alerting.

At the root (`main.tsx`) we still mount exactly **one** `<AppErrorBoundary>`, which must render without any providers.

---

## 7. Don't

* **Do not** `alert()` or `console.error()` user-visible errors.
* **Do not** swallow errors silently in fire-and-forget flows — pass them through `toastFromError` (you can set `reportToSentry: false` if the error is purely optional).
* **Do not** show both a toast **and** a banner for the same error — pick one based on §2.
* **Do not** hard-code retry copy; always go through `getFriendlyErrorInfo` (even for a fallback title) so translations stay consistent.
