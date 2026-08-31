import { CRM_APP_PATHS } from '../app/crmAppPaths.generated'

export type FriendlyErrorInfo = {
  title: string
  detail?: string
  hint: string
  /** When set, ErrorRecoveryBanner shows a secondary link (e.g. Settings → Billing). */
  secondaryTo?: string
  secondaryLabel?: string
  /**
   * Transport-layer hint used by toastFromError / Sentry forwarding:
   *   - HTTP status code (0 if unknown — e.g. network error)
   *   - machine-readable `detail.code` or error family from resolveApiErrorMeta
   *   - retryAfterSec for 429 (parsed from `detail.retry_after` or `Retry-After`)
   * Consumers that only render UI can ignore these fields.
   */
  status?: number
  code?: string
  retryAfterSec?: number
}

/** Merge `info.secondary*` with page defaults for ErrorRecoveryBanner (quota / billing CTA wins). */
export function friendlyErrorBannerSecondary(
  info: FriendlyErrorInfo,
  fallbackTo?: string,
  fallbackLabel?: string,
): { secondaryTo?: string; secondaryLabel?: string } {
  return {
    secondaryTo: info.secondaryTo ?? fallbackTo,
    secondaryLabel: info.secondaryLabel ?? fallbackLabel,
  }
}

export type FriendlyErrorTranslateFn = (
  key: string,
  options?: { values?: Record<string, string | number> },
) => string

/** Title + localized generic retry hint (form validation, public auth pages). */
export function friendlyFormHintError(title: string, t?: FriendlyErrorTranslateFn): FriendlyErrorInfo {
  return {
    title,
    hint: tr('Retry the action or refresh the page.', 'app.common.retry_hint', t),
  }
}

function tr(en: string, i18nKey: string, t?: FriendlyErrorTranslateFn): string {
  if (!t) return en
  const out = t(i18nKey)
  if (!out || out === i18nKey) return en
  return out
}

function withBillingCta(
  base: { title: string; detail?: string; hint: string },
  t?: FriendlyErrorTranslateFn,
): FriendlyErrorInfo {
  return {
    ...base,
    secondaryTo: CRM_APP_PATHS.settingsBilling,
    secondaryLabel: tr('Open Billing', 'app.api_errors.open_billing', t),
  }
}

function pickDetail(err: any): string | undefined {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail.trim() || undefined
  if (Array.isArray(detail)) {
    const msg = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
      .join('; ')
    return msg || undefined
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message.trim()) {
      return detail.message.trim()
    }
    const codeStr = typeof detail.code === 'string' ? detail.code.trim() : ''
    if (
      codeStr &&
      typeof (detail as { limit?: unknown }).limit === 'number' &&
      typeof (detail as { current?: unknown }).current === 'number'
    ) {
      return `${codeStr} (${(detail as { current: number }).current}/${(detail as { limit: number }).limit})`
    }
    if (codeStr) {
      return codeStr
    }
    if (typeof detail.msg === 'string' && detail.msg.trim()) {
      return detail.msg.trim()
    }
  }
  const message = typeof err?.message === 'string' ? err.message.trim() : ''
  return message || undefined
}

function resolveApiErrorMeta(err: any): {
  status: number
  requestCode: string
  detail: string | undefined
  detailPayload: unknown
  detailCode: string
  /** `detail.code` only (403 handlers in API use this field). */
  raw403Code: string
  /**
   * Seconds until the client can retry. Filled for 429 responses from either
   * `detail.retry_after` (our own `enforce_rate_limit`) or the `Retry-After`
   * header (set by most reverse proxies / slowapi's default handler).
   */
  retryAfterSec: number | null
} {
  const status = Number(err?.response?.status || 0)
  const requestCode = String(err?.code || '').trim().toUpperCase()
  const detailPayload = err?.response?.data?.detail
  const detail = pickDetail(err)
  const fromPayload =
    typeof detailPayload === 'object' && detailPayload && !Array.isArray(detailPayload)
      ? (detailPayload as { code?: string; error_code?: string; retry_after?: unknown })
      : null
  const raw403Code = fromPayload ? String(fromPayload.code || '').trim().toUpperCase() : ''
  const detailCode = String(
    (fromPayload && (fromPayload.code || fromPayload.error_code)) || detail || '',
  )
    .trim()
    .toUpperCase()
  let retryAfterSec: number | null = null
  if (fromPayload && typeof fromPayload.retry_after === 'number' && fromPayload.retry_after > 0) {
    retryAfterSec = Math.ceil(fromPayload.retry_after)
  } else {
    // Axios lowercases response headers; try both casings defensively.
    const hdrs = err?.response?.headers || {}
    const raw = hdrs['retry-after'] ?? hdrs['Retry-After']
    const parsed = Number.parseInt(String(raw ?? ''), 10)
    if (Number.isFinite(parsed) && parsed > 0) retryAfterSec = parsed
  }
  return { status, requestCode, detail, detailPayload, detailCode, raw403Code, retryAfterSec }
}

/** 403 codes that represent plan / seat / billing gates (show unified plan-limit modal + Billing CTA). */
const PLAN_LIMIT_OR_BILLING_GATE_403_CODES = new Set<string>([
  'PORTAL_LINK_LIMIT_REACHED',
  'BILLING_PAST_DUE',
  'BILLING_TRIAL_EXPIRED',
  'PLAN_REQUIRES_TEAM',
  'SEAT_LIMIT_REACHED',
  'PLAN_META_FIELD_MAPPING_LIMIT',
  'PLAN_META_LEAD_CREDENTIALS_LIMIT',
  'PLAN_META_LEADS_OAUTH',
  'PLAN_LEAD_CUSTOM_FIELDS_LIMIT',
])

export function isPlanLimitOrBillingGateError(err: any): boolean {
  const { status, raw403Code } = resolveApiErrorMeta(err)
  if (status === 402) return true
  if (status === 403 && PLAN_LIMIT_OR_BILLING_GATE_403_CODES.has(raw403Code)) return true
  return false
}

export function getFriendlyErrorInfo(
  err: any,
  fallbackTitle: string,
  t?: FriendlyErrorTranslateFn,
): FriendlyErrorInfo {
  const meta = resolveApiErrorMeta(err)
  const info = _getFriendlyErrorInfoInner(err, fallbackTitle, t, meta)
  return Object.assign(info, {
    status: meta.status,
    code: meta.raw403Code || meta.detailCode || meta.requestCode || undefined,
    retryAfterSec: meta.retryAfterSec ?? undefined,
  })
}

function _getFriendlyErrorInfoInner(
  _err: any,
  fallbackTitle: string,
  t: FriendlyErrorTranslateFn | undefined,
  meta: ReturnType<typeof resolveApiErrorMeta>,
): FriendlyErrorInfo {
  const { status, requestCode, detail, detailPayload, detailCode, raw403Code, retryAfterSec } = meta
  const offline = typeof navigator !== 'undefined' && navigator?.onLine === false

  if (offline || requestCode === 'ERR_NETWORK') {
    return {
      title: tr('No internet connection', 'app.api_errors.network_offline_title', t),
      detail,
      hint: tr('Check connection and retry.', 'app.api_errors.network_offline_hint', t),
    }
  }

  if (requestCode === 'ECONNABORTED') {
    return {
      title: tr('Request timed out', 'app.api_errors.timeout_title', t),
      detail,
      hint: tr('Retry in a few seconds.', 'app.api_errors.timeout_hint', t),
    }
  }

  if (status === 400 && detailCode === 'CAPTCHA_FAILED') {
    return {
      title: tr('Bot check failed', 'app.api_errors.captcha_failed_title', t),
      detail,
      hint: tr(
        'Complete the bot-protection challenge below and try again.',
        'app.api_errors.captcha_failed_hint',
        t,
      ),
    }
  }

  if (status === 403) {
    if (raw403Code === 'PORTAL_LINK_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr(
            'Client portal link limit reached',
            'app.api_errors.billing.portal_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade your plan in Settings → Billing or revoke an existing portal link.',
            'app.api_errors.billing.portal_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'BILLING_PAST_DUE') {
      return withBillingCta(
        {
          title: tr('Subscription payment required', 'app.api_errors.billing.past_due_title', t),
          detail:
            typeof detailPayload === 'object' &&
            detailPayload &&
            typeof (detailPayload as { message?: string }).message === 'string'
              ? (detailPayload as { message: string }).message.trim()
              : detail,
          hint: tr(
            'Open Settings → Billing to retry payment or update your payment method.',
            'app.api_errors.billing.past_due_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'BILLING_TRIAL_EXPIRED') {
      return withBillingCta(
        {
          title: tr('Trial has ended', 'app.api_errors.billing.trial_expired_title', t),
          detail:
            typeof detailPayload === 'object' &&
            detailPayload &&
            typeof (detailPayload as { message?: string }).message === 'string'
              ? (detailPayload as { message: string }).message.trim()
              : detail,
          hint: tr(
            'Choose a plan in Settings → Billing to keep working.',
            'app.api_errors.billing.trial_expired_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'PLAN_REQUIRES_TEAM') {
      return withBillingCta(
        {
          title: tr(
            'This action needs a Team-tier plan',
            'app.api_errors.plan_gate.plan_requires_team_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade in Settings → Billing to unlock team-tier automation and integrations.',
            'app.api_errors.plan_gate.plan_requires_team_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'SEAT_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Seat limit reached', 'app.api_errors.plan_gate.seat_limit_title', t),
          detail,
          hint: tr(
            'Remove users or invites for this role, or add seats in Settings → Billing.',
            'app.api_errors.plan_gate.seat_limit_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'PLAN_META_FIELD_MAPPING_LIMIT') {
      return withBillingCta(
        {
          title: tr(
            'Meta field mapping limit reached',
            'app.api_errors.plan_gate.meta_field_mapping_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade in Settings → Billing for a larger mapping table on Team-tier plans.',
            'app.api_errors.plan_gate.meta_field_mapping_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'PLAN_META_LEAD_CREDENTIALS_LIMIT') {
      return withBillingCta(
        {
          title: tr(
            'Meta lead integration limit reached',
            'app.api_errors.plan_gate.meta_lead_credentials_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade in Settings → Billing to connect additional Meta lead sources.',
            'app.api_errors.plan_gate.meta_lead_credentials_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'PLAN_META_LEADS_OAUTH') {
      return withBillingCta(
        {
          title: tr(
            'Meta quick connect needs a Team-tier plan',
            'app.api_errors.plan_gate.meta_leads_oauth_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade in Settings → Billing to use Facebook Login for Meta Leads.',
            'app.api_errors.plan_gate.meta_leads_oauth_hint',
            t,
          ),
        },
        t,
      )
    }
    if (raw403Code === 'PLAN_LEAD_CUSTOM_FIELDS_LIMIT') {
      return withBillingCta(
        {
          title: tr(
            'Lead custom field limit reached',
            'app.api_errors.plan_gate.lead_custom_fields_title',
            t,
          ),
          detail,
          hint: tr(
            'Archive unused fields or upgrade in Settings → Billing to add more.',
            'app.api_errors.plan_gate.lead_custom_fields_hint',
            t,
          ),
        },
        t,
      )
    }
    return {
      title: tr('Access denied for this action', 'app.api_errors.access_denied_title', t),
      detail,
      hint: tr(
        'Refresh session or ask admin for permissions.',
        'app.api_errors.access_denied_hint',
        t,
      ),
    }
  }

  if (status === 401) {
    return {
      title: tr('Access denied for this action', 'app.api_errors.access_denied_title', t),
      detail,
      hint: tr(
        'Refresh session or ask admin for permissions.',
        'app.api_errors.access_denied_hint',
        t,
      ),
    }
  }

  if (status === 402) {
    if (detailCode === 'OPERATING-COMPANY-LIMIT') {
      return withBillingCta(
        {
          title: tr(
            'Operating company limit reached',
            'app.api_errors.quota.operating_company_title',
            t,
          ),
          detail,
          hint: tr(
            'Open Billing and add an extra operating company slot.',
            'app.api_errors.quota.operating_company_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'MONTHLY_LEADS_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Monthly leads limit reached', 'app.api_errors.quota.monthly_leads_title', t),
          detail,
          hint: tr(
            'Upgrade in Settings → Billing or wait until the next month (UTC).',
            'app.api_errors.quota.monthly_leads_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'CANDIDATE_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Active candidate limit reached', 'app.api_errors.quota.candidate_title', t),
          detail,
          hint: tr(
            'Archive or remove candidates you no longer need, or upgrade in Settings → Billing.',
            'app.api_errors.quota.candidate_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'OPEN_VACANCY_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Open vacancy limit reached', 'app.api_errors.quota.vacancy_title', t),
          detail,
          hint: tr(
            'Close vacancies you are not hiring for, or upgrade in Settings → Billing.',
            'app.api_errors.quota.vacancy_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'DOCUMENT_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Document limit reached', 'app.api_errors.quota.document_title', t),
          detail,
          hint: tr(
            'Remove obsolete documents or upgrade in Settings → Billing.',
            'app.api_errors.quota.document_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'STORAGE_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Storage limit reached', 'app.api_errors.quota.storage_title', t),
          detail,
          hint: tr(
            'Remove large files or upgrade storage in Settings → Billing.',
            'app.api_errors.quota.storage_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'AUTOMATION_RULES_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Automation rules limit reached', 'app.api_errors.quota.automation_rules_title', t),
          detail,
          hint: tr(
            'Disable a rule you no longer need or upgrade in Settings → Billing.',
            'app.api_errors.quota.automation_rules_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'LEAD_FORMS_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Lead forms limit reached', 'app.api_errors.quota.lead_forms_title', t),
          detail,
          hint: tr(
            'Deactivate a form, buy a lead-forms pack, or upgrade in Settings → Billing.',
            'app.api_errors.quota.lead_forms_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'PORTAL_ACTIVE_CANDIDATES_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr(
            'Monthly candidate portal limit reached',
            'app.api_errors.quota.portal_active_candidates_title',
            t,
          ),
          detail,
          hint: tr(
            'Upgrade or add a portal pack in Settings → Billing. Candidates already counted this month can still refresh links.',
            'app.api_errors.quota.portal_active_candidates_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'COMMUNICATION_CHANNELS_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr(
            'Communication channel limit reached',
            'app.api_errors.quota.communication_channels_title',
            t,
          ),
          detail,
          hint: tr(
            'Remove a channel account you no longer need or upgrade in Settings → Billing.',
            'app.api_errors.quota.communication_channels_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'FUNNEL_DEFINITIONS_LIMIT_REACHED') {
      return withBillingCta(
        {
          title: tr('Pipeline limit reached', 'app.api_errors.quota.funnel_definitions_title', t),
          detail,
          hint: tr(
            'Remove or merge a custom pipeline or upgrade in Settings → Billing.',
            'app.api_errors.quota.funnel_definitions_hint',
            t,
          ),
        },
        t,
      )
    }
    if (detailCode === 'USAGE_LIMIT_EXCEEDED') {
      return withBillingCta(
        {
          title: tr('Usage limit reached', 'app.api_errors.quota.usage_meter_title', t),
          detail,
          hint: tr(
            'Open Settings → Billing to review your plan or try again next month.',
            'app.api_errors.quota.usage_meter_hint',
            t,
          ),
        },
        t,
      )
    }
    return withBillingCta(
      {
        title: tr('Plan limit reached', 'app.api_errors.quota.plan_generic_title', t),
        detail,
        hint: tr(
          'Open Settings → Billing to review your plan and usage.',
          'app.api_errors.quota.plan_generic_hint',
          t,
        ),
      },
      t,
    )
  }

  if (status === 404) {
    return {
      title: tr('Requested data was not found', 'app.api_errors.not_found_title', t),
      detail,
      hint: tr('Refresh data and retry the action.', 'app.api_errors.not_found_hint', t),
    }
  }

  if (status === 409) {
    return {
      title: tr('Data conflict detected', 'app.api_errors.conflict_title', t),
      detail,
      hint: tr('Refresh page and retry.', 'app.api_errors.conflict_hint', t),
    }
  }

  if (status === 422) {
    const peUnmapped =
      typeof detail === 'string' && detail.toLowerCase().includes('process engine')
    if (peUnmapped) {
      return {
        title: tr('Stage code is not in the catalog', 'admin.funnels.errors.unmapped_stage_code', t),
        detail,
        hint: tr(
          'Pick a registered system stage code. The label can be custom.',
          'admin.funnels.code_must_map_pe',
          t,
        ),
      }
    }
    return {
      title: fallbackTitle,
      detail,
      hint: tr('Retry the action or refresh the page.', 'app.api_errors.generic_retry_hint', t),
    }
  }

  if (status === 429) {
    const hintBase = tr('Wait a moment and try again.', 'app.api_errors.rate_limit_hint', t)
    const hint =
      retryAfterSec && retryAfterSec > 0
        ? tr('Please retry in {{seconds}} seconds.', 'app.api_errors.rate_limit_retry_after_hint', t).replace(
            '{{seconds}}',
            String(retryAfterSec),
          )
        : hintBase
    return {
      title: tr('Too many requests', 'app.api_errors.rate_limit_title', t),
      detail,
      hint,
    }
  }

  if (status >= 500) {
    return {
      title: tr('Server is temporarily unavailable', 'app.api_errors.server_error_title', t),
      detail,
      hint: tr(
        'Retry shortly. If problem persists, check service health.',
        'app.api_errors.server_error_hint',
        t,
      ),
    }
  }

  return {
    title: fallbackTitle,
    detail,
    hint: tr('Retry the action or refresh the page.', 'app.api_errors.generic_retry_hint', t),
  }
}
