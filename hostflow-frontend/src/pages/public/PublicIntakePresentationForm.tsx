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
import {
  evaluatePresentationFields,
  pruneHiddenPresentationValues,
} from '../../utils/presentationRules'
import {
  normalizeFieldValue,
  serializeValuesForApi,
  type PresentationFieldValue,
} from '../../utils/intakePresentationFieldOptions'
import { PresentationFieldControl, presentationFieldHasValue } from './PresentationFieldControl'

type Props = {
  intake: PublicIntakeHook
  presentation: FormPresentationRuntime
}

type ValueState = Record<string, PresentationFieldValue>

export default function PublicIntakePresentationForm({ intake, presentation }: Props) {
  const { t, locale } = useI18n()
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

  const [values, setValues] = useState<ValueState>({})
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

  const [agreements, setAgreements] = useState({
    general: Boolean(formData.agreements?.general),
    employer_share: Boolean(formData.agreements?.employer_share),
    terms_acceptance: Boolean(formData.agreements?.terms_acceptance),
    cookies_accepted: Boolean(formData.agreements?.cookies_accepted),
  })

  const syncPresentationValues = useCallback(
    (nextValues: ValueState) => {
      const evaluated = evaluatePresentationFields(sortedFields, nextValues)
      const pruned = pruneHiddenPresentationValues(nextValues, evaluated) as ValueState
      setValues(pruned)
      updatePresentationValues(serializeValuesForApi(pruned))
      return pruned
    },
    [sortedFields, updatePresentationValues],
  )

  useEffect(() => {
    if (!formData.presentation_values) return
    const initial: ValueState = {}
    for (const field of sortedFields) {
      const raw = formData.presentation_values[field.qualified_code]
      if (raw !== undefined && raw !== null) {
        initial[field.qualified_code] = normalizeFieldValue(raw)
      }
    }
    const evaluated = evaluatePresentationFields(sortedFields, initial)
    const pruned = pruneHiddenPresentationValues(initial, evaluated) as ValueState
    setValues(pruned)
  }, [formData.presentation_values, sortedFields])

  useEffect(() => {
    setAgreements({
      general: Boolean(formData.agreements?.general),
      employer_share: Boolean(formData.agreements?.employer_share),
      terms_acceptance: Boolean(formData.agreements?.terms_acceptance),
      cookies_accepted: Boolean(formData.agreements?.cookies_accepted),
    })
  }, [formData.agreements])

  const handleChange = useCallback(
    (qualifiedCode: string, next: PresentationFieldValue) => {
      syncPresentationValues({ ...values, [qualifiedCode]: next })
      setFieldErrors((prev) => {
        if (!prev[qualifiedCode]) return prev
        const copy = { ...prev }
        delete copy[qualifiedCode]
        return copy
      })
    },
    [syncPresentationValues, values],
  )

  const validateRequired = useCallback(() => {
    const nextErrors: Record<string, string> = {}
    for (const field of evaluatedFields) {
      if (!field.evaluated.visible) continue
      if (field.evaluated.intake_level !== 'required') continue
      if (!presentationFieldHasValue(values[field.qualified_code])) {
        nextErrors[field.qualified_code] = t('public.intake.presentation.required', {
          defaultValue: 'Pole wymagane',
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
    syncPresentationValues(values)
    if (!validateRequired()) return
    const cookieReady = Boolean(agreements.cookies_accepted || cookiesAccepted)
    if (!agreements.general || !agreements.employer_share || !agreements.terms_acceptance) {
      notify({
        title: t('public.intake.presentation.consents_required', { defaultValue: 'Zaakceptuj wymagane zgody' }),
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
        title: t('public.intake.presentation.submitted', { defaultValue: 'Ankieta została wysłana' }),
        variant: 'success',
      })
    } catch {
      // error surfaced via hook
    }
  }

  if (loading && !state) {
    return (
      <PublicPageShell maxWidth="lg" headerExtra={<PublicLocaleSwitcher />}>
        <div className="card p-8 text-center text-slate-600">{t('common.loading')}</div>
      </PublicPageShell>
    )
  }

  if (state?.status === 'submitted') {
    return (
      <PublicPageShell maxWidth="lg" headerExtra={<PublicLocaleSwitcher />}>
        <div className="card p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500 text-xl text-white">
            ✓
          </div>
          <h1 className="text-xl font-semibold text-slate-900">
            {t('public.intake.presentation.thank_you', { defaultValue: 'Dziękujemy — otrzymaliśmy Państwa ankietę' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.intake.presentation.thank_you_hint', {
              defaultValue: 'Zapisaliśmy odpowiedzi. Nasz zespół wkrótce się z Państwem skontaktuje.',
            })}
          </p>
          {state.status_share_token ? (
            <Link
              to={`/public/status/${state.status_share_token}`}
              className="mt-6 inline-flex rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              {t('public.intake.presentation.track_status', { defaultValue: 'Sprawdź status' })}
            </Link>
          ) : null}
        </div>
      </PublicPageShell>
    )
  }

  return (
    <PublicPageShell maxWidth="lg" headerExtra={<PublicLocaleSwitcher />}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('public.intake.presentation.kicker', { defaultValue: 'Ankieta' })}
          </p>
          <h1 className="text-xl font-semibold text-slate-900">
            {presentation.profile_name || presentation.entity_profile_code}
          </h1>
        </div>
        <AutosaveIndicator saving={saving} />
      </div>

      <div className="card space-y-5 p-6">
        {visibleFields.map((field) => (
          <PresentationFieldControl
            key={field.qualified_code}
            field={field}
            value={values[field.qualified_code]}
            error={fieldErrors[field.qualified_code]}
            disabled={submitting}
            locale={locale}
            t={t}
            onChange={handleChange}
          />
        ))}

        <div className="space-y-2 border-t border-slate-100 pt-4">
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.general}
              onChange={(e) => patchAgreements({ general: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_general', { defaultValue: 'Akceptuję politykę prywatności' })}</span>
          </label>
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.employer_share}
              onChange={(e) => patchAgreements({ employer_share: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_share', { defaultValue: 'Wyrażam zgodę na udostępnienie danych' })}</span>
          </label>
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={agreements.terms_acceptance}
              onChange={(e) => patchAgreements({ terms_acceptance: e.target.checked })}
            />
            <span>{t('public.intake.presentation.consent_terms', { defaultValue: 'Akceptuję regulamin' })}</span>
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
          {submitting ? t('common.loading') : t('public.intake.presentation.submit', { defaultValue: 'Wyślij ankietę' })}
        </button>
      </div>
    </PublicPageShell>
  )
}
