import type { ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'

type Props = {
  stepNumber: number
  stepLabel: string
  documentLabel: string
  /** When set, replaces default "Step N: Verify …" heading. */
  stepHeadline?: string
  /** Legacy badge; ignored when `statusBadge` is set. */
  documentStatusLabel?: string
  documentStatusTone?: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  /** Preferred: shared DocumentStatus from surfaces. */
  statusBadge?: ReactNode
  verifiedCount: number
  totalCount: number
  nextDocumentLabel?: string | null
  documentViewer: ReactNode
  dataPanel: ReactNode
  footer: ReactNode
  /** Optional compact identity strip below progress (employment setup hint). */
  identityStrip?: ReactNode
}

export default function HrVerificationStepShell({
  stepNumber,
  stepLabel,
  documentLabel,
  stepHeadline,
  documentStatusLabel,
  documentStatusTone = 'neutral',
  statusBadge,
  verifiedCount,
  totalCount,
  nextDocumentLabel,
  documentViewer,
  dataPanel,
  footer,
  identityStrip,
}: Props) {
  const { t } = useI18n()
  const pct = totalCount > 0 ? Math.round((verifiedCount / totalCount) * 100) : 0

  const toneClass =
    documentStatusTone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
      : documentStatusTone === 'danger'
        ? 'border-rose-200 bg-rose-50 text-rose-900'
        : documentStatusTone === 'warning'
          ? 'border-amber-200 bg-amber-50 text-amber-900'
          : documentStatusTone === 'info'
            ? 'border-sky-200 bg-sky-50 text-sky-900'
            : 'border-slate-200 bg-slate-50 text-slate-700'

  return (
    <section id="hr-document-verification" className="scroll-mt-24">
      <div className="flex flex-col overflow-hidden rounded-xl border border-brand-200 bg-white shadow-md">
        <header className="sticky top-0 z-20 border-b border-brand-100 bg-brand-50/90 px-4 py-4 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.hr.verify_shell.phase', { defaultValue: 'Document verification' })}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">
            {stepHeadline ??
              t('app.hr.verify_shell.step_verify', {
                defaultValue: 'Step {step}: Verify {document}',
                values: { step: stepNumber, document: documentLabel },
              })}
          </h2>
          <p className="text-sm text-slate-600">{stepLabel}</p>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <div className="min-w-[10rem] flex-1">
              <div className="mb-1 flex justify-between text-xs font-medium text-slate-700">
                <span>
                  {t('app.hr.verify_shell.progress', {
                    defaultValue: '{verified} of {total} required documents confirmed',
                    values: { verified: verifiedCount, total: totalCount },
                  })}
                </span>
                <span>{pct}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-brand-500 transition-all duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
            {statusBadge ?? (
              <span
                className={clsx(
                  'inline-flex shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold',
                  toneClass,
                )}
              >
                {documentStatusLabel ?? ''}
              </span>
            )}
          </div>

          {nextDocumentLabel ? (
            <p className="mt-2 text-sm text-slate-600">
              {t('app.hr.verify_shell.up_next', {
                defaultValue: 'Up next: {document}',
                values: { document: nextDocumentLabel },
              })}
            </p>
          ) : verifiedCount >= totalCount && totalCount > 0 ? (
            <p className="mt-2 text-sm font-medium text-emerald-800">
              {t('app.hr.verify_shell.all_required_done', {
                defaultValue: 'All required documents are confirmed.',
              })}
            </p>
          ) : null}

          {identityStrip ? <div className="mt-3">{identityStrip}</div> : null}
        </header>

        <div className="grid min-h-[26rem] flex-1 grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-slate-100">
          <div className="flex flex-col bg-slate-50/60 p-4">{documentViewer}</div>
          <div className="flex flex-col p-4">{dataPanel}</div>
        </div>

        <footer className="sticky bottom-0 z-20 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.06)] backdrop-blur-sm">
          {footer}
        </footer>
      </div>
    </section>
  )
}
