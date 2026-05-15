import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { WorkforceEmployeeDocumentRow, WorkforceEmployeeOperationalProfile } from '../../api/workforce'
import { formatShortDateIso, humanizeToken } from './hrEmployeeUiFormat'

function isHrDebugSnapshot(): boolean {
  try {
    return Boolean(import.meta.env.DEV && typeof localStorage !== 'undefined' && localStorage.getItem('hostflow_hr_debug') === '1')
  } catch {
    return false
  }
}

function pickString(obj: Record<string, unknown>, keys: string[]): string | null {
  for (const k of keys) {
    const v = obj[k]
    if (typeof v === 'string' && v.trim()) return v.trim()
  }
  return null
}

function pickNotes(snap: Record<string, unknown> | null): string | null {
  if (!snap) return null
  return pickString(snap, ['notes', 'recruiter_notes', 'internal_notes', 'handoff_notes', 'summary', 'comment'])
}

function pickDocListFromSnapshot(snap: Record<string, unknown> | null): Array<{ title: string; subtitle?: string }> {
  if (!snap) return []
  const keys = ['documents_at_handoff', 'documents', 'handoff_documents', 'captured_documents', 'dossier_documents']
  for (const k of keys) {
    const v = snap[k]
    if (!Array.isArray(v)) continue
    const out: Array<{ title: string; subtitle?: string }> = []
    for (const item of v) {
      if (!item || typeof item !== 'object') continue
      const o = item as Record<string, unknown>
      const title =
        pickString(o, ['title', 'name', 'document_title', 'document_type', 'type', 'label']) ||
        (typeof o.id === 'string' ? o.id.slice(0, 8) : null) ||
        '—'
      const subtitle = pickString(o, ['status', 'document_type', 'category', 'doc_type']) || undefined
      out.push({ title, subtitle })
    }
    if (out.length) return out
  }
  return []
}

function pickDocListFromLinked(
  rows: WorkforceEmployeeDocumentRow[] | undefined,
  limit: number,
): Array<{ title: string; subtitle?: string }> {
  if (!rows?.length) return []
  return rows.slice(0, limit).map((r) => ({
    title: (r.document.title || r.document.doc_type || '—').trim(),
    subtitle: (r.document.status || '').trim() || undefined,
  }))
}

type Props = {
  profile: WorkforceEmployeeOperationalProfile
  linkedDocRows?: WorkforceEmployeeDocumentRow[] | null
}

/**
 * Readable recruitment → HR handoff (replaces raw hire_snapshot JSON on the employee profile).
 */
export default function HrRecruitmentTransferSummary({ profile, linkedDocRows }: Props) {
  const { t } = useI18n()
  const snap = profile.hire_snapshot && typeof profile.hire_snapshot === 'object' ? profile.hire_snapshot : null
  const rs = profile.recruiter_summary
  const tr = profile.transfer

  const snapRecord = snap as Record<string, unknown> | null
  const candidateName =
    [rs.first_name, rs.last_name].filter(Boolean).join(' ').trim() ||
    pickString(snapRecord || {}, ['first_name', 'last_name', 'full_name', 'candidate_name']) ||
    ''

  const vacancyTitle =
    pickString(snapRecord || {}, ['vacancy_title', 'job_title', 'position_title', 'role_title']) || null

  const capturedAt = rs.captured_at || (snapRecord ? pickString(snapRecord, ['captured_at']) : null)
  const notes = pickNotes(snapRecord)
  const snapDocs = pickDocListFromSnapshot(snapRecord)
  const linkedDocs = pickDocListFromLinked(linkedDocRows ?? undefined, 12)
  const docLines = snapDocs.length > 0 ? snapDocs : linkedDocs

  const vacancyId = tr.vacancy_id || (snapRecord ? pickString(snapRecord, ['vacancy_id']) : null)
  const candidateId = tr.candidate_id || rs.candidate_id || (snapRecord ? pickString(snapRecord, ['candidate_id']) : null)

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.employee_operational.transfer_card_title', { defaultValue: 'Handoff' })}
          </div>
          <dl className="mt-2 space-y-2 text-sm text-slate-800">
            <div>
              <dt className="text-xs text-slate-500">
                {t('app.hr.employee_operational.handoff_when', { defaultValue: 'Handoff date' })}
              </dt>
              <dd className="font-medium">{formatShortDateIso(tr.handoff_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.handoff_by', { defaultValue: 'Handed off by' })}</dt>
              <dd className="font-medium">{tr.handoff_by_name || tr.handoff_by_user_id || '—'}</dd>
            </div>
            {tr.handoff_id ? (
              <div>
                <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.handoff_ref', { defaultValue: 'Internal reference' })}</dt>
                <dd className="font-mono text-xs text-slate-600 break-all">{tr.handoff_id}</dd>
              </div>
            ) : null}
          </dl>
        </div>

        <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-indigo-800">
            {t('app.hr.employee_operational.candidate_card_title', { defaultValue: 'Candidate at hire' })}
          </div>
          <dl className="mt-2 space-y-2 text-sm text-slate-900">
            <div>
              <dt className="text-xs text-slate-600">{t('app.hr.employee_operational.name', { defaultValue: 'Name' })}</dt>
              <dd className="font-medium">{candidateName || '—'}</dd>
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
              {rs.stage ? (
                <span>
                  <span className="text-slate-500">{t('app.hr.employee_operational.pipeline_stage', { defaultValue: 'Stage' })}: </span>
                  <span className="font-medium">{humanizeToken(rs.stage)}</span>
                </span>
              ) : null}
              {rs.status ? (
                <span>
                  <span className="text-slate-500">{t('app.hr.employee_operational.recruitment_status', { defaultValue: 'Status' })}: </span>
                  <span className="font-medium">{humanizeToken(rs.status)}</span>
                </span>
              ) : null}
            </div>
            <div>
              <dt className="text-xs text-slate-600">Email</dt>
              <dd className="break-all">{rs.email || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-600">Phone</dt>
              <dd>{rs.phone || '—'}</dd>
            </div>
            {capturedAt ? (
              <div>
                <dt className="text-xs text-slate-600">{t('app.hr.employee_operational.snapshot_captured', { defaultValue: 'Snapshot captured' })}</dt>
                <dd>{formatShortDateIso(capturedAt)}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.employee_operational.vacancy_card_title', { defaultValue: 'Vacancy' })}
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm">
          <div>
            <div className="font-medium text-slate-900">{vacancyTitle || '—'}</div>
            {vacancyId ? <div className="font-mono text-xs text-slate-500 mt-0.5 break-all">{vacancyId}</div> : null}
          </div>
          {vacancyId ? (
            <Link
              to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(vacancyId)}`}
              className="btn-secondary btn-sm shrink-0"
              target="_blank"
              rel="noopener noreferrer"
            >
              {t('app.hr.employee_operational.open_vacancy', { defaultValue: 'Open vacancy' })}
            </Link>
          ) : null}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.employee_operational.documents_at_handoff', { defaultValue: 'Documents at hire' })}
        </div>
        {docLines.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            {t('app.hr.employee_operational.documents_at_handoff_empty', {
              defaultValue: 'No hire-time document list in the snapshot — see linked dossier below when available.',
            })}
          </p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-100">
            {docLines.map((d, i) => (
              <li key={`${d.title}-${i}`} className="flex flex-wrap items-baseline justify-between gap-2 py-2 text-sm">
                <span className="font-medium text-slate-900">{d.title}</span>
                {d.subtitle ? <span className="text-xs text-slate-500">{humanizeToken(d.subtitle)}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.employee_operational.notes_at_handoff', { defaultValue: 'Notes' })}
        </div>
        {notes ? (
          <p className="mt-2 text-sm text-slate-800 whitespace-pre-wrap">{notes}</p>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            {t('app.hr.employee_operational.notes_empty', { defaultValue: 'No notes were stored on the hire snapshot.' })}
          </p>
        )}
      </div>

      {candidateId ? (
        <p className="text-sm">
          <Link
            to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`}
            className="text-indigo-700 underline-offset-2 hover:underline font-medium"
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('app.hr.employee_operational.open_recruitment_record', {
              defaultValue: 'Open recruitment record (read-only context)',
            })}
          </Link>
        </p>
      ) : null}

      {isHrDebugSnapshot() && snapRecord && Object.keys(snapRecord).length > 0 ? (
        <details className="rounded-lg border border-dashed border-amber-300 bg-amber-50/50 text-xs">
          <summary className="cursor-pointer select-none px-3 py-2 font-semibold text-amber-950">
            {t('app.hr.employee_operational.debug_snapshot', { defaultValue: 'Raw hire snapshot (debug)' })}
          </summary>
          <pre className="max-h-56 overflow-auto border-t border-amber-100 px-3 py-2 text-[11px] leading-snug text-slate-800">
            {JSON.stringify(snapRecord, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  )
}
