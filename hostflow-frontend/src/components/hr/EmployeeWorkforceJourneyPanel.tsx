import { useMemo } from 'react'
import clsx from 'clsx'
import CandidateStageJourneyPanel from '../candidate/CandidateStageJourneyPanel'
import { useI18n } from '../../i18n'
import type { WorkforceEmployee, WorkforceHrBundle } from '../../api/workforce'
import { canonicalStageKey } from '../../utils/stageLabels'

type Props = {
  locale: string
  employee: WorkforceEmployee
  bundle: WorkforceHrBundle
  /** Linked candidate recruitment stage (for “trip / line” milestone). */
  candidateStage?: string | null
  /** Lighter surface when nested inside the employee hero gradient. */
  hero?: boolean
}

type Step = { code: string; label: string }

function stepDone(
  code: string,
  ctx: {
    tasks: WorkforceHrBundle['onboarding_tasks']
    zus: WorkforceHrBundle['zus_profile']
    payroll: WorkforceHrBundle['payroll_profile']
    employments: WorkforceHrBundle['employments']
    employeeStatus: string
    candidateStage: string | null | undefined
  },
): boolean {
  switch (code) {
    case 'wf_onboarding': {
      const tasks = ctx.tasks || []
      if (!tasks.length) return true
      return tasks.every((t) => String(t.status || '').toLowerCase() === 'done')
    }
    case 'wf_zus': {
      const st = String(ctx.zus?.registration_status || '').toLowerCase()
      return st === 'active' || st === 'submitted'
    }
    case 'wf_payroll': {
      const st = String(ctx.payroll?.payroll_status || '').toLowerCase()
      return st === 'sent_to_accounting' || st === 'settled' || st === 'ready_for_payroll'
    }
    case 'wf_contract':
      return (ctx.employments || []).length > 0
    case 'wf_active': {
      const st = String(ctx.employeeStatus || '').toLowerCase()
      return st === 'active' || st === 'on_vacation' || st === 'on_sick_leave' || st === 'on_leave'
    }
    case 'wf_trip': {
      const c = canonicalStageKey(ctx.candidateStage, null) || String(ctx.candidateStage || '').toLowerCase()
      return c === 'on_trip' || c === 'employed'
    }
    default:
      return false
  }
}

export default function EmployeeWorkforceJourneyPanel({
  locale,
  employee,
  bundle,
  candidateStage,
  hero = false,
}: Props) {
  const { t } = useI18n()

  const stages: Step[] = useMemo(
    () => [
      {
        code: 'wf_onboarding',
        label: t('app.hr.employee_detail.workforce_journey.onboarding', { defaultValue: 'HR onboarding' }),
      },
      {
        code: 'wf_zus',
        label: t('app.hr.employee_detail.workforce_journey.zus', { defaultValue: 'ZUS registration' }),
      },
      {
        code: 'wf_payroll',
        label: t('app.hr.employee_detail.workforce_journey.payroll', { defaultValue: 'Payroll setup' }),
      },
      {
        code: 'wf_contract',
        label: t('app.hr.employee_detail.workforce_journey.contract', { defaultValue: 'Contract / employment' }),
      },
      {
        code: 'wf_active',
        label: t('app.hr.employee_detail.workforce_journey.active', { defaultValue: 'Active employee' }),
      },
      {
        code: 'wf_trip',
        label: t('app.hr.employee_detail.workforce_journey.trip', { defaultValue: 'Line / trip (recruitment stage)' }),
      },
    ],
    [t],
  )

  const ctx = useMemo(
    () => ({
      tasks: bundle.onboarding_tasks,
      zus: bundle.zus_profile,
      payroll: bundle.payroll_profile,
      employments: bundle.employments,
      employeeStatus: employee.status,
      candidateStage,
    }),
    [bundle, employee.status, candidateStage],
  )

  const { currentStage, completedCodes, blockers } = useMemo(() => {
    const completed = new Set<string>()
    let firstOpen: string | null = null
    let blocked = false
    for (const s of stages) {
      const done = stepDone(s.code, ctx)
      if (done) {
        completed.add(s.code)
      } else {
        if (!firstOpen) {
          firstOpen = s.code
          blocked = true
        }
      }
    }
    return {
      currentStage: firstOpen || stages[stages.length - 1]?.code || null,
      completedCodes: completed,
      blockers: blocked,
    }
  }, [stages, ctx])

  return (
    <section
      className={clsx(
        hero
          ? 'rounded-xl border border-white/25 bg-white/95 p-3 shadow-sm backdrop-blur-[1px]'
          : 'rounded-2xl border border-slate-200 bg-white p-3',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs font-semibold text-slate-700">
            {t('app.hr.employee_detail.workforce_journey.title', {
              defaultValue: 'Employment & deployment',
            })}
          </div>
          <p className="mt-1 text-[11px] text-slate-500 max-w-xl">
            {hero
              ? t('app.hr.employee_detail.workforce_journey.hint_hero', {
                  defaultValue:
                    'HR timeline: onboarding → compliance → payroll → contract → active. Use the row below for deployment stages on the linked candidate after recruitment handoff.',
                })
              : t('app.hr.employee_detail.workforce_journey.hint', {
                  defaultValue:
                    'Checklist through hire, payroll, contract, and active status. “Line / trip” follows the linked candidate stage when available.',
                })}
          </p>
        </div>
        {ctx.candidateStage ? (
          <span
            className={clsx(
              'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
              blockers ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900',
            )}
          >
            {t('app.hr.employee_detail.workforce_journey.candidate_stage', {
              defaultValue: 'Candidate stage: {stage}',
              values: { stage: String(candidateStage) },
            })}
          </span>
        ) : null}
      </div>
      <div className="mt-3">
        <CandidateStageJourneyPanel
          locale={locale}
          variant="horizontal"
          tone="default"
          compact
          stages={stages}
          outcomeStages={[]}
          currentStage={currentStage}
          currentOutcomeStage={null}
          signals={[]}
          stageSinceAt={null}
          completedStageCodes={completedCodes}
          canEdit={false}
          blocked={blockers}
        />
      </div>
    </section>
  )
}
