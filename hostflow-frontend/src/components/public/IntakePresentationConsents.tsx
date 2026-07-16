import type { ReactNode } from 'react'
import { useI18n } from '../../i18n'
import { ConsentRow } from './ConsentRow'

export const INTAKE_LEGAL_URLS = {
  privacy: '/legal/privacy.html',
  terms: '/legal/terms.html',
  rodo: '/legal/rodo.html',
} as const

type AgreementsState = {
  general: boolean
  employer_share: boolean
  terms_acceptance: boolean
  rodo_acknowledgment: boolean
}

type ConsentErrors = Partial<Record<keyof AgreementsState, string>>

type Props = {
  agreements: AgreementsState
  onChange: (patch: Partial<AgreementsState>) => void
  showErrors?: boolean
  errors?: ConsentErrors
  disabled?: boolean
  consentRefs?: Partial<Record<keyof AgreementsState, React.RefObject<HTMLInputElement | null>>>
}

function LegalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
      {children}
    </a>
  )
}

export function IntakePresentationConsents({
  agreements,
  onChange,
  showErrors = false,
  errors = {},
  disabled = false,
  consentRefs,
}: Props) {
  const { t } = useI18n()
  const requiredMessage = t('public.intake.presentation.consent_required', {
    defaultValue: 'To pole jest wymagane',
  })

  return (
    <div className="space-y-2">
      <ConsentRow
        id="consent-general"
        ref={consentRefs?.general}
        checked={agreements.general}
        disabled={disabled}
        showError={showErrors}
        errorMessage={errors.general || requiredMessage}
        onChange={(checked) => onChange({ general: checked })}
      >
        {t('public.intake.presentation.consent_general_prefix', { defaultValue: 'Akceptuję' })}{' '}
        <LegalLink href={INTAKE_LEGAL_URLS.privacy}>
          {t('public.intake.presentation.consent_general_link', { defaultValue: 'politykę prywatności' })}
        </LegalLink>
      </ConsentRow>

      <ConsentRow
        id="consent-employer-share"
        ref={consentRefs?.employer_share}
        checked={agreements.employer_share}
        disabled={disabled}
        showError={showErrors}
        errorMessage={errors.employer_share || requiredMessage}
        onChange={(checked) => onChange({ employer_share: checked })}
      >
        {t('public.intake.presentation.consent_share_prefix', { defaultValue: 'Wyrażam zgodę na' })}{' '}
        <LegalLink href={INTAKE_LEGAL_URLS.rodo}>
          {t('public.intake.presentation.consent_share_link', { defaultValue: 'udostępnienie danych' })}
        </LegalLink>
      </ConsentRow>

      <ConsentRow
        id="consent-terms"
        ref={consentRefs?.terms_acceptance}
        checked={agreements.terms_acceptance}
        disabled={disabled}
        showError={showErrors}
        errorMessage={errors.terms_acceptance || requiredMessage}
        onChange={(checked) => onChange({ terms_acceptance: checked })}
      >
        {t('public.intake.presentation.consent_terms_prefix', { defaultValue: 'Akceptuję' })}{' '}
        <LegalLink href={INTAKE_LEGAL_URLS.terms}>
          {t('public.intake.presentation.consent_terms_link', { defaultValue: 'regulamin' })}
        </LegalLink>
      </ConsentRow>

      <ConsentRow
        id="consent-rodo"
        ref={consentRefs?.rodo_acknowledgment}
        checked={agreements.rodo_acknowledgment}
        disabled={disabled}
        showError={showErrors}
        errorMessage={errors.rodo_acknowledgment || requiredMessage}
        onChange={(checked) => onChange({ rodo_acknowledgment: checked })}
      >
        {t('public.intake.presentation.consent_rodo_prefix', { defaultValue: 'Zapoznałem się z' })}{' '}
        <LegalLink href={INTAKE_LEGAL_URLS.rodo}>
          {t('public.intake.presentation.consent_rodo_link', { defaultValue: 'informacją RODO' })}
        </LegalLink>
      </ConsentRow>
    </div>
  )
}

export function allPresentationConsentsAccepted(agreements: AgreementsState): boolean {
  return (
    agreements.general &&
    agreements.employer_share &&
    agreements.terms_acceptance &&
    agreements.rodo_acknowledgment
  )
}
