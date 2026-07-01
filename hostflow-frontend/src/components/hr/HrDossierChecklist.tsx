import clsx from 'clsx'
import type { HrReviewDocumentRow } from '../../api/workforce'
import { useI18n } from '../../i18n'
import type { RecruitmentBlockStatus } from './recruitmentDossierBlocks'
import {
  countMissingFieldsOnDocument,
  isDocumentVerified,
} from './hrDocumentVerificationFields'
import { dossierBlockKind, dossierFileRequiredForConfirm } from './dossierBlockKind'

type Props = {
  blocks: HrReviewDocumentRow[]
  onSelectBlock?: (documentKey: string) => void
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

export function hrDossierBlockStatus(doc: HrReviewDocumentRow): RecruitmentBlockStatus {
  if (isDocumentVerified(doc)) return 'ready'
  const raw = String(doc.verification_status || doc.status || '').toLowerCase()
  if (raw === 'needs_correction' || raw === 'rejected') return 'issue'
  if (dossierBlockKind(doc) === 'data_only') return 'data'
  const fileRequired = dossierFileRequiredForConfirm(doc)
  const hasFile = Boolean(doc.document_id || doc.open_url || doc.file_url)
  if (fileRequired && !hasFile) return 'missing'
  if (countMissingFieldsOnDocument(doc) > 0) return 'data'
  return 'data'
}

export function hrDossierBlockAnchorId(documentKey: string): string {
  return `dossier-doc-${documentKey.replace(/[^a-z0-9_-]+/gi, '-')}`
}

export default function HrDossierChecklist({ blocks, onSelectBlock, className }: Props) {
  const { t } = useI18n()

  const rows = blocks.map((doc) => ({
    doc,
    key: doc.document_key,
    label: doc.label || doc.document_key,
    status: hrDossierBlockStatus(doc),
    confirmed: isDocumentVerified(doc),
  }))

  const pending = rows.filter((r) => !r.confirmed).length
  const allConfirmed = rows.length > 0 && pending === 0

  const scrollToBlock = (documentKey: string) => {
    onSelectBlock?.(documentKey)
    const el = document.getElementById(hrDossierBlockAnchorId(documentKey))
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.dossier.checklist_badge', { defaultValue: 'HR verification package' })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t('app.hr.dossier.checklist_hint', {
              defaultValue: 'Same blocks as recruitment — open each section, check fields and documents, then confirm.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full px-2.5 py-1 text-xs font-semibold',
            allConfirmed ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900',
          )}
        >
          {rows.length === 0
            ? t('app.hr.verify_task.no_docs', {
                defaultValue: 'No required documents in the verification plan yet.',
              })
            : allConfirmed
              ? t('app.hr.dossier.checklist_complete', { defaultValue: 'All blocks confirmed' })
              : t('app.candidate_card.dossier_checklist.pending', {
                  defaultValue: '{count} open',
                  values: { count: pending },
                })}
        </span>
      </div>
      {rows.length > 0 ? (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {rows.map(({ key, label, status, confirmed }) => (
            <li key={key}>
              <button
                type="button"
                className={clsx(
                  'flex w-full flex-col gap-2 rounded-lg border px-3 py-2 text-left text-sm transition hover:ring-1 hover:ring-brand-200',
                  statusClass(status),
                  confirmed && 'ring-1 ring-emerald-300',
                )}
                onClick={() => scrollToBlock(String(key))}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{label}</span>
                  <span className="text-xs">
                    {confirmed
                      ? t('app.candidate_card.dossier_checklist.confirmed', { defaultValue: 'Confirmed' })
                      : statusLabel(t, status)}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
