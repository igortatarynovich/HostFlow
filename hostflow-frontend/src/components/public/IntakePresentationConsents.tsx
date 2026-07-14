import type { ReactNode } from 'react'
import { useI18n } from '../../i18n'

const LEGAL_LINK_CLASS = 'text-brand-700 underline-offset-2 hover:underline'

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

type Props = {
  agreements: AgreementsState
  onChange: (patch: Partial<AgreementsState>) => void
  showErrors?: boolean
}

function LegalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={LEGAL_LINK_CLASS}>
      {children}
    </a>
  )
}

export function IntakePresentationConsents({ agreements, onChange, showErrors = false }: Props) {
  const { t } = useI18n()

  const labelClass = (checked: boolean) =>
    `flex items-start gap-2 rounded-lg border px-2 py-2 text-sm transition ${
      showErrors && !checked ? 'border-rose-400 bg-rose-50 text-rose-900' : 'border-transparent text-slate-700'
    }`

  return (
    <div className="space-y-3">
      <label className={labelClass(agreements.general)}>
        <input
          type="checkbox"
          className={`mt-0.5 ${showErrors && !agreements.general ? 'outline outline-2 outline-rose-500' : ''}`}
          checked={agreements.general}
          onChange={(e) => onChange({ general: e.target.checked })}
        />
        <span>
          {t('public.intake.presentation.consent_general_prefix', { defaultValue: 'I accept the' })}{' '}
          <LegalLink href={INTAKE_LEGAL_URLS.privacy}>
            {t('public.intake.presentation.consent_general_link', { defaultValue: 'privacy policy' })}
          </LegalLink>
        </span>
      </label>

      <label className={labelClass(agreements.employer_share)}>
        <input
          type="checkbox"
          className={`mt-0.5 ${showErrors && !agreements.employer_share ? 'outline outline-2 outline-rose-500' : ''}`}
          checked={agreements.employer_share}
          onChange={(e) => onChange({ employer_share: e.target.checked })}
        />
        <span>{t('public.intake.presentation.consent_share', { defaultValue: 'I agree to share data with employers' })}</span>
      </label>

      <label className={labelClass(agreements.terms_acceptance)}>
        <input
          type="checkbox"
          className={`mt-0.5 ${showErrors && !agreements.terms_acceptance ? 'outline outline-2 outline-rose-500' : ''}`}
          checked={agreements.terms_acceptance}
          onChange={(e) => onChange({ terms_acceptance: e.target.checked })}
        />
        <span>
          {t('public.intake.presentation.consent_terms_prefix', { defaultValue: 'I accept the' })}{' '}
          <LegalLink href={INTAKE_LEGAL_URLS.terms}>
            {t('public.intake.presentation.consent_terms_link', { defaultValue: 'terms of use' })}
          </LegalLink>
        </span>
      </label>

      <label className={labelClass(agreements.rodo_acknowledgment)}>
        <input
          type="checkbox"
          className={`mt-0.5 ${showErrors && !agreements.rodo_acknowledgment ? 'outline outline-2 outline-rose-500' : ''}`}
          checked={agreements.rodo_acknowledgment}
          onChange={(e) => onChange({ rodo_acknowledgment: e.target.checked })}
        />
        <span>
          {t('public.intake.presentation.consent_rodo_prefix', { defaultValue: 'I have read the' })}{' '}
          <LegalLink href={INTAKE_LEGAL_URLS.rodo}>
            {t('public.intake.presentation.consent_rodo_link', { defaultValue: 'RODO information' })}
          </LegalLink>
        </span>
      </label>
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
