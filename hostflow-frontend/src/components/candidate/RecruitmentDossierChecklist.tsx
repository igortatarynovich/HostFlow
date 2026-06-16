import clsx from 'clsx'
import { useMemo } from 'react'
import type { RecruitmentPackageBlock, RecruitmentPackageReadiness } from '../../api/candidates'
import { useI18n } from '../../i18n'
import {
  RECRUITMENT_DOSSIER_BLOCKS,
  recruitmentBlockStatuses,
  type RecruitmentBlockStatus,
} from '../hr/recruitmentDossierBlocks'
import {
  pruneConfirmedRecruitmentBlocks,
  recruitmentBlocksPendingConfirm,
  recruitmentPackageHandoffReady,
} from '../hr/recruitmentDossierConfirm'

type Props = {
  candidateId?: string
  pkg: RecruitmentPackageReadiness | null
  pkgLoading?: boolean
  confirmedBlocks: string[]
  onConfirmBlock?: (blockKey: string) => void | Promise<void>
  confirmBusy?: boolean
  canConfirm?: boolean
  missing: string[]
  problematic: string[]
  contactsReady?: boolean
  experienceReady?: boolean
  className?: string
}

function statusLabel(t: ReturnType<typeof useI18n>['t'], status: RecruitmentBlockStatus): string {
  switch (status) {
    case 'ready':
      return t('app.candidate_card.dossier_checklist.ready', { defaultValue: 'Ready' })
    case 'missing':
      return t('app.candidate_card.dossier_checklist.missing', { defaultValue: 'Missing' })
    case 'issue':
      return t('app.candidate_card.dossier_checklist.issue', { defaultValue: 'Needs review' })
    case 'data':
      return t('app.candidate_card.dossier_checklist.data', { defaultValue: 'Check fields' })
    default:
      return t('app.candidate_card.dossier_checklist.optional', { defaultValue: 'Optional' })
  }
}

function statusClass(status: RecruitmentBlockStatus): string {
  switch (status) {
    case 'ready':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'missing':
      return 'border-amber-200 bg-amber-50 text-amber-950'
    case 'issue':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'data':
      return 'border-slate-200 bg-slate-50 text-slate-800'
    default:
      return 'border-slate-200 bg-white text-slate-600'
  }
}

function mapApiStatus(raw: string): RecruitmentBlockStatus {
  const s = String(raw || '').toLowerCase()
  if (s === 'ready') return 'ready'
  if (s === 'missing') return 'missing'
  if (s === 'issue') return 'issue'
  if (s === 'data') return 'data'
  return 'optional'
}

function blockDetail(
  block: RecruitmentPackageBlock | undefined,
  status: RecruitmentBlockStatus,
): string | null {
  if (!block) return null
  if (status === 'data' && block.missing_fields?.length) {
    return block.missing_fields.map((f) => f.label || f.field_code).join(', ')
  }
  if ((status === 'missing' || status === 'issue') && block.missing_doc_types?.length) {
    return block.missing_doc_types.join(', ')
  }
  return null
}

export default function RecruitmentDossierChecklist({
  candidateId: _candidateId,
  pkg,
  pkgLoading = false,
  confirmedBlocks,
  onConfirmBlock,
  confirmBusy = false,
  canConfirm = true,
  missing,
  problematic,
  contactsReady,
  experienceReady,
  className,
}: Props) {
  const { t } = useI18n()
  void _candidateId

  const apiBlockByKey = useMemo(() => {
    const map = new Map<string, RecruitmentPackageBlock>()
    for (const b of pkg?.blocks || []) {
      const key = String(b.document_key || b.label || '').trim()
      if (key) map.set(key, b)
    }
    return map
  }, [pkg?.blocks])

  const rows = useMemo(() => {
    if (pkg?.blocks?.length) {
      return pkg.blocks.map((b: RecruitmentPackageBlock) => ({
        key: b.document_key || b.label,
        label: b.label || b.document_key,
        status: mapApiStatus(b.status),
        block: b,
      }))
    }
    const base = recruitmentBlockStatuses(RECRUITMENT_DOSSIER_BLOCKS, missing, problematic)
    return base.map(({ block, status }) => {
      if (block.key === 'Contacts & address' && contactsReady !== undefined) {
        return {
          key: block.key,
          label: block.key,
          status: contactsReady ? ('ready' as const) : ('data' as const),
          block: undefined,
        }
      }
      if (block.key === 'Work experience' && experienceReady !== undefined && status !== 'issue') {
        if (experienceReady) return { key: block.key, label: block.key, status: 'ready' as const, block: undefined }
        if (!missing.some((m) => block.docTypes.includes(m))) {
          return { key: block.key, label: block.key, status: 'data' as const, block: undefined }
        }
      }
      return { key: block.key, label: block.key, status, block: undefined }
    })
  }, [pkg, contactsReady, experienceReady, missing, problematic])

  const prunedConfirmed = useMemo(
    () => pruneConfirmedRecruitmentBlocks(confirmedBlocks, rows),
    [confirmedBlocks, rows],
  )
  const confirmedSet = useMemo(() => new Set(prunedConfirmed), [prunedConfirmed])
  const pendingConfirm = useMemo(
    () => recruitmentBlocksPendingConfirm(rows, confirmedSet),
    [rows, confirmedSet],
  )
  const pending = rows.filter((r) => r.status === 'missing' || r.status === 'issue' || r.status === 'data').length
  const readyForHandoff = recruitmentPackageHandoffReady({
    pkgReady: pkg?.ready,
    pendingConfirmCount: pendingConfirm.length,
  })

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.dossier_checklist.badge', { defaultValue: 'Recruitment package' })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t('app.candidate_card.dossier_checklist.hint', {
              defaultValue: 'Same logical blocks as HR dossier — verify each block, then hand off.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full px-2.5 py-1 text-xs font-semibold',
            readyForHandoff ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900',
          )}
        >
          {pkgLoading
            ? t('common.loading')
            : readyForHandoff
              ? t('app.candidate_card.dossier_checklist.complete', { defaultValue: 'Ready for handoff' })
              : t('app.candidate_card.dossier_checklist.pending', {
                  defaultValue: '{count} open',
                  values: { count: pending + pendingConfirm.length },
                })}
        </span>
      </div>
      {pkg?.missing_data_fields?.length ? (
        <p className="mt-2 text-xs text-amber-900">
          {t('app.candidate_card.dossier_checklist.missing_data', {
            defaultValue: 'Missing data: {list}',
            values: {
              list: pkg.missing_data_fields.map((f) => f.label || f.field_code).join(', '),
            },
          })}
        </p>
      ) : null}
      {pendingConfirm.length > 0 ? (
        <p className="mt-2 text-xs text-amber-900">
          {t('app.candidate_card.dossier_checklist.pending_confirm', {
            defaultValue: 'Confirm reviewed blocks: {list}',
            values: { list: pendingConfirm.join(', ') },
          })}
        </p>
      ) : null}
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {rows.map(({ key, label, status, block }) => {
          const apiBlock = block || apiBlockByKey.get(String(key))
          const detail = blockDetail(apiBlock, status)
          const isConfirmed = confirmedSet.has(String(key))
          const showConfirm =
            canConfirm &&
            onConfirmBlock &&
            status === 'ready' &&
            !isConfirmed
          return (
            <li
              key={key}
              className={clsx(
                'flex flex-col gap-2 rounded-lg border px-3 py-2 text-sm',
                statusClass(status),
                isConfirmed && status === 'ready' && 'ring-1 ring-emerald-300',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{label}</span>
                <span className="text-xs">
                  {isConfirmed && status === 'ready'
                    ? t('app.candidate_card.dossier_checklist.confirmed', { defaultValue: 'Confirmed' })
                    : statusLabel(t, status)}
                </span>
              </div>
              {detail ? <p className="text-xs opacity-90">{detail}</p> : null}
              {showConfirm ? (
                <button
                  type="button"
                  className="btn-secondary btn-xs self-start"
                  disabled={confirmBusy}
                  onClick={() => void onConfirmBlock(String(key))}
                >
                  {t('app.candidate_card.dossier_checklist.confirm_block', { defaultValue: 'Confirm reviewed' })}
                </button>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export { recruitmentPackageHandoffReady, recruitmentBlocksPendingConfirm }
