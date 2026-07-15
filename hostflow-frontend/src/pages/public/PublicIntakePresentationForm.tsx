import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { isCookieConsentGranted, subscribeCookieConsent } from '../../components/public/cookieConsent'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { LegalLinksBlock } from './components/LegalLinksBlock'
import { AutosaveIndicator } from './components/AutosaveIndicator'
import { CONSENT_DOCUMENT_VERSIONS } from './constants'
import type { FormPresentationRuntime } from '../../modules/public-intake/types'
import type { PublicIntakeHook } from '../../modules/public-intake/usePublicIntake'
import type { PublicIntakeSubmitPayload } from '../../api/publicIntake'
import { evaluatePresentationFields } from '../../utils/presentationRules'
import { IntakePresentationFieldControl } from '../../components/intake/IntakePresentationFieldControl'

type Props = {
  intake: PublicIntakeHook
  presentation: FormPresentationRuntime
  /** When set, client cannot change locale (manager chose language on send). */
  lockedLocale?: 'ru' | 'pl' | 'en'
}

type FieldValue = string | string[]

function normalizeStoredValue(raw: unknown, field: FormPresentationRuntime['fields'][number]): FieldValue {
  const kind = String(field.widget_hint || field.field_type || 'text').toLowerCase()
  if (kind.includes('multi_select')) {
    if (Array.isArray(raw)) return raw.map((item) => String(item))
    if (raw == null || raw === '') return []
    return [String(raw)]
  }
  if (raw == null) return ''
  return String(raw)
}

function isEmptyValue(value: FieldValue, field: FormPresentationRuntime['fields'][number]): boolean {
  const kind = String(field.widget_hint || field.field_type || 'text').toLowerCase()
  if (kind.includes('multi_select')) return !Array.isArray(value) || value.length === 0
  return !String(value || '').trim()
}

export default function PublicIntakePresentationForm({ intake, presentation, lockedLocale }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const {
    loading,
    saving,
    submitting,
    error,
    state,
    formData,
    updatePresentationValues,
    updateAgreements,
    submit,
  } = intake

  const [cookiesAccepted, setCookiesAccepted] = useState(() => isCookieConsentGranted())

  useEffect(() => {
    const unsubscribe = subscribeCookieConsent(() => setCookiesAccepted(true))
    return unsubscribe
  }, [])

  useEffect(() => {
    if (cookiesAccepted && !formData.agreements?.cookies_accepted) {
      updateAgreements({ cookies_accepted: true })
    }
  }, [cookiesAccepted, formData.agreements?.cookies_accepted, updateAgreements])

  const sortedFields = useMemo(
    () => [...presentation.fields].sort((a, b) => a.sort_order - b.sort_order),
    [presentation.fields],
  )

  const [values, setValues] = useState<Record<string, FieldValue>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const valueMap = useMemo(() => {
    const map: Record<string, unknown> = {}
    for (const [key, val] of Object.entries(values)) {
      map[key] = val
    }
    return map
  }, [values])

  const evaluatedFields = useMemo(
    () => evaluatePresentationFields(sortedFields, valueMap),
    [sortedFields, valueMap],
  )

  const visibleFields = useMemo(
    () => evaluatedFields.filter((field) => field.evaluated.visible),
    [evaluatedFields],
  )

  const progress = useMemo(() => {
    const total = visibleFields.length
    const filled = visibleFields.filter((field) => !isEmptyValue(values[field.qualified_code], field)).length
    return { total, filled, pct: total > 0 ? Math.round((filled / total) * 100) : 0 }
  }, [values, visibleFields])

  const headerLocaleSwitcher = lockedLocale ? null : <PublicLocaleSwitcher />

  const [agreements, setAgreements] = useState({
    general: Boolean(formData.agreements?.general),
    employer_share: Boolean(formData.agreements?.employer_share),
    terms_acceptance: Boolean(formData.agreements?.terms_acceptance),
    cookies_accepted: Boolean(formData.agreements?.cookies_accepted),
  })

  useEffect(() => {
    const initial: Record<string, FieldValue> = {}
    for (const field of sortedFields) {
      const raw = formData.presentation_values?.[field.qualified_code]
      if (raw !== undefined && raw !== null) {
        initial[field.qualified_code] = normalizeStoredValue(raw, field)
      }
    }
    setValues((prev) => ({ ...initial, ...prev }))
  }, [formData.presentation_values, sortedFields])

  useEffect(() => {
    setAgreements({
      general: Boolean(formData.agreements?.general),
      employer_share: Boolean(formData.agreements?.employer_share),
      terms_acceptance: Boolean(formData.agreements?.terms_acceptance),
      cookies_accepted: Boolean(formData.agreements?.cookies_accepted),
    })
  }, [formData.agreements])

  const dependentFields: Record<string, string[]> = useMemo(
    () => ({
      'service_sales.targeted_advertising.work_location_country': [
        'service_sales.targeted_advertising.work_location_region',
        'service_sales.targeted_advertising.work_location_city',
      ],
      'service_sales.targeted_advertising.client_geo_country': [
        'service_sales.targeted_advertising.client_geo_region',
        'service_sales.targeted_advertising.client_geo_city',
      ],
    }),
    [],
  )

  const handleChange = useCallback(
    (qualifiedCode: string, next: FieldValue) => {
      setValues((prev) => {
        const updated = { ...prev, [qualifiedCode]: next }
        for (const childCode of dependentFields[qualifiedCode] ?? []) {
          delete updated[childCode]
        }
        updatePresentationValues(updated as Record<string, string>)
        return updated
      })
      setFieldErrors((prev) => {
        if (!prev[qualifiedCode]) return prev
        const copy = { ...prev }
        delete copy[qualifiedCode]
        return copy
      })
    },
    [dependentFields, updatePresentationValues],
  )

  const validateRequired = useCallback(() => {
    const nextErrors: Record<string, string> = {}
    for (const field of evaluatedFields) {
      if (!field.evaluated.visible) continue
      if (field.evaluated.intake_level !== 'required') continue
      const val = values[field.qualified_code]
      if (isEmptyValue(val, field)) {
        nextErrors[field.qualified_code] = t('public.intake.presentation.required', {
          defaultValue: 'Required field',
        })
      }
    }
    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }, [evaluatedFields, values, t])

  const patchAgreements = useCallback(
    (patch: Partial<typeof agreements>) => {
      setAgreements((prev) => {
        const next = { ...prev, ...patch }
        updateAgreements({
          general: next.general,
          employer_share: next.employer_share,
          terms_acceptance: next.terms_acceptance,
          cookies_accepted: Boolean(next.cookies_accepted || cookiesAccepted),
        })
        return next
      })
    },
    [cookiesAccepted, updateAgreements],
  )

  const handleSubmit = async () => {
    if (!validateRequired()) return
    const cookieReady = Boolean(agreements.cookies_accepted || cookiesAccepted)
    if (!agreements.general || !agreements.employer_share || !agreements.terms_acceptance) {
      notify({
        title: t('public.intake.presentation.consents_required', { defaultValue: 'Accept required consents' }),
        variant: 'error',
      })
      return
    }
    if (!cookieReady) {
      notify({
        title: t('public.intake.validations.cookies', { defaultValue: 'Accept cookies to continue' }),
        variant: 'error',
      })
      return
    }
    const payload: PublicIntakeSubmitPayload = {
      consents: {
        general: agreements.general,
        employer_share: agreements.employer_share,
        terms_acceptance: agreements.terms_acceptance,
      },
      documents_version: CONSENT_DOCUMENT_VERSIONS,
      cookies_accepted: cookieReady,
    }
    try {
      await submit(payload)
      notify({
        title: t('public.intake.presentation.submitted', { defaultValue: 'Application submitted' }),
        variant: 'success',
      })
    } catch {
      // error surfaced via hook
    }
  }

  if (loading && !state) {
    return (
      <PublicPageShell maxWidth="lg" headerExtra={headerLocaleSwitcher}>
        <div className="card p-8 text-center text-slate-600">{t('common.loading')}</div>
      </PublicPageShell>
    )
  }

  if (state?.status === 'submitted') {
    return (
      <PublicPageShell maxWidth="lg" headerExtra={headerLocaleSwitcher}>
        <div className="card p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500 text-xl text-white">
            ✓
          </div>
          <h1 className="text-xl font-semibold text-slate-900">
            {t('public.intake.presentation.thank_you', { defaultValue: 'Thank you — your application was received' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.intake.presentation.thank_you_hint', {
              defaultValue: 'We saved your submission as a lead draft. Our team will review it shortly.',
            })}
          </p>
          {state.status_share_token ? (
            <Link
              to={`/public/status/${state.status_share_token}`}
              className="mt-6 inline-flex rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              {t('public.intake.presentation.track_status', { defaultValue: 'Track status' })}
            </Link>
          ) : null}
        </div>
      </PublicPageShell>
    )
  }

  return (
    <PublicPageShell maxWidth="lg" headerExtra={headerLocaleSwitcher}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('public.intake.presentation.kicker', { defaultValue: 'Application form' })}
          </p>
          <h1 className="text-xl font-semibold text-slate-900">
            {presentation.profile_name || presentation.entity_profile_code}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {t('public.intake.presentation.duration_hint', { defaultValue: 'Обычно занимает 2–3 минуты' })}
          </p>
        </div>
        <AutosaveIndicator saving={saving} />
      </div>

      {progress.total > 0 ? (
        <div className="mb-4">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-brand-600 transition-all duration-300"
              style={{ width: `${progress.pct}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t('public.intake.presentation.progress', {
              defaultValue: 'Заполнено {{filled}} из {{total}}',
              filled: progress.filled,
              total: progress.total,
            })}
          </p>
        </div>
      ) : null}

      <div className="card space-y-5 p-6">
        {visibleFields.map((field) => (
          <div key={field.qualified_code} className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700">
              {field.label}
              {field.evaluated.intake_level === 'required' ? <span className="text-red-500"> *</span> : null}
            </span>
            <IntakePresentationFieldControl
              field={field}
              values={values}
              value={values[field.qualified_code] ?? ''}
              error={fieldErrors[field.qualified_code]}
              disabled={submitting || field.evaluated.readonly}
              onChange={(next) => handleChange(field.qualified_code, next)}
            />
          </div>
        ))}

        <div className="space-y-2 border-t border-slate-100 pt-4">
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.general}
              onChange={(e) => patchAgreements({ general: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_general', { defaultValue: 'I accept the privacy policy' })}</span>
          </label>
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.employer_share}
              onChange={(e) => patchAgreements({ employer_share: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_share', { defaultValue: 'I agree to share data with employers' })}</span>
          </label>
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.terms_acceptance}
              onChange={(e) => patchAgreements({ terms_acceptance: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_terms', { defaultValue: 'I accept the terms of service' })}</span>
          </label>
          <p className="text-xs text-slate-500">{t('public.intake.forms.agreements.cookies_hint')}</p>
          <LegalLinksBlock />
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <button
          type="button"
          className="btn-primary w-full"
          disabled={submitting || saving}
          onClick={() => void handleSubmit()}
        >
          {submitting ? t('common.loading') : t('public.intake.presentation.submit', { defaultValue: 'Submit application' })}
        </button>
      </div>
    </PublicPageShell>
  )
}
