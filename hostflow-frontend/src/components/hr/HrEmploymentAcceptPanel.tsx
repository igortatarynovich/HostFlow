/**
 * ESO-1: Employment accept policy surface on the existing HR handoff case.
 * Does not host Formalize / Started. Does not mint ESO-2 UI.
 */
import { useI18n } from '../../i18n'
import type { EmploymentAcceptPolicyOut } from '../../api/hrWorkspace'
import {
  employmentAcceptBlockerLabel,
  primaryEmploymentAcceptBlocker,
} from '../../utils/employmentAcceptUi'

type Props = {
  policy: EmploymentAcceptPolicyOut | null
  applying?: boolean
  error?: string | null
  onRetry?: () => void
}

export default function HrEmploymentAcceptPanel({ policy, applying, error, onRetry }: Props) {
  const { t } = useI18n()
  const blocker = primaryEmploymentAcceptBlocker(policy)
  const blockerLabel = employmentAcceptBlockerLabel(blocker)
  const accepted = Boolean(policy?.accepted || policy?.employment_started)
  const decision = String(policy?.decision || '').trim()

  if (applying && !policy) {
    return (
      <section
        id="hr-employment-accept"
        className="scroll-mt-24 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
        data-testid="hr-employment-accept-applying"
      >
        {t('app.hr.employment_accept.applying', {
          defaultValue: 'Applying employment accept policy…',
        })}
      </section>
    )
  }

  if (accepted) {
    return (
      <section
        id="hr-employment-accept"
        className="scroll-mt-24 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3"
        data-testid="hr-employment-accept-accepted"
      >
        <h2 className="text-sm font-semibold text-emerald-900">
          {t('app.hr.employment_accept.accepted_title', {
            defaultValue: 'Employment case accepted',
          })}
        </h2>
        <p className="mt-1 text-sm text-emerald-800">
          {policy?.message ||
            t('app.hr.employment_accept.employment_started', {
              defaultValue: 'Employment started',
            })}
        </p>
        <p className="mt-2 text-xs text-emerald-800/90">
          {t('app.hr.employment_accept.next_employability', {
            defaultValue:
              'Next: employability / employment missing (ESO-2–3). Approve for employment is not the Employment happy path.',
          })}
        </p>
      </section>
    )
  }

  if (error || (policy && decision && decision !== 'auto_accept')) {
    return (
      <section
        id="hr-employment-accept"
        className="scroll-mt-24 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
        data-testid="hr-employment-accept-blocked"
      >
        <h2 className="text-sm font-semibold text-amber-950">
          {t('app.hr.employment_accept.blocked_title', {
            defaultValue: 'Employment accept needs attention',
          })}
        </h2>
        <p className="mt-1 text-sm text-amber-900" data-testid="hr-employment-accept-blocker">
          {error ||
            blockerLabel ||
            policy?.message ||
            t('app.hr.employment_accept.blocked_fallback', {
              defaultValue: 'Concrete employment blockers must be resolved before accept.',
            })}
        </p>
        {onRetry ? (
          <div className="mt-3">
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={applying}
              onClick={onRetry}
              data-testid="hr-employment-accept-retry"
            >
              {t('app.hr.employment_accept.retry', {
                defaultValue: 'Retry employment accept policy',
              })}
            </button>
          </div>
        ) : null}
        <p className="mt-2 text-xs text-amber-900/80">
          {t('app.hr.employment_accept.no_ritual', {
            defaultValue: 'Ritual “Take into HR review” is not used when Employment policy owns accept.',
          })}
        </p>
      </section>
    )
  }

  return null
}
