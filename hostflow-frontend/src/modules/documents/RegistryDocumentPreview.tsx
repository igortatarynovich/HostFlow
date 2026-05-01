import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { patchDocument } from '../../api/documents'
import type { Document } from '../../api/types/document'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { DocumentWorkflow } from './components/DocumentWorkflow'
import { DocumentLastCheck } from './components/DocumentLastCheck'
import { DocumentReminders } from './components/DocumentReminders'
import { isProcessDocument, isWorkflowStepDone, withStepCompleted } from './workflowUtils'

type RegistryDocumentPreviewProps = {
  doc: Document
  nowTs: number
  meId: string | null
  onPatched: (next: Document) => void
  planLimitError?: (err: unknown, fallback: string) => boolean
  translateStatus: (status: string) => string
  translateProcess: (value: string | null | undefined) => string | null
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const ts = Date.parse(value)
  if (Number.isNaN(ts)) return value
  return new Date(ts).toLocaleString()
}

function getLatestUploadInfo(doc: Document): { by: string | null; at: string | null } {
  const files = Array.isArray(doc.files) ? doc.files : []
  let bestAt = -1
  let bestBy: string | null = null
  let bestAtRaw: string | null = null
  files.forEach((f) => {
    const raw = f?.uploaded_at || null
    const ts = raw ? Date.parse(raw) : Number.NaN
    if (!Number.isNaN(ts) && ts >= bestAt) {
      bestAt = ts
      bestBy = (f?.uploaded_by || '').trim() || null
      bestAtRaw = raw
    } else if (bestAt < 0 && !bestBy) {
      bestBy = (f?.uploaded_by || '').trim() || null
    }
  })
  return { by: bestBy, at: bestAtRaw }
}

function documentDeadlineParts(doc: Document, nowTs: number): { text: string; overdue: boolean } {
  const raw = doc.expires_at || doc.expire_date
  if (!raw) return { text: '—', overdue: false }
  const ts = Date.parse(raw)
  const text = formatDate(raw)
  if (Number.isNaN(ts)) return { text, overdue: false }
  const overdue = ts < nowTs || doc.status === 'expired'
  return { text, overdue }
}

const STATUS_TONES: Record<string, string> = {
  missing: 'bg-slate-100 text-slate-700',
  requested: 'bg-amber-50 text-amber-800',
  in_progress: 'bg-sky-50 text-sky-800',
  received: 'bg-emerald-50 text-emerald-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-rose-100 text-rose-800',
  expired: 'bg-rose-50 text-rose-800',
}

function StatusChip({ label, tone }: { label: string; tone: string }) {
  const toneClass = STATUS_TONES[tone] ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex items-center rounded-md px-3 py-1 text-xs font-medium ${toneClass}`}>
      {label}
    </span>
  )
}

function documentResponsibleLabel(doc: Document): string {
  const n = doc.responsible_name?.trim()
  if (n) return n
  return '—'
}

export function RegistryDocumentPreview({
  doc,
  nowTs,
  meId,
  onPatched,
  planLimitError,
  translateStatus,
  translateProcess,
}: RegistryDocumentPreviewProps) {
  const { t } = useI18n()
  const [wfSaving, setWfSaving] = useState(false)
  const [wfError, setWfError] = useState<string | null>(null)

  const deadline = documentDeadlineParts(doc, nowTs)
  const cid = doc.candidate_id
  const candidateHref =
    cid != null && String(cid).length > 0 ? `${CRM_APP_PATHS.candidates}/${String(cid)}/documents` : null
  const ownerLabel =
    (doc.meta as any)?.candidate_name ||
    (doc.meta as any)?.company_name ||
    (doc as any).extra?.owner_name ||
    doc.owner_id ||
    t('common.labels.not_available')
  const latestUpload = getLatestUploadInfo(doc)
  const lastCheck = doc.last_check ?? null
  const showWf = isProcessDocument(doc) && doc.workflow && Array.isArray(doc.workflow.steps) && doc.workflow.steps.length > 0
  const canWf = Boolean(meId)

  const runPatch = useCallback(
    async (nextWorkflow: NonNullable<typeof doc.workflow>) => {
      setWfSaving(true)
      setWfError(null)
      try {
        const next = await patchDocument(String(doc.id), { workflow: nextWorkflow })
        onPatched(next as Document)
      } catch (e: any) {
        if (planLimitError?.(e, t('admin.documents.registry.workflow_error', { defaultValue: 'Update failed' }))) {
          return
        }
        const detail = e?.response?.data?.detail
        setWfError(typeof detail === 'string' ? detail : e?.message || String(e))
      } finally {
        setWfSaving(false)
      }
    },
    [doc.id, onPatched, planLimitError, t],
  )

  const onCompleteStep = useCallback(
    async (_d: Document, stepCode: string) => {
      if (!doc.workflow) return
      const merged = withStepCompleted(doc.workflow, stepCode, meId)
      if (merged) await runPatch(merged)
    },
    [doc.workflow, meId, runPatch],
  )

  const onStartWorkflow = useCallback(
    async (d: Document) => {
      if (!d.workflow?.steps?.length) return
      const first = d.workflow.steps[0]
      if (!first || isWorkflowStepDone(first)) return
      const iso = new Date().toISOString()
      const w = {
        ...d.workflow,
        steps: d.workflow.steps.map((s, i) =>
          i === 0 ? { ...s, status: 'in_progress' as const, ordered_at: iso, started_at: iso } : s,
        ),
      }
      await runPatch(w)
    },
    [runPatch],
  )

  return (
    <div className="space-y-3 text-sm text-slate-700">
      {wfError ? (
        <p className="rounded border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800">{wfError}</p>
      ) : null}
      <div>
        <p className="text-lg font-semibold leading-snug text-slate-900">
          {doc.custom_name || doc.title || doc.doc_type || t('common.labels.not_available')}
        </p>
        <p className="text-xs text-slate-500">{doc.doc_type}</p>
        {isProcessDocument(doc) ? (
          <p className="mt-1 text-xs text-teal-800">
            {t('admin.documents.registry.preview.process_badge', { defaultValue: 'Process document' })}
            {doc.process_type ? ` · ${translateProcess(doc.process_type) || doc.process_type}` : ''}
          </p>
        ) : null}
        {Array.isArray(doc.reminders) && doc.reminders.length > 0 ? (
          <div className="mt-2">
            <DocumentReminders reminders={doc.reminders} />
          </div>
        ) : null}
      </div>
      {showWf ? (
        <div className={wfSaving ? 'pointer-events-none opacity-70' : ''}>
          <DocumentWorkflow
            doc={doc}
            workflow={doc.workflow ?? undefined}
            translateStatus={translateStatus as any}
            translateProcess={translateProcess as any}
            canManageDocuments={canWf}
            canModify={canWf && !wfSaving}
            onStartWorkflow={onStartWorkflow}
            onCompleteStep={onCompleteStep}
          />
        </div>
      ) : null}
      <dl className="space-y-2 border-t border-slate-100 pt-3">
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.table.owner')}</dt>
          <dd className="max-w-[60%] text-right font-medium text-slate-900">{ownerLabel}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.table.responsible')}</dt>
          <dd className="max-w-[60%] text-right font-medium text-slate-900">{documentResponsibleLabel(doc)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">
            {t('admin.documents.registry.preview.process_owner', { defaultValue: 'Process owner' })}
          </dt>
          <dd className="max-w-[60%] text-right text-slate-800">
            {(doc as any).owner_id && (doc as any).owner_id === meId
              ? t('common.pronouns.you', { defaultValue: 'You' })
              : (doc as any).owner_id || '—'}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.table.deadline')}</dt>
          <dd
            className={
              deadline.overdue ? 'text-right font-medium text-amber-800' : 'text-right text-slate-900'
            }
          >
            {deadline.text}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.table.updated')}</dt>
          <dd className="text-right text-slate-800">{formatDate(doc.updated_at || doc.created_at)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.preview.version', { defaultValue: 'Version' })}</dt>
          <dd className="text-right text-slate-800">{(doc as any).version ?? '—'}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">
            {t('admin.documents.registry.preview.last_upload_by', { defaultValue: 'Last upload by' })}
          </dt>
          <dd className="max-w-[60%] text-right text-slate-800">{latestUpload.by ?? '—'}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">
            {t('admin.documents.registry.preview.last_upload_at', { defaultValue: 'Last upload at' })}
          </dt>
          <dd className="text-right text-slate-800">{latestUpload.at ? formatDate(latestUpload.at) : '—'}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="shrink-0 text-slate-500">
            {t('admin.documents.registry.preview.last_check', { defaultValue: 'Last review decision' })}
          </dt>
          <dd className="min-w-0 max-w-[65%] text-right text-slate-800">
            {lastCheck ? (
              <DocumentLastCheck check={lastCheck} variant="inline" className="justify-end" />
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">{t('admin.documents.registry.preview.files')}</dt>
          <dd className="text-right font-medium text-slate-900">
            {doc.has_files ? t('common.yes') : t('common.no')}
          </dd>
        </div>
      </dl>
      <div className="border-t border-slate-100 pt-3">
        <StatusChip
          tone={String(doc.status || 'missing')}
          label={t(`admin.documents.status_labels.${doc.status}`, { defaultValue: String(doc.status) })}
        />
      </div>
      {candidateHref ? (
        <Link className="btn-primary inline-flex w-full justify-center no-underline" to={candidateHref}>
          {t('admin.documents.registry.preview.open_candidate')}
        </Link>
      ) : null}
    </div>
  )
}
