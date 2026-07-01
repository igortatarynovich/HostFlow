import clsx from 'clsx'
import { useMemo, type ReactNode } from 'react'
import type { TransferReadinessReport as TransferReadinessReportData } from '../../api/candidates'
import { useI18n } from '../../i18n'
import { formatTransferList, groupBlockingReasonsByLayer } from './transferReadinessDisplay'

type Props = {
  report: TransferReadinessReportData | null
  loading?: boolean
  onConfirmBlock?: (blockKey: string, fingerprint?: string) => void | Promise<void>
  confirmBusy?: boolean
  canConfirm?: boolean
  confirmedBlocks?: string[]
  className?: string
}

function DecisionBadge({ label, allowed }: { label: string; allowed: boolean | undefined }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
        allowed ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-950',
      )}
    >
      {label}: {allowed ? '✓' : '✗'}
    </span>
  )
}

function Section({ title, children, empty }: { title: string; children: ReactNode; empty?: boolean }) {
  if (empty) return null
  return (
    <div className="border-t border-slate-100 pt-3 first:border-t-0 first:pt-0">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-2 text-sm text-slate-800">{children}</div>
    </div>
  )
}

function layerLabel(t: ReturnType<typeof useI18n>['t'], layer: string): string {
  return t(`app.candidate_card.transfer_readiness.layer.${layer}`, {
    defaultValue: layer.replace(/_/g, ' '),
  })
}

function destinationLabel(t: ReturnType<typeof useI18n>['t'], code: string): string {
  return t(`app.candidate_card.transfer_readiness.destination.${code}`, {
    defaultValue: code,
  })
}

export default function TransferReadinessReport({
  report,
  loading = false,
  onConfirmBlock,
  confirmBusy = false,
  canConfirm = true,
  confirmedBlocks = [],
  className,
}: Props) {
  const { t } = useI18n()

  const confirmedSet = useMemo(() => new Set(confirmedBlocks), [confirmedBlocks])
  const pendingConfirmations = useMemo(
    () => (report?.required_confirmations || []).filter((item) => !confirmedSet.has(item.block_key)),
    [confirmedSet, report?.required_confirmations],
  )

  const groupedReasons = groupBlockingReasonsByLayer(report?.blocking_reasons)
  const groupedWarnings = groupBlockingReasonsByLayer(report?.warnings)

  return (
    <section
      className={clsx('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}
      id="section-transfer-readiness"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.transfer_readiness.badge', { defaultValue: 'Transfer readiness' })}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.candidate_card.transfer_readiness.hint', {
              defaultValue: 'Decision from Transfer Policy — no local checklist rules.',
            })}
          </p>
        </div>
        {report?.policy_version ? (
          <span className="text-xs text-slate-400">{report.policy_version}</span>
        ) : null}
      </div>

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">{t('common.loading')}</p>
      ) : !report ? (
        <p className="mt-4 text-sm text-amber-900">
          {t('app.candidate_card.transfer_readiness.load_failed', {
            defaultValue: 'Could not load transfer readiness. Refresh the page.',
          })}
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          <Section title={t('app.candidate_card.transfer_readiness.final_decision', { defaultValue: 'Final decision' })}>
            <div className="flex flex-wrap gap-2">
              <DecisionBadge
                label={t('app.candidate_card.transfer_readiness.transfer_allowed', {
                  defaultValue: 'Stage → ready_for_handoff',
                })}
                allowed={report.transfer_allowed}
              />
              <DecisionBadge
                label={t('app.candidate_card.transfer_readiness.handoff_create_allowed', {
                  defaultValue: 'Create handoff',
                })}
                allowed={report.handoff_create_allowed}
              />
            </div>
          </Section>

          <Section
            title={t('app.candidate_card.transfer_readiness.blocking_reasons', { defaultValue: 'Blocking reasons' })}
            empty={groupedReasons.length === 0}
          >
            <ul className="space-y-3">
              {groupedReasons.map(({ layer, items }) => (
                <li key={layer}>
                  <p className="text-xs font-medium text-slate-500">{layerLabel(t, layer)}</p>
                  <ul className="mt-1 space-y-1">
                    {items.map((reason, idx) => (
                      <li
                        key={`${layer}-${reason.code}-${idx}`}
                        className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-sm text-amber-950"
                      >
                        <span className="font-medium">{reason.message}</span>
                        <span className="ml-2 text-xs text-amber-800/80">({reason.code})</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </Section>

          {groupedWarnings.length > 0 ? (
            <Section title={t('app.candidate_card.transfer_readiness.warnings', { defaultValue: 'Warnings' })}>
              <ul className="space-y-2">
                {groupedWarnings.map(({ layer, items }) => (
                  <li key={`warn-${layer}`}>
                    <p className="text-xs font-medium text-slate-500">{layerLabel(t, layer)}</p>
                    <ul className="mt-1 space-y-1">
                      {items.map((reason, idx) => (
                        <li key={`warn-${layer}-${idx}`} className="text-sm text-slate-700">
                          {reason.message}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          <Section
            title={t('app.candidate_card.transfer_readiness.required_documents', {
              defaultValue: 'Required documents',
            })}
            empty={
              !report.required_documents?.length &&
              !report.missing_documents?.length &&
              !report.pending_verification_documents?.length
            }
          >
            <dl className="grid gap-2 text-sm">
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.transfer_readiness.required_list', { defaultValue: 'Required' })}
                </dt>
                <dd>{formatTransferList(report.required_documents)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.transfer_readiness.missing_list', { defaultValue: 'Missing' })}
                </dt>
                <dd className={report.missing_documents?.length ? 'text-amber-900' : undefined}>
                  {formatTransferList(report.missing_documents)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">
                  {t('app.candidate_card.transfer_readiness.pending_verification_list', {
                    defaultValue: 'Pending verification',
                  })}
                </dt>
                <dd className={report.pending_verification_documents?.length ? 'text-amber-900' : undefined}>
                  {formatTransferList(report.pending_verification_documents)}
                </dd>
              </div>
            </dl>
          </Section>

          <Section
            title={t('app.candidate_card.transfer_readiness.required_data', { defaultValue: 'Required data' })}
            empty={!report.missing_data_fields?.length}
          >
            <p>{formatTransferList(report.missing_data_fields?.map((f) => f.label || f.field_code))}</p>
          </Section>

          <Section
            title={t('app.candidate_card.transfer_readiness.confirmations', { defaultValue: 'Confirmations' })}
            empty={pendingConfirmations.length === 0}
          >
            <ul className="space-y-2">
              {pendingConfirmations.map((item) => (
                <li
                  key={item.block_key}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 px-2 py-1.5"
                >
                  <span>
                    {item.block_key}
                    <span className="ml-2 text-xs text-slate-500">({item.confirmed_by_role})</span>
                  </span>
                  {canConfirm && onConfirmBlock ? (
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      disabled={confirmBusy}
                      onClick={() => void onConfirmBlock(item.block_key)}
                    >
                      {t('app.candidate_card.dossier_checklist.confirm_block', {
                        defaultValue: 'Confirm reviewed',
                      })}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </Section>

          <Section title={t('app.candidate_card.transfer_readiness.destinations', { defaultValue: 'Destinations' })}>
            <p>
              {report.destinations_allowed?.length
                ? report.destinations_allowed.map((d) => destinationLabel(t, d)).join(', ')
                : t('app.candidate_card.transfer_readiness.no_destinations', { defaultValue: 'None enabled' })}
            </p>
          </Section>

          <Section
            title={t('app.candidate_card.transfer_readiness.overrides', { defaultValue: 'Overrides' })}
            empty={!report.approved_overrides?.length}
          >
            <p>{formatTransferList(report.approved_overrides)}</p>
          </Section>
        </div>
      )}
    </section>
  )
}
