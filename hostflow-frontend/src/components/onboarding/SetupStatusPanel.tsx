import { Link } from 'react-router-dom'
import {
  IconAlertCircle,
  IconArrowRight,
  IconCheck,
  IconCircleMinus,
  IconCircleX,
  IconLoader2,
} from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import type {
  SetupGateId,
  SetupGateStatus,
  SetupReadinessSnapshot,
} from '../../api/onboarding'

const GATE_ORDER: SetupGateId[] = ['G0', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8']

const GATE_ACTION_TEST_ID: Partial<Record<SetupGateId, string>> = {
  G1: 'm1-action-create-company',
  G2: 'm1-action-add-client',
  G3: 'm1-action-add-vacancy',
  G4: 'm1-action-bind-funnel',
  G5: 'm1-action-bind-profile',
  G6: 'm1-action-intake',
  G7: 'm1-action-intake',
  G8: 'm1-action-intake',
}

function gateDataStatus(status: SetupGateStatus, applicable: boolean): string {
  if (!applicable) return 'na'
  if (status === 'pass') return 'pass'
  return 'fail'
}

type SetupStatusPanelProps = {
  snapshot: SetupReadinessSnapshot | null
  loading?: boolean
  className?: string
  onActionNavigate?: () => void
}

function gateStatusIcon(status: SetupGateStatus) {
  if (status === 'pass') {
    return <IconCheck size={16} stroke={2} className="shrink-0 text-emerald-600" aria-hidden />
  }
  if (status === 'fail') {
    return <IconCircleX size={16} stroke={2} className="shrink-0 text-rose-600" aria-hidden />
  }
  return <IconCircleMinus size={16} stroke={2} className="shrink-0 text-slate-400" aria-hidden />
}

export function SetupStatusPanel({ snapshot, loading, className = '', onActionNavigate }: SetupStatusPanelProps) {
  const { t } = useI18n()

  if (loading && !snapshot) {
    return (
      <section
        className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
        aria-busy="true"
      >
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <IconLoader2 size={18} className="animate-spin" aria-hidden />
          {t('app.onboarding.setup_status.loading', { defaultValue: 'Checking setup readiness…' })}
        </div>
      </section>
    )
  }

  if (!snapshot) {
    return (
      <section className={`rounded-2xl border border-rose-200 bg-rose-50/60 p-6 shadow-sm ${className}`}>
        <p className="text-sm text-rose-800">
          {t('app.onboarding.setup_status.load_error', {
            defaultValue: 'Could not load setup status. Refresh the page or try again later.',
          })}
        </p>
      </section>
    )
  }

  const gatesById = new Map(snapshot.gates.map((gate) => [gate.id, gate]))
  const passedCount = snapshot.gates.filter(
    (gate) => gate.applicable && gate.status === 'pass',
  ).length
  const applicableCount = snapshot.gates.filter((gate) => gate.applicable).length
  const nextActionLabel = snapshot.next_action
    ? t(`app.onboarding.${snapshot.next_action.label_key}`, {
        defaultValue: t('app.onboarding.setup_status.next_action_fallback', {
          defaultValue: 'Continue setup',
        }),
      })
    : null

  return (
    <section
      className={`rounded-2xl border bg-white p-6 shadow-sm ${className} ${snapshot.ready ? 'border-emerald-200' : 'border-slate-200'}`}
      data-testid="m1-health-check"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div
            className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold uppercase tracking-wide ${
              snapshot.ready
                ? 'bg-emerald-50 text-emerald-800'
                : 'bg-amber-50 text-amber-900'
            }`}
            data-testid={snapshot.ready ? 'm1-readiness-ready' : 'm1-readiness-not-ready'}
          >
            {snapshot.ready
              ? t('app.onboarding.setup_status.ready_badge', { defaultValue: 'Ready to accept people' })
              : t('app.onboarding.setup_status.not_ready_badge', { defaultValue: 'Setup not complete' })}
          </div>
          <h2 className="mt-3 text-lg font-semibold text-slate-900">
            {t('app.onboarding.setup_status.title', { defaultValue: 'Setup status' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {snapshot.ready
              ? t('app.onboarding.setup_status.ready_subtitle', {
                  defaultValue:
                    'Recruitment готов принимать кандидатов — можно открыть модуль из Launchpad.',
                })
              : t('app.onboarding.setup_status.not_ready_subtitle', {
                  defaultValue:
                    'Состояние модуля Recruitment по операционным шагам — не прогресс мастера.',
                })}
          </p>
          <p className="mt-2 text-xs font-medium text-slate-500">
            {t('app.onboarding.setup_status.gates_progress', {
              defaultValue: 'Gates passed: {passed}/{total}',
              values: { passed: passedCount, total: applicableCount },
            })}
          </p>
        </div>
      </div>

      <ul className="mt-5 space-y-2" aria-label={t('app.onboarding.setup_status.gates_aria', { defaultValue: 'Setup gates' })}>
        {GATE_ORDER.map((gateId) => {
          const gate = gatesById.get(gateId)
          if (!gate) return null
          return (
            <li
              key={gateId}
              data-testid={`m1-gate-${gateId.toLowerCase()}`}
              data-status={gateDataStatus(gate.status, gate.applicable)}
              className={`flex items-start gap-3 rounded-lg border px-3 py-2 text-sm ${
                gate.status === 'fail'
                  ? 'border-rose-200 bg-rose-50/50'
                  : gate.status === 'pass'
                    ? 'border-emerald-100 bg-emerald-50/40'
                    : 'border-slate-100 bg-slate-50/50'
              }`}
            >
              {gateStatusIcon(gate.status)}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">
                    {t(`app.onboarding.setup_status.gates.${gateId.toLowerCase()}.title`, {
                      defaultValue: gateId,
                    })}
                  </span>
                  <span className="text-xs uppercase text-slate-500">{gateId}</span>
                  {!gate.applicable ? (
                    <span className="text-xs text-slate-500">
                      {t('app.onboarding.setup_status.not_applicable', { defaultValue: 'N/A' })}
                    </span>
                  ) : null}
                </div>
                {gate.status === 'fail' && gate.blocker_text ? (
                  <p className="mt-0.5 text-xs text-rose-800">{gate.blocker_text}</p>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>

      {!snapshot.ready && snapshot.blockers.length > 0 ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
          <div className="flex items-start gap-2">
            <IconAlertCircle size={18} className="mt-0.5 shrink-0 text-amber-700" aria-hidden />
            <div>
              <p className="text-sm font-semibold text-slate-900">
                {t('app.onboarding.setup_status.blockers_title', { defaultValue: 'What blocks readiness' })}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-700">
                {snapshot.blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}

      {snapshot.next_action ? (
        <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.onboarding.setup_status.next_action_title', { defaultValue: 'Next action' })}
          </p>
          <p className="mt-1 text-sm text-slate-800">{nextActionLabel}</p>
          <Link
            to={snapshot.next_action.handler_ref}
            data-testid={
              GATE_ACTION_TEST_ID[snapshot.next_action.gate_id] ?? 'm1-next-action'
            }
            onClick={() => onActionNavigate?.()}
            className="mt-3 inline-flex items-center gap-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {nextActionLabel}
            <IconArrowRight size={14} stroke={1.9} aria-hidden />
          </Link>
        </div>
      ) : null}
    </section>
  )
}

export default SetupStatusPanel
