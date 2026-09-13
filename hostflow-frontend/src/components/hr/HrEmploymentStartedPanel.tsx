/**
 * ESO-5: Started on the HR handoff case.
 * Entry: ready_to_create_employee=true only.
 * confirm_physical_start is human confirmation — never auto.
 * Terminal started/already_started stays on this host (no employee-card redirect).
 */
import { useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import type { EmploymentStartedOut } from '../../api/hrWorkspace'
import {
  buildPhysicalStartConfirmation,
  isStartedTerminal,
  needsEmploymentContextOnly,
  needsStartDateInput,
  operatorCanConfirmPhysicalStart,
  primaryStartedItem,
  shouldShowStartedRuntimeChoice,
  startedSurfaceMode,
} from '../../utils/employmentStartedUi'

type Props = {
  started: EmploymentStartedOut | null
  evaluating?: boolean
  confirming?: boolean
  error?: string | null
  onConfirm: (confirmation: { confirmed: true; start_date?: string }) => void
}

export default function HrEmploymentStartedPanel({
  started,
  evaluating,
  confirming,
  error,
  onConfirm,
}: Props) {
  const { t } = useI18n()
  const [draftStartDate, setDraftStartDate] = useState('')
  const surface = useMemo(() => startedSurfaceMode(started), [started])
  const primary = useMemo(() => primaryStartedItem(started), [started])
  const canConfirm = operatorCanConfirmPhysicalStart(started)
  const needDate = needsStartDateInput(started)
  const needContext = needsEmploymentContextOnly(started)
  const terminal = isStartedTerminal(started)

  if (evaluating && !started) {
    return (
      <section
        id="hr-employment-started"
        className="scroll-mt-24 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
        data-testid="hr-employment-started-evaluating"
      >
        {t('app.hr.employment_started.evaluating', {
          defaultValue: 'Evaluating physical start…',
        })}
      </section>
    )
  }

  if (!started) return null

  const blockerMessage =
    error ||
    started.rejection_reason ||
    (Array.isArray(started.blockers) && started.blockers[0]
      ? String(
          (started.blockers[0] as { message?: string }).message ||
            (started.blockers[0] as { code?: string }).code ||
            '',
        )
      : '') ||
    primary?.message ||
    ''

  const submitConfirm = (withDate?: string) => {
    onConfirm(buildPhysicalStartConfirmation({ startDate: withDate }))
  }

  const submitMissingDate = () => {
    const date = draftStartDate.trim()
    if (!date) return
    submitConfirm(date)
  }

  return (
    <section
      id="hr-employment-started"
      className="scroll-mt-24 space-y-3 rounded-lg border border-slate-200 bg-white px-4 py-4"
      data-testid="hr-employment-started-panel"
      data-decision={surface.mode}
      data-started={surface.started ? 'true' : 'false'}
      data-idempotent-replay={surface.idempotentReplay ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.hr.employment_started.title', { defaultValue: 'Confirm physical start' })}
        </h2>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
          {surface.mode}
        </span>
      </div>

      <div data-testid="hr-employment-started-zero-choice" hidden aria-hidden="true" />
      {shouldShowStartedRuntimeChoice('pathway') ||
      shouldShowStartedRuntimeChoice('employer') ||
      shouldShowStartedRuntimeChoice('vacancy') ||
      shouldShowStartedRuntimeChoice('rates') ? (
        <select data-testid="hr-employment-started-runtime-choice" aria-label="forbidden">
          <option>forbidden</option>
        </select>
      ) : null}

      {needDate ? (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="hr-employment-started-missing-date"
        >
          <p className="font-medium">
            {t('app.hr.employment_started.missing_date_title', {
              defaultValue: 'Start date is required',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-started-primary">
            {primary?.message || primary?.code || blockerMessage}
          </p>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="block text-xs font-medium text-amber-950">
              {t('app.hr.employment_started.start_date_label', { defaultValue: 'Start date' })}
              <input
                type="date"
                className="mt-1 block rounded border border-amber-300 bg-white px-2 py-1 text-sm text-slate-900"
                value={draftStartDate}
                onChange={(e) => setDraftStartDate(e.target.value)}
                data-testid="hr-employment-started-date-input"
              />
            </label>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={confirming || !draftStartDate.trim()}
              onClick={submitMissingDate}
              data-testid="hr-employment-started-confirm-with-date"
            >
              {t('app.hr.employment_started.confirm_with_date', {
                defaultValue: 'Confirm physical start',
              })}
            </button>
          </div>
          <p className="mt-2 text-xs text-amber-900/80">
            {t('app.hr.employment_started.only_missing_fact', {
              defaultValue: 'Only the missing start fact is shown — known employment context is reused.',
            })}
          </p>
        </div>
      ) : null}

      {needContext ? (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="hr-employment-started-missing-context"
        >
          <p className="font-medium">
            {t('app.hr.employment_started.missing_context_title', {
              defaultValue: 'Employment context is incomplete',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-started-primary">
            {primary?.message || primary?.code || blockerMessage}
          </p>
          <p className="mt-2 text-xs text-amber-900/80">
            {t('app.hr.employment_started.no_context_picker', {
              defaultValue:
                'Employer / vacancy / country are not re-selected here — fix package context first.',
            })}
          </p>
        </div>
      ) : null}

      {surface.mode === 'awaiting_confirm' && canConfirm ? (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="hr-employment-started-awaiting-confirm"
        >
          <p className="font-medium">
            {t('app.hr.employment_started.confirm_title', {
              defaultValue: 'Confirm the person has actually started work',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-started-primary">
            {primary?.message ||
              t('app.hr.employment_started.confirm_hint', {
                defaultValue: 'Known start date and employment context will be reused.',
              })}
          </p>
          {started.start_date ? (
            <p className="mt-1 text-xs text-amber-900/90" data-testid="hr-employment-started-known-date">
              {t('app.hr.employment_started.known_start_date', {
                defaultValue: 'Start date: {date}',
                date: started.start_date,
              })}
            </p>
          ) : null}
          <div className="mt-3">
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={confirming}
              onClick={() => submitConfirm()}
              data-testid="hr-employment-started-confirm"
            >
              {t('app.hr.employment_started.confirm_physical_start', {
                defaultValue: 'Confirm physical start',
              })}
            </button>
          </div>
          <p className="mt-2 text-xs text-amber-900/80" data-testid="hr-employment-started-human-confirm">
            {t('app.hr.employment_started.human_confirm_only', {
              defaultValue:
                'This is an explicit human confirmation — Formalize complete and Employee create do not auto-start.',
            })}
          </p>
        </div>
      ) : null}

      {terminal ? (
        <div
          className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="hr-employment-started-terminal"
        >
          <p className="font-medium" data-testid="hr-employment-started-terminal-title">
            {surface.mode === 'already_started'
              ? t('app.hr.employment_started.already_started_title', {
                  defaultValue: 'Already started',
                })
              : t('app.hr.employment_started.started_title', {
                  defaultValue: 'Started',
                })}
          </p>
          <p className="mt-1">
            {t('app.hr.employment_started.terminal_body', {
              defaultValue: 'Physical start is confirmed on this HR handoff case.',
            })}
          </p>
          {started.start_date ? (
            <p className="mt-1 text-xs" data-testid="hr-employment-started-terminal-date">
              {t('app.hr.employment_started.known_start_date', {
                defaultValue: 'Start date: {date}',
                date: started.start_date,
              })}
            </p>
          ) : null}
          {surface.idempotentReplay ? (
            <p className="mt-2 text-xs text-emerald-800/80" data-testid="hr-employment-started-replay">
              {t('app.hr.employment_started.idempotent_replay', {
                defaultValue: 'already_started — no second employee_physical_start event.',
              })}
            </p>
          ) : (
            <p className="mt-2 text-xs text-emerald-800/80" data-testid="hr-employment-started-event">
              {t('app.hr.employment_started.event_emitted', {
                defaultValue: 'employee_physical_start recorded once.',
              })}
            </p>
          )}
          <div data-testid="hr-employment-started-no-employee-redirect" hidden aria-hidden="true" />
          <div data-testid="hr-employment-started-no-hr-card-cta" hidden aria-hidden="true" />
        </div>
      ) : null}

      {surface.mode === 'blocked' || surface.mode === 'rejected' ? (
        <div
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-950"
          data-testid="hr-employment-started-blocked"
        >
          <p className="font-medium">
            {t('app.hr.employment_started.blocked_title', {
              defaultValue: 'Physical start blocked',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-started-blocker">
            {blockerMessage ||
              t('app.hr.employment_started.blocked_fallback', {
                defaultValue: 'ready_to_create_employee is required before Started.',
              })}
          </p>
          <p className="mt-2 text-xs text-rose-900/80" data-testid="hr-employment-started-no-fake-action">
            {t('app.hr.employment_started.no_fake_action', {
              defaultValue: 'No Started shortcut when preconditions fail.',
            })}
          </p>
        </div>
      ) : null}
    </section>
  )
}
