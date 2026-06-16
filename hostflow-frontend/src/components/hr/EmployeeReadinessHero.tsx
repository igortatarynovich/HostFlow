import clsx from 'clsx'
import type { EmployeeReadinessSummary, ReadinessPrimaryCta } from '../../utils/buildEmployeeReadinessSummary'
import { useI18n } from '../../i18n'

type Props = {
  summary: EmployeeReadinessSummary
  loading?: boolean
  followUpMessage?: string | null
  onPrimaryAction?: (cta: ReadinessPrimaryCta) => void
}

const STATUS_STYLES = {
  ready: 'border-emerald-300 bg-gradient-to-br from-emerald-50 to-white text-emerald-950',
  not_ready: 'border-rose-300 bg-gradient-to-br from-rose-50 to-white text-rose-950',
  attention: 'border-amber-300 bg-gradient-to-br from-amber-50 to-white text-amber-950',
}

export function EmployeeReadinessHero({
  summary,
  loading = false,
  followUpMessage = null,
  onPrimaryAction,
}: Props) {
  const { t } = useI18n()
  const primary = summary.primary
  const cta = summary.primaryCta

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      </section>
    )
  }

  return (
    <section
      className={clsx(
        'rounded-2xl border-2 p-5 shadow-sm sm:p-6',
        STATUS_STYLES[summary.status],
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.14em] opacity-80">
            {t('app.hr.readiness.status_label', { defaultValue: 'Readiness status' })}
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight">{summary.statusLabel}</div>
          {summary.verificationProgress ? (
            <p className="mt-1 text-xs font-medium opacity-80">
              {t('app.hr.readiness.verification_progress', {
                defaultValue: 'Verified {verified} of {total} uploaded documents',
                values: summary.verificationProgress,
              })}
            </p>
          ) : null}
        </div>
        {cta && onPrimaryAction ? (
          <button type="button" className="btn-primary btn-sm" onClick={() => onPrimaryAction(cta)}>
            {cta.label}
          </button>
        ) : null}
      </div>

      {followUpMessage ? (
        <div className="mt-4 rounded-lg border border-current/20 bg-white/80 px-3 py-2 text-sm font-medium">
          {followUpMessage}
        </div>
      ) : null}

      {primary ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
              {t('app.hr.readiness.next_action', { defaultValue: 'Next action' })}
            </div>
            <div className="mt-1 text-xl font-semibold leading-snug">{primary.actionTitle}</div>
            {summary.remainingBlockingCount > 1 ? (
              <p className="mt-1 text-xs font-medium opacity-80">
                {t('app.hr.readiness.remaining', {
                  defaultValue: '{count} documents remaining',
                  values: { count: summary.remainingBlockingCount },
                })}
              </p>
            ) : null}
          </div>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
                {t('app.hr.readiness.reason', { defaultValue: 'Reason' })}
              </dt>
              <dd className="mt-1 font-medium">{primary.reason}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
                {t('app.hr.readiness.blocks', { defaultValue: 'Blocks' })}
              </dt>
              <dd className="mt-1 font-medium">{primary.blockLabel}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
                {t('app.hr.readiness.owner', { defaultValue: 'Responsible' })}
              </dt>
              <dd className="mt-1 font-medium">{primary.responsible}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
                {t('app.hr.readiness.due', { defaultValue: 'Due' })}
              </dt>
              <dd className="mt-1 font-medium">{primary.dueLabel}</dd>
            </div>
          </dl>
          {primary.missingItems.length > 0 ? (
            <div className="lg:col-span-2">
              <div className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
                {t('app.hr.readiness.missing', { defaultValue: 'Missing / affected' })}
              </div>
              <ul className="mt-2 flex flex-wrap gap-2">
                {primary.missingItems.map((item) => (
                  <li
                    key={item}
                    className="rounded-full border border-current/15 bg-white/70 px-2.5 py-1 text-xs font-medium"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="mt-4 text-sm font-medium">
          {summary.readyNextStep
            ? t('app.hr.readiness.ready_next', {
                defaultValue: 'Next step: {step}',
                values: { step: summary.readyNextStep },
              })
            : t('app.hr.readiness.ready_hint', {
                defaultValue: 'No document blockers detected. Employment readiness looks clear from current packs.',
              })}
        </p>
      )}
    </section>
  )
}
