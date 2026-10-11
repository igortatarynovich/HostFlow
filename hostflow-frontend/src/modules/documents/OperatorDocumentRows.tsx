import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import type { Document, DocumentStatus } from '../../api/types'
import { EQUIVALENT_TYPE_GROUPS } from '../../data/documentTypeAliases'
import { Button } from '../../components/ui/Button'
import { DocumentDetails } from '../../components/ui/documentRequirement/DocumentDetails'
import { DocumentFile } from '../../components/ui/documentRequirement/DocumentFile'
import { DocumentRequirementList, type DocumentRequirementColumns } from '../../components/ui/documentRequirement/DocumentRequirementList'
import { DocumentUploadAction } from '../../components/ui/documentRequirement/DocumentUploadAction'
import { DocumentRequirementRow } from '../../components/ui/documentRequirement/DocumentRequirementRow'
import { DocumentStatus as DocumentStatusBadge, type DocumentStatusKind } from '../../components/ui/documentRequirement/DocumentStatus'
import { PresenceToggle } from '../../components/ui/documentRequirement/PresenceToggle'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import DateInput from '../../components/controls/DateInput'
import { useI18n } from '../../i18n'
import { runtimeBadgeFromDocument } from '../../utils/runtimeBadgePresentation'
import type { OperatorFactsView } from '../candidates/OperatorFactsSurface'
import { DocumentMetadataForm } from './components/DocumentMetadataForm'
import { getDocumentFieldsConfig, isProcedureDocument } from './documentFieldsConfig'
import { computeTodayIso, documentHasFiles, formatDate, isSyntheticDocumentId, normalizeDocTypeCode } from './documentUtils'
import type { MetadataState } from './types'

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
  additional: 'additional',
  additional_document: 'additional',
}

const PRESENCE_PATCH: Record<string, string> = {
  code95: 'code95_presence',
  tachograph: 'tachograph_presence',
  adr: 'adr_presence',
  medical: 'medical_presence',
  psych: 'psych_presence',
  additional: 'additional_presence',
}

const LICENCE_TYPES = new Set(['driver_license', 'driver_license_code95', 'driver_licence'])
const CODE95_TYPES = new Set(['code95', 'driver_qualification_card', 'qualification_code95'])

export type DocumentRowGroup = { key: string; types: string[] }

function expandTypeCodes(codes: Iterable<string>): Set<string> {
  const out = new Set<string>()
  const pending = Array.from(codes, (code) => normalizeDocTypeCode(code)).filter(Boolean)
  while (pending.length) {
    const norm = pending.pop() || ''
    if (!norm || out.has(norm)) continue
    out.add(norm)
    for (const group of EQUIVALENT_TYPE_GROUPS) {
      if (group.some((item) => normalizeDocTypeCode(item) === norm)) {
        for (const item of group) pending.push(normalizeDocTypeCode(item))
      }
    }
  }
  return out
}

function preferredDoc(list: Document[]): Document | undefined {
  const real = list.filter((doc) => !isSyntheticDocumentId(doc.id))
  const pool = real.length ? real : list
  return pool.find((doc) => documentHasFiles(doc)) || pool[0]
}

function statusKind(doc: Document, hasFile: boolean): DocumentStatusKind {
  if (!hasFile) return 'missing'
  const badge = runtimeBadgeFromDocument(doc).badge
  if (badge === 'approved') return 'approved'
  if (badge === 'rejected') return 'rejected'
  if (badge === 'pending' || badge === 'expiring_soon' || badge === 'expired') return 'review'
  return 'uploaded'
}

export function OperatorDocumentRows({
  candidateId,
  docs,
  docTypes,
  typeLevel,
  onlyTypes,
  excludeTypes,
  groups,
  renderGroups,
  canManage,
  countries,
  getLabel,
  onUpload,
  uploading,
  onFactsSaved,
  metadataEdits,
  getFieldValue,
  updateFieldValue,
  saveCoreFields,
  approveDocument,
  rejectDocument,
  deleteDocumentFile,
  openDoc,
  recordProcedure,
  coreSaving,
}: {
  candidateId: string
  docs: Document[]
  docTypes: Array<{ code: string; name?: string | null }>
  typeLevel: Record<string, TypeLevel>
  onlyTypes?: string[]
  excludeTypes?: string[]
  groups?: DocumentRowGroup[]
  renderGroups?: (nodes: Record<string, ReactNode>) => ReactNode
  canManage: boolean
  countries?: Array<{ value: string; label: string }>
  getLabel: (code: string, name?: string | null) => string
  onUpload: (doc: Document, file: File) => Promise<void>
  uploading: Record<string, boolean>
  onFactsSaved?: () => void
  metadataEdits: Record<string, MetadataState>
  getFieldValue: (doc: Document, fieldKey: string, metadataValues: MetadataState) => unknown
  updateFieldValue: (doc: Document, fieldKey: string, value: unknown) => void
  saveCoreFields: (doc: Document) => void
  approveDocument: (doc: Document) => void
  rejectDocument: (doc: Document) => void
  deleteDocumentFile: (doc: Document) => void
  openDoc: (doc: Document) => void
  recordProcedure: (doc: Document, patch: { ordered_at?: string | null; status?: DocumentStatus; meta?: Record<string, unknown> }) => Promise<void>
  coreSaving: Record<string, boolean>
}) {
  const { t } = useI18n()
  const [facts, setFacts] = useState<OperatorFactsView | null>(null)
  const [openCode, setOpenCode] = useState<string | null>(null)
  const [permitType, setPermitType] = useState<Record<string, string>>({})
  const yes = t('app.candidate_card.ia.doc_present', { defaultValue: 'Present' })
  const no = t('app.candidate_card.ia.doc_absent', { defaultValue: 'Absent' })
  const columns: DocumentRequirementColumns = {
    name: t('app.candidate_card.ia.doc_col_name', { defaultValue: 'Document' }),
    requirement: t('app.candidate_card.ia.doc_col_requirement', { defaultValue: 'Requirement' }),
    presence: t('app.candidate_card.ia.doc_col_presence', { defaultValue: 'Presence' }),
    file: t('app.candidate_card.ia.doc_col_file', { defaultValue: 'File and status' }),
    action: t('app.candidate_card.ia.doc_col_action', { defaultValue: 'Action' }),
  }

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

  const only = useMemo(() => (onlyTypes ? expandTypeCodes(onlyTypes) : null), [onlyTypes])
  const exclude = useMemo(() => expandTypeCodes(excludeTypes || []), [excludeTypes])
  const sharedCode95 = facts?.ce_code95?.evidence_shape === 'shared'

  const rows = useMemo(() => {
    return docTypes.flatMap((type) => {
      const norm = normalizeDocTypeCode(type.code)
      if (sharedCode95 && CODE95_TYPES.has(norm)) return []
      if (only && !only.has(norm)) return []
      if (!only && exclude.has(norm)) return []
      const matches = docs.filter((doc) => normalizeDocTypeCode(doc.type_code || doc.doc_type || '') === norm)
      const doc = preferredDoc(matches)
      if (!doc) return []
      return [{ type, norm, doc }]
    })
  }, [docTypes, docs, exclude, only, sharedCode95])

  const step = (key: string) => facts?.steps?.find((item) => item.key === key)
  const patchFacts = async (patch: Record<string, unknown>) => {
    const response = await api.put<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`, patch)
    setFacts(response.data)
    onFactsSaved?.()
  }
  const readPresence = (norm: string): boolean | null => {
    const stepKey = PRESENCE_STEP[norm]
    if (stepKey) {
      const value = step(stepKey)?.presence
      return value === true || value === false ? value : null
    }
    const map = facts?.document_presence || {}
    const keys = LICENCE_TYPES.has(norm) ? ['driver_license', norm] : [norm]
    for (const key of keys) {
      const value = map[key]
      if (value === true || value === false) return value
    }
    return null
  }
  const persistPresence = async (norm: string, next: boolean) => {
    const stepKey = PRESENCE_STEP[norm]
    const patchKey = stepKey ? PRESENCE_PATCH[stepKey] : undefined
    if (patchKey) {
      await patchFacts({ [patchKey]: next })
      return
    }
    const code = LICENCE_TYPES.has(norm) ? 'driver_license' : norm
    await patchFacts({ document_presence: { [code]: next } })
  }

  const statusLabel = (kind: DocumentStatusKind, doc?: Document) => {
    if (kind === 'approved') return t('admin.documents.status_labels.approved', { defaultValue: 'Approved' })
    if (kind === 'rejected') return t('admin.documents.status_labels.rejected', { defaultValue: 'Rejected' })
    if (kind === 'review') return t('app.candidate_card.ia.doc_in_review', { defaultValue: 'In review' })
    if (kind === 'uploaded') return t('app.candidate_card.ia.doc_uploaded', { defaultValue: 'Uploaded' })
    if (kind === 'ordered') {
      return t('app.candidate_card.ia.ordered_on', {
        defaultValue: 'Ordered {date}',
        values: { date: formatDate(doc?.ordered_at) },
      })
    }
    if (kind === 'received') return t('app.candidate_card.ia.doc_received', { defaultValue: 'Received' })
    if (kind === 'absent') return t('app.candidate_card.ia.doc_no_document', { defaultValue: 'No document' })
    return t('app.candidate_card.ia.doc_not_uploaded', { defaultValue: 'Not uploaded' })
  }

  const renderRow = (row: (typeof rows)[number]) => {
    const hasFile = documentHasFiles(row.doc)
    const procedure = isProcedureDocument(row.norm)
    const storedPresence = readPresence(row.norm)
    const presence = storedPresence === true || storedPresence === false
      ? storedPresence
      : (hasFile ? true : null)
    const fileName = row.doc.files?.[0]?.name || ''
    const licence = LICENCE_TYPES.has(row.norm)
    const country = licence ? step('driving_licence')?.issuing_country || '' : ''
    const showSharedCode95 = licence && sharedCode95 && presence === true
    const phase: DocumentStatusKind | null = procedure
      ? (hasFile ? null : row.doc.status === 'in_progress' ? 'received' : row.doc.ordered_at ? 'ordered' : 'absent')
      : null
    const kind = phase || statusKind(row.doc, hasFile)
    const expanded = procedure || (presence === true && openCode === row.norm && (hasFile || licence))
    const meta = (row.doc.meta_json || row.doc.meta || {}) as Record<string, unknown>
    const storedPermit = typeof meta.work_permit_type === 'string' ? meta.work_permit_type : ''
    const selectedPermit = permitType[row.norm] ?? storedPermit
    const setPresence = (next: boolean) => {
      if (!canManage) return
      if (next) setOpenCode(row.norm)
      else setOpenCode((current) => (current === row.norm ? null : current))
      void persistPresence(row.norm, next)
    }
    const uploadControl = (
      <DocumentUploadAction
        label={uploading[row.doc.id]
          ? t('common.saving')
          : hasFile
            ? t('admin.documents.actions.replace', { defaultValue: 'Replace' })
            : t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
        disabled={!canManage || uploading[row.doc.id]}
        onFile={(file) => {
          setOpenCode(row.norm)
          void onUpload(row.doc, file).then(() => {
            if (readPresence(row.norm) !== true) void persistPresence(row.norm, true)
          })
        }}
      />
    )
    const requirement = (
      <StatusBadge
        size="sm"
        shape="pill"
        semantic={(typeLevel[row.type.code] || 'required') === 'required' ? 'warning' : 'neutral'}
        label={(typeLevel[row.type.code] || 'required') === 'required'
          ? t('app.candidate_card.ia.required_mark', { defaultValue: 'Required' })
          : t('app.candidate_card.ia.preferred_mark', { defaultValue: 'Preferred' })}
      />
    )
    const fileKind = hasFile ? statusKind(row.doc, true) : 'missing'
    const fileStatus = (
      <>
        {hasFile ? <DocumentFile name={fileName} /> : null}
        {!procedure && presence !== false ? (
          <DocumentStatusBadge kind={fileKind} label={statusLabel(fileKind, row.doc)} />
        ) : null}
        {procedure && hasFile ? (
          <DocumentStatusBadge kind={fileKind} label={statusLabel(fileKind, row.doc)} />
        ) : null}
      </>
    )
    let action: ReactNode = null
    if (procedure && !hasFile && phase === 'absent') {
      action = (
        <Button
          type="button"
          variant="secondary"
          size="compact"
          disabled={!canManage || !selectedPermit || coreSaving[row.doc.id]}
          onClick={() => void recordProcedure(row.doc, {
            ordered_at: computeTodayIso(),
            meta: { work_permit_type: selectedPermit },
          })}
        >
          {t('app.candidate_card.ia.doc_order', { defaultValue: 'Order' })}
        </Button>
      )
    } else if (procedure && !hasFile && phase === 'ordered') {
      action = (
        <Button
          type="button"
          variant="secondary"
          size="compact"
          disabled={!canManage || coreSaving[row.doc.id]}
          onClick={() => void recordProcedure(row.doc, { status: 'in_progress' })}
        >
          {t('app.candidate_card.ia.doc_mark_received', { defaultValue: 'Document received' })}
        </Button>
      )
    } else if ((procedure && phase === 'received' && !hasFile) || (!procedure && presence === true && !hasFile)) {
      action = uploadControl
    } else if (hasFile) {
      action = (
        <Button type="button" variant="secondary" size="compact" onClick={() => openDoc(row.doc)}>
          {t('admin.documents.actions.open', { defaultValue: 'Open' })}
        </Button>
      )
    }

    const details = expanded ? (
      <DocumentDetails
        file={(
          <div className="space-y-2">
            {hasFile ? <DocumentFile name={fileName} /> : null}
            <DocumentStatusBadge kind={hasFile ? statusKind(row.doc, true) : kind} label={statusLabel(hasFile ? statusKind(row.doc, true) : kind, row.doc)} />
            <div className="flex flex-wrap gap-2">
              {procedure && phase === 'absent' ? (
                <DocumentMetadataForm
                  doc={row.doc}
                  metadataValues={metadataEdits[row.doc.id] ?? {}}
                  disabled={!canManage}
                  onlyKeys={['work_permit_type']}
                  getFieldValue={() => selectedPermit}
                  onChange={(_doc, _key, value) => setPermitType((prev) => ({ ...prev, [row.norm]: String(value || '') }))}
                />
              ) : null}
              {procedure && (phase === 'ordered' || phase === 'received' || hasFile) && storedPermit ? (
                <p className="text-sm text-slate-700">
                  {t('admin.documents.forms.fields.work_permit_type', { defaultValue: 'Permit type' })}
                  {': '}
                  {(() => {
                    const option = getDocumentFieldsConfig(row.norm).find((field) => field.key === 'work_permit_type')?.options?.find((item) => item.value === storedPermit)
                    if (!option) return storedPermit
                    return option.labelKey ? t(option.labelKey, { defaultValue: option.label }) : option.label
                  })()}
                </p>
              ) : null}
              {hasFile ? uploadControl : null}
              {hasFile ? (
                <Button type="button" variant="secondary" size="compact" onClick={() => openDoc(row.doc)}>
                  {t('admin.documents.actions.open', { defaultValue: 'Open' })}
                </Button>
              ) : null}
              {hasFile && canManage ? (
                <Button type="button" variant="danger" size="compact" onClick={() => deleteDocumentFile(row.doc)}>
                  {t('app.candidate_card.ia.doc_remove', { defaultValue: 'Remove' })}
                </Button>
              ) : null}
              {hasFile && statusKind(row.doc, true) !== 'approved' ? (
                <Button type="button" variant="primary" size="compact" disabled={!canManage} onClick={() => approveDocument(row.doc)}>
                  {t('admin.documents.actions.approve', { defaultValue: 'Approve' })}
                </Button>
              ) : null}
              {hasFile && statusKind(row.doc, true) !== 'rejected' ? (
                <Button type="button" variant="danger" size="compact" disabled={!canManage} onClick={() => rejectDocument(row.doc)}>
                  {t('admin.documents.actions.reject', { defaultValue: 'Reject' })}
                </Button>
              ) : null}
            </div>
          </div>
        )}
        metadata={(
          <div className="space-y-3">
            {licence && presence === true ? (
              <label className="block">
                <div className="text-[11px] text-slate-500">{t('app.candidate_card.ia.issuing_country', { defaultValue: 'Issuing country' })}</div>
                <select
                  className="input input-sm mt-1"
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
            {showSharedCode95 ? (
              <label className="block">
                <div className="text-[11px] text-slate-500">{t('app.candidate_card.ia.code95_valid_to', { defaultValue: 'Code 95 valid to' })}</div>
                <DateInput
                  className="mt-1"
                  disabled={!canManage}
                  value={step('code95')?.valid_to || ''}
                  onValueChange={(next) => void patchFacts({ code95_valid_to: next || 'unknown' })}
                />
              </label>
            ) : null}
            {hasFile ? (
              <>
                <DocumentMetadataForm
                  doc={row.doc}
                  metadataValues={metadataEdits[row.doc.id] ?? {}}
                  disabled={!canManage}
                  omitKeys={licence ? ['country'] : undefined}
                  getFieldValue={getFieldValue}
                  onChange={updateFieldValue}
                />
                <Button
                  type="button"
                  variant="primary"
                  size="compact"
                  disabled={!canManage || coreSaving[row.doc.id]}
                  onClick={() => saveCoreFields(row.doc)}
                >
                  {coreSaving[row.doc.id] ? t('common.saving') : t('common.actions.save', { defaultValue: 'Save' })}
                </Button>
              </>
            ) : null}
          </div>
        )}
      />
    ) : null

    return (
      <DocumentRequirementRow
        key={row.norm}
        title={getLabel(row.type.code, row.type.name)}
        requirement={requirement}
        presence={procedure && !hasFile ? (
          <span className="text-sm text-slate-700">{statusLabel(phase || 'absent', row.doc)}</span>
        ) : procedure ? (
          <span className="text-sm text-slate-500">—</span>
        ) : (
          <PresenceToggle value={presence} yesLabel={yes} noLabel={no} disabled={!canManage} onChange={setPresence} />
        )}
        fileStatus={fileStatus}
        action={action}
        expanded={expanded}
        onToggle={!procedure && presence === true ? () => setOpenCode((current) => (current === row.norm ? null : row.norm)) : undefined}
        details={details}
      />
    )
  }

  if (groups && renderGroups) {
    const nodes: Record<string, ReactNode> = {}
    for (const group of groups) {
      const wanted = expandTypeCodes(group.types)
      const grouped = rows.filter((row) => wanted.has(row.norm))
      nodes[group.key] = grouped.length ? <DocumentRequirementList columns={columns}>{grouped.map(renderRow)}</DocumentRequirementList> : null
    }
    return <>{renderGroups(nodes)}</>
  }

  if (!rows.length) return null
  const ordered = [...rows].sort((left, right) => {
    const leftRequired = (typeLevel[left.type.code] || 'required') === 'required' ? 0 : 1
    const rightRequired = (typeLevel[right.type.code] || 'required') === 'required' ? 0 : 1
    return leftRequired - rightRequired
  })
  return (
    <WorkspaceSection title={t('app.candidate_card.ia.documents_list', { defaultValue: 'Documents' })}>
      <DocumentRequirementList columns={columns}>{ordered.map(renderRow)}</DocumentRequirementList>
    </WorkspaceSection>
  )
}
