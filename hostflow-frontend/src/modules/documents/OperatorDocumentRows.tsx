import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import type { Document } from '../../api/types'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import { useI18n } from '../../i18n'
import type { OperatorFactsView } from '../candidates/OperatorFactsSurface'
import { documentHasFiles, isSyntheticDocumentId, normalizeDocTypeCode } from './documentUtils'

type TypeLevel = 'required' | 'preferred'

const PRESENCE_STEP: Record<string, string> = {
  code95: 'code95',
  driver_qualification_card: 'code95',
  tachograph_card: 'tachograph',
  tacho_card: 'tachograph',
  karta_tachografu: 'tachograph',
  adr: 'adr',
  adr_certificate: 'adr',
  medical: 'medical',
  medical_certificate: 'medical',
  psych: 'psych',
  psych_tests: 'psych',
  psychological_certificate: 'psych',
}

const PRESENCE_PATCH: Record<string, string> = {
  code95: 'code95_presence',
  tachograph: 'tachograph_presence',
  adr: 'adr_presence',
  medical: 'medical_presence',
  psych: 'psych_presence',
}

const LICENCE_TYPES = new Set(['driver_license', 'driver_license_code95', 'driver_licence'])

function preferredDoc(list: Document[]): Document | undefined {
  const real = list.filter((doc) => !isSyntheticDocumentId(doc.id))
  const pool = real.length ? real : list
  return pool.find((doc) => documentHasFiles(doc)) || pool[0]
}

export function OperatorDocumentRows({
  candidateId,
  docs,
  docTypes,
  typeLevel,
  onlyTypes,
  excludeTypes,
  canManage,
  countries,
  getLabel,
  onUpload,
  uploading,
  onFactsSaved,
  renderOpen,
}: {
  candidateId: string
  docs: Document[]
  docTypes: Array<{ code: string; name?: string | null }>
  typeLevel: Record<string, TypeLevel>
  onlyTypes?: string[]
  excludeTypes?: string[]
  canManage: boolean
  countries?: Array<{ value: string; label: string }>
  getLabel: (code: string, name?: string | null) => string
  onUpload: (doc: Document, file: File) => Promise<void>
  uploading: Record<string, boolean>
  onFactsSaved?: () => void
  renderOpen: (doc: Document) => ReactNode
}) {
  const { t } = useI18n()
  const [facts, setFacts] = useState<OperatorFactsView | null>(null)
  const [localPresence, setLocalPresence] = useState<Record<string, boolean | null>>({})
  const [openCode, setOpenCode] = useState<string | null>(null)
  const yes = t('app.candidate_card.ia.doc_present', { defaultValue: 'Present' })
  const no = t('app.candidate_card.ia.doc_absent', { defaultValue: 'Absent' })

  useEffect(() => {
    let cancelled = false
    void api.get<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`).then((response) => {
      if (!cancelled) setFacts(response.data)
    }).catch(() => {
      if (!cancelled) setFacts(null)
    })
    return () => {
      cancelled = true
    }
  }, [candidateId, docs])

  const only = useMemo(() => (onlyTypes ? new Set(onlyTypes.map(normalizeDocTypeCode)) : null), [onlyTypes])
  const exclude = useMemo(() => new Set((excludeTypes || []).map(normalizeDocTypeCode)), [excludeTypes])

  const rows = useMemo(() => {
    return docTypes.flatMap((type) => {
      const norm = normalizeDocTypeCode(type.code)
      if (only && !only.has(norm)) return []
      if (!only && exclude.has(norm)) return []
      const matches = docs.filter((doc) => normalizeDocTypeCode(doc.type_code || doc.doc_type || '') === norm)
      const doc = preferredDoc(matches)
      if (!doc) return []
      return [{ type, norm, doc }]
    })
  }, [docTypes, docs, exclude, only])

  const step = (key: string) => facts?.steps?.find((item) => item.key === key)
  const patchFacts = async (patch: Record<string, unknown>) => {
    const response = await api.put<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`, patch)
    setFacts(response.data)
    onFactsSaved?.()
  }

  if (!rows.length) return null

  const required = rows.filter((row) => (typeLevel[row.type.code] || 'required') === 'required')
  const preferred = rows.filter((row) => typeLevel[row.type.code] === 'preferred')

  const renderRow = (row: (typeof rows)[number]) => {
    const presenceStep = PRESENCE_STEP[row.norm]
    const storedPresence = presenceStep ? step(presenceStep)?.presence : undefined
    const hasOwner = presenceStep != null
    const hasFile = documentHasFiles(row.doc)
    const presence = hasOwner
      ? (storedPresence === true ? true : storedPresence === false ? false : null)
      : (localPresence[row.norm] ?? (hasFile ? true : null))
    const fileName = row.doc.files?.[0]?.name || ''
    const status = presence === false
      ? no
      : hasFile
        ? [fileName, row.doc.status === 'approved'
          ? t('app.candidate_card.ia.doc_checked', { defaultValue: 'Checked' })
          : t('app.candidate_card.ia.doc_check', { defaultValue: 'Review' })].filter(Boolean).join(' · ')
        : t('app.candidate_card.ia.doc_not_uploaded', { defaultValue: 'Not uploaded' })
    const licence = LICENCE_TYPES.has(row.norm)
    const country = licence ? step('driving_licence')?.issuing_country || '' : ''
    const sharedCode95 = licence && facts?.ce_code95?.evidence_shape === 'shared'
    const setPresence = (next: boolean) => {
      if (!canManage) return
      if (hasOwner && presenceStep) {
        const patchKey = PRESENCE_PATCH[presenceStep]
        if (patchKey) void patchFacts({ [patchKey]: next })
        return
      }
      setLocalPresence((prev) => ({ ...prev, [row.norm]: next }))
    }
    return (
      <div key={row.norm} className="border-b border-slate-100 py-2 last:border-b-0">
        <div className="grid grid-cols-1 items-center gap-2 md:grid-cols-[minmax(0,1.3fr)_auto_minmax(0,1fr)_auto]">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-900">{getLabel(row.type.code, row.type.name)}</span>
            <StatusBadge
              size="sm"
              shape="pill"
              semantic={(typeLevel[row.type.code] || 'required') === 'required' ? 'warning' : 'neutral'}
              label={(typeLevel[row.type.code] || 'required') === 'required'
                ? t('app.candidate_card.ia.required_mark', { defaultValue: 'Required' })
                : t('app.candidate_card.ia.preferred_mark', { defaultValue: 'Preferred' })}
            />
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className={presence === true ? 'btn-primary btn-compact' : 'btn-secondary btn-compact'}
              disabled={!canManage}
              onClick={() => setPresence(true)}
            >
              {yes}
            </button>
            <button
              type="button"
              className={presence === false ? 'btn-primary btn-compact' : 'btn-secondary btn-compact'}
              disabled={!canManage}
              onClick={() => {
                setPresence(false)
                setOpenCode(null)
              }}
            >
              {no}
            </button>
          </div>
          <div className="min-w-0 truncate text-xs text-slate-600">{status}</div>
          <div>
            {presence === true && !hasFile ? (
              <label className="btn-secondary btn-compact cursor-pointer">
                {uploading[row.doc.id]
                  ? t('common.saving')
                  : t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
                <input
                  type="file"
                  className="sr-only"
                  disabled={!canManage || uploading[row.doc.id]}
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    event.target.value = ''
                    if (file) void onUpload(row.doc, file)
                  }}
                />
              </label>
            ) : null}
            {presence === true && hasFile ? (
              <button type="button" className="btn-secondary btn-compact" onClick={() => setOpenCode(openCode === row.norm ? null : row.norm)}>
                {openCode === row.norm
                  ? t('app.candidate_card.ia.done', { defaultValue: 'Done' })
                  : t('app.candidate_card.ia.open_row', { defaultValue: 'Open' })}
              </button>
            ) : null}
          </div>
        </div>
        {presence === true && licence ? (
          <label className="mt-2 block max-w-sm text-xs text-slate-500">
            {t('app.candidate_card.ia.issuing_country', { defaultValue: 'Issuing country' })}
            <select
              className="input mt-1 text-sm"
              disabled={!canManage}
              value={country || 'unknown'}
              onChange={(event) => void patchFacts({ licence_issuing_country: event.target.value })}
            >
              <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
              {(countries || []).map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
        ) : null}
        {presence === true && sharedCode95 ? (
          <label className="mt-2 block max-w-sm text-xs text-slate-500">
            {t('app.candidate_card.ia.code95_valid_to', { defaultValue: 'Code 95 valid to' })}
            <input
              type="date"
              className="input mt-1 text-sm"
              disabled={!canManage}
              value={step('code95')?.valid_to || ''}
              onChange={(event) => void patchFacts({ code95_valid_to: event.target.value || 'unknown' })}
            />
          </label>
        ) : null}
        {openCode === row.norm && presence === true && hasFile ? (
          <div className="mt-2">{renderOpen(row.doc)}</div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {required.length ? (
        <WorkspaceSection title={t('app.candidate_card.ia.mandatory_group', { defaultValue: 'Required' })}>
          <div>{required.map(renderRow)}</div>
        </WorkspaceSection>
      ) : null}
      {preferred.length ? (
        <WorkspaceSection title={t('app.candidate_card.ia.preferred_group', { defaultValue: 'Preferred' })}>
          <div>{preferred.map(renderRow)}</div>
        </WorkspaceSection>
      ) : null}
    </div>
  )
}
