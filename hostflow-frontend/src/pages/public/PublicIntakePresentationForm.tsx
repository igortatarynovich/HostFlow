import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { ConsentRow } from '../../components/public/ConsentRow'
import { INTAKE_LEGAL_URLS } from '../../components/public/IntakePresentationConsents'
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
import { intakePresentationProfileTitle } from '../../utils/intakePresentationI18n'

type Props = {
  intake: PublicIntakeHook
  presentation: FormPresentationRuntime
}

type ValueState = Record<string, PresentationFieldValue>
type ConsentKey = 'general' | 'employer_share' | 'terms_acceptance'

const CONSENT_ORDER: ConsentKey[] = ['general', 'employer_share', 'terms_acceptance']

function presentationSectionKey(code: string): string {
  const leaf = (code.split('.').pop() || code).toLowerCase()
  if (leaf.startsWith('contact_')) return 'contact'
  if (leaf.startsWith('recruitment_')) return 'recruitment'
  if (leaf.startsWith('promotion_') || leaf.startsWith('marketing_') || leaf.startsWith('client_geo')) {
    return 'promotion'
  }
  if (leaf.startsWith('client_') || leaf.includes('company')) return 'company'
  return 'needs'
}

export default function PublicIntakePresentationForm({ intake, presentation }: Props) {
  const { t, locale, setLocale } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
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
  const requestedLang = searchParams.get('lang')
  const [languageConfirmed, setLanguageConfirmed] = useState(
    () => requestedLang === 'pl' || requestedLang === 'en' || requestedLang === 'ru',
  )

  useEffect(() => {
    if (requestedLang === 'pl' || requestedLang === 'en' || requestedLang === 'ru') {
      setLocale(requestedLang)
      setLanguageConfirmed(true)
    }
  }, [requestedLang, setLocale])

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
  const [consentErrors, setConsentErrors] = useState<Partial<Record<ConsentKey, string>>>({})
  const [showConsentErrors, setShowConsentErrors] = useState(false)
  const consentRefs = {
    general: useRef<HTMLInputElement>(null),
    employer_share: useRef<HTMLInputElement>(null),
    terms_acceptance: useRef<HTMLInputElement>(null),
  }

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

  const sectionedFields = useMemo(() => {
    const groups: Array<{ key: string; fields: typeof visibleFields }> = []
    for (const field of visibleFields) {
      const key = presentationSectionKey(field.qualified_code)
      const last = groups[groups.length - 1]
      if (!last || last.key !== key) {
        groups.push({ key, fields: [field] })
      } else {
        last.fields.push(field)
      }
    }
    return groups
  }, [visibleFields])

  const sectionTitle = useCallback(
    (key: string) => {
      const titles: Record<string, string> = {
        contact: t('public.intake.presentation.section_contact', { defaultValue: 'Kontakt' }),
        recruitment: t('public.intake.presentation.section_recruitment', { defaultValue: 'Rekrutacja' }),
        promotion: t('public.intake.presentation.section_promotion', { defaultValue: 'Promocja' }),
        company: t('public.intake.presentation.section_company', { defaultValue: 'Firma' }),
        needs: t('public.intake.presentation.section_needs', { defaultValue: 'Potrzeby' }),
      }
      return titles[key] || titles.needs
    },
    [t],
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
      for (const key of Object.keys(patch) as ConsentKey[]) {
        if (patch[key]) {
          setConsentErrors((prev) => {
            if (!prev[key]) return prev
            const copy = { ...prev }
            delete copy[key]
            return copy
          })
        }
      }
    },
    [cookiesAccepted, updateAgreements],
  )

  const validateConsents = useCallback(() => {
    const requiredMessage = t('public.intake.presentation.consent_required', {
      defaultValue: 'To pole jest wymagane',
    })
    const nextErrors: Partial<Record<ConsentKey, string>> = {}
    for (const key of CONSENT_ORDER) {
      if (!agreements[key]) nextErrors[key] = requiredMessage
    }
    setConsentErrors(nextErrors)
    setShowConsentErrors(true)
    const firstMissing = CONSENT_ORDER.find((key) => !agreements[key])
    if (firstMissing) {
      consentRefs[firstMissing].current?.focus()
      consentRefs[firstMissing].current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return false
    }
    return true
  }, [agreements, consentRefs, t])

  const handleSubmit = async () => {
    syncPresentationValues(values)
    if (!validateRequired()) return
    if (!validateConsents()) return
    const cookieReady = Boolean(agreements.cookies_accepted || cookiesAccepted)
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

  if (!languageConfirmed) {
    const chooseLanguage = (lang: 'pl' | 'en' | 'ru') => {
      setLocale(lang)
      setLanguageConfirmed(true)
      const next = new URLSearchParams(searchParams)
      next.set('lang', lang)
      setSearchParams(next, { replace: true })
    }
    return (
      <PublicPageShell maxWidth="md">
        <div className="card p-8 text-center">
          <h1 className="text-xl font-semibold text-slate-900">
            {t('public.intake.language.title', { defaultValue: 'Choose language' })}
          </h1>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {(['pl', 'en', 'ru'] as const).map((lang) => (
              <button
                key={lang}
                type="button"
                className="btn-secondary rounded-lg px-4 py-2 text-sm font-semibold uppercase"
                onClick={() => chooseLanguage(lang)}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>
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
          {state.status_share_token && state.data?.application_kind !== 'client' ? (
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
            {intakePresentationProfileTitle(t, presentation, locale)}
          </h1>
        </div>
        <AutosaveIndicator saving={saving} />
      </div>

      <div className="card space-y-4 p-5 sm:p-6">
        {sectionedFields.map((section, sectionIndex) => (
          <section
            key={`${section.key}-${sectionIndex}`}
            className={sectionIndex > 0 ? 'border-t border-slate-200 pt-4' : undefined}
          >
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {sectionTitle(section.key)}
            </h2>
            <div className="space-y-3">
              {section.fields.map((field) => (
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
            </div>
          </section>
        ))}

        <div className="space-y-2 border-t border-slate-200 pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            {t('public.intake.presentation.section_consents', { defaultValue: 'Zgody' })}
          </h2>
          <ConsentRow
            id="presentation-consent-general"
            ref={consentRefs.general}
            checked={agreements.general}
            disabled={submitting}
            showError={showConsentErrors}
            errorMessage={consentErrors.general}
            onChange={(checked) => patchAgreements({ general: checked })}
          >
            {t('public.intake.presentation.consent_general_prefix', { defaultValue: 'Akceptuję' })}{' '}
            <a href={INTAKE_LEGAL_URLS.privacy} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
              {t('public.intake.presentation.consent_general_link', { defaultValue: 'politykę prywatności' })}
            </a>
          </ConsentRow>
          <ConsentRow
            id="presentation-consent-share"
            ref={consentRefs.employer_share}
            checked={agreements.employer_share}
            disabled={submitting}
            showError={showConsentErrors}
            errorMessage={consentErrors.employer_share}
            onChange={(checked) => patchAgreements({ employer_share: checked })}
          >
            {t('public.intake.presentation.consent_share_prefix', { defaultValue: 'Wyrażam zgodę na' })}{' '}
            <a href={INTAKE_LEGAL_URLS.rodo} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
              {t('public.intake.presentation.consent_share_link', { defaultValue: 'udostępnienie danych' })}
            </a>
          </ConsentRow>
          <ConsentRow
            id="presentation-consent-terms"
            ref={consentRefs.terms_acceptance}
            checked={agreements.terms_acceptance}
            disabled={submitting}
            showError={showConsentErrors}
            errorMessage={consentErrors.terms_acceptance}
            onChange={(checked) => patchAgreements({ terms_acceptance: checked })}
          >
            {t('public.intake.presentation.consent_terms_prefix', { defaultValue: 'Akceptuję' })}{' '}
            <a href={INTAKE_LEGAL_URLS.terms} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
              {t('public.intake.presentation.consent_terms_link', { defaultValue: 'regulamin' })}
            </a>
          </ConsentRow>
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
