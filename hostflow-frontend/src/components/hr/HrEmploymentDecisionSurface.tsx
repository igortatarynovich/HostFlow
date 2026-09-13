/**
 * ESO-2 + ESO-3: one Employment Decision Surface on the HR handoff case.
 * Employability → one missing → resolve → auto re-eval. No Formalize UI. No Employee.
 */
import { useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import type { EarlyEmployabilityOut } from '../../api/hrWorkspace'
import {
  buildResolutionPatchForNextStep,
  decisionSurfaceMode,
  operatorCanResolveCurrentGap,
  primaryNextStep,
  shouldShowPathwaySelector,
} from '../../utils/employmentDecisionUi'

type Props = {
  employability: EarlyEmployabilityOut | null
  evaluating?: boolean
  resolving?: boolean
  error?: string | null
  onResolve: (patch: { facts?: Record<string, unknown>; evidence?: Record<string, unknown> }) => void
}

export default function HrEmploymentDecisionSurface({
  employability,
  evaluating,
  resolving,
  error,
  onResolve,
}: Props) {
  const { t } = useI18n()
  const [citizenship, setCitizenship] = useState('')
  const [employmentCountry, setEmploymentCountry] = useState('PL')
  const [workAuth, setWorkAuth] = useState(false)

  const { mode, readyForFormalize } = useMemo(
    () => decisionSurfaceMode(employability),
    [employability],
  )
  const nextStep = useMemo(() => primaryNextStep(employability), [employability])
  const canResolve = operatorCanResolveCurrentGap(employability)
  const nextCode = String(nextStep?.code || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')

  if (evaluating && !employability) {
    return (
      <section
        id="hr-employment-decision"
        className="scroll-mt-24 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
        data-testid="hr-employment-decision-evaluating"
      >
        {t('app.hr.employment_decision.evaluating', {
          defaultValue: 'Evaluating employability…',
        })}
      </section>
    )
  }

  if (!employability) return null

  const blockerMessage =
    error ||
    (Array.isArray(employability.blockers) && employability.blockers[0]
      ? String(
          (employability.blockers[0] as { message?: string }).message ||
            (employability.blockers[0] as { code?: string }).code ||
            '',
        )
      : '') ||
    nextStep?.label ||
    ''

  const submitResolve = () => {
    if (!nextStep?.code) return
    const patch = buildResolutionPatchForNextStep(nextStep.code, {
      citizenship,
      employmentCountry,
      workAuthorizationPresent: workAuth,
    })
    if (!patch) return
    onResolve(patch)
  }

  return (
    <section
      id="hr-employment-decision"
      className="scroll-mt-24 space-y-3 rounded-lg border border-slate-200 bg-white px-4 py-4"
      data-testid="hr-employment-decision-surface"
      data-decision={mode}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.hr.employment_decision.title', { defaultValue: 'Employment decision' })}
        </h2>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
          {mode}
        </span>
      </div>

      {/* Zero-choice proof: pathway/status/permit menus are forbidden. */}
      <div data-testid="hr-employment-decision-zero-choice" hidden aria-hidden="true" />
      {shouldShowPathwaySelector(employability) ? (
        <select data-testid="hr-employment-decision-pathway-select" aria-label="pathway">
          <option>forbidden</option>
        </select>
      ) : null}

      {readyForFormalize ? (
        <div
          className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="hr-employment-decision-employable"
        >
          <p className="font-medium">
            {t('app.hr.employment_decision.employable_title', {
              defaultValue: 'Employable — ready for Formalize',
            })}
          </p>
          <p className="mt-1 text-xs text-emerald-800/90">
            {nextStep?.label ||
              t('app.hr.employment_decision.employable_next', {
                defaultValue: 'Next product boundary is ESO-4 Formalize (not opened in this surface).',
              })}
          </p>
          <p className="mt-2 text-xs text-emerald-800/80" data-testid="hr-employment-decision-ready-formalize">
            {t('app.hr.employment_decision.formalize_deferred', {
              defaultValue: 'Formalize UI is out of scope here. Employee is not created.',
            })}
          </p>
        </div>
      ) : null}

      {mode === 'insufficient_facts' ? (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="hr-employment-decision-insufficient"
        >
          <p className="font-medium">
            {t('app.hr.employment_decision.insufficient_title', {
              defaultValue: 'One fact or evidence is needed',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-decision-primary">
            {nextStep?.label || blockerMessage}
          </p>

          {canResolve && nextCode === 'provide_citizenship' ? (
            <div className="mt-3 flex flex-wrap items-end gap-2">
              <label className="block text-xs font-medium text-amber-950">
                {t('app.hr.employment_decision.citizenship_label', {
                  defaultValue: 'Citizenship (ISO alpha-2)',
                })}
                <input
                  className="mt-1 block w-24 rounded border border-amber-300 bg-white px-2 py-1.5 text-sm uppercase"
                  maxLength={2}
                  value={citizenship}
                  onChange={(e) => setCitizenship(e.target.value.toUpperCase())}
                  data-testid="hr-employment-decision-citizenship"
                  autoComplete="off"
                />
              </label>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={resolving || citizenship.trim().length !== 2}
                onClick={submitResolve}
                data-testid="hr-employment-decision-resolve"
              >
                {t('app.hr.employment_decision.resolve', { defaultValue: 'Supply and continue' })}
              </button>
            </div>
          ) : null}

          {canResolve && nextCode === 'provide_employment_country' ? (
            <div className="mt-3 flex flex-wrap items-end gap-2">
              <label className="block text-xs font-medium text-amber-950">
                {t('app.hr.employment_decision.country_label', {
                  defaultValue: 'Employment country',
                })}
                <input
                  className="mt-1 block w-24 rounded border border-amber-300 bg-white px-2 py-1.5 text-sm uppercase"
                  maxLength={2}
                  value={employmentCountry}
                  onChange={(e) => setEmploymentCountry(e.target.value.toUpperCase())}
                  data-testid="hr-employment-decision-country"
                />
              </label>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={resolving || !employmentCountry.trim()}
                onClick={submitResolve}
                data-testid="hr-employment-decision-resolve"
              >
                {t('app.hr.employment_decision.resolve', { defaultValue: 'Supply and continue' })}
              </button>
            </div>
          ) : null}

          {canResolve && nextCode === 'provide_work_authorization_evidence' ? (
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm text-amber-950">
                <input
                  type="checkbox"
                  checked={workAuth}
                  onChange={(e) => setWorkAuth(e.target.checked)}
                  data-testid="hr-employment-decision-work-auth"
                />
                {t('app.hr.employment_decision.work_auth_label', {
                  defaultValue: 'Work authorization evidence is available for this case',
                })}
              </label>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={resolving || !workAuth}
                onClick={submitResolve}
                data-testid="hr-employment-decision-resolve"
              >
                {t('app.hr.employment_decision.resolve', { defaultValue: 'Supply and continue' })}
              </button>
            </div>
          ) : null}

          <p className="mt-2 text-xs text-amber-900/80">
            {t('app.hr.employment_decision.auto_reeval', {
              defaultValue: 'After supply, employability re-evaluates automatically — no “check again” step.',
            })}
          </p>
        </div>
      ) : null}

      {mode === 'blocked' ? (
        <div
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-950"
          data-testid="hr-employment-decision-blocked"
        >
          <p className="font-medium">
            {t('app.hr.employment_decision.blocked_title', {
              defaultValue: 'Employment blocked',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-decision-blocker">
            {blockerMessage ||
              t('app.hr.employment_decision.blocked_fallback', {
                defaultValue: 'Concrete employment blockers prevent employ-now.',
              })}
          </p>
          <p className="mt-2 text-xs text-rose-900/80" data-testid="hr-employment-decision-no-fake-action">
            {t('app.hr.employment_decision.no_fake_action', {
              defaultValue: 'No operator action is offered when the blocker cannot be cleared here.',
            })}
          </p>
        </div>
      ) : null}

      {employability.legal_pathway?.pathway_id ? (
        <p className="text-xs text-slate-500" data-testid="hr-employment-decision-pathway-readonly">
          {t('app.hr.employment_decision.pathway_set', {
            defaultValue: 'Legal pathway (system): {id}',
            id: employability.legal_pathway.pathway_id,
          })}
        </p>
      ) : null}
    </section>
  )
}
