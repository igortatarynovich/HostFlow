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
import { InlineActions } from '../../components/ui/InlineActions'
import { MetadataGrid } from '../../components/ui/MetadataGrid'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import DateInput from '../../components/controls/DateInput'
import { useI18n } from '../../i18n'
import { runtimeBadgeFromDocument } from '../../utils/runtimeBadgePresentation'
import type { OperatorFactsView } from '../candidates/OperatorFactsSurface'
import { DocumentMetadataForm } from './components/DocumentMetadataForm'
import { getDocumentFieldsConfig, isProcedureDocument } from './documentFieldsConfig'
import { computeTodayIso, documentHasFiles, formatDate, isSyntheticDocumentId, legalDocumentSlot, normalizeDocTypeCode, stayDocumentRole } from './documentUtils'
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
  discardEdits,
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
  getLabel: (code: string, name?: string | null, title?: Record<string, string> | null) => string
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
  discardEdits: (doc: Document) => void
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
  const issuingCountry = facts?.steps?.find((item) => item.key === 'driving_licence')?.issuing_country || ''
  const separateCode95 = facts?.steps?.find((item) => item.key === 'code95')?.visible === true
  const code95Required = Object.entries(typeLevel).some(([code, level]) => {
    const norm = normalizeDocTypeCode(code)
    return level === 'required' && (CODE95_TYPES.has(norm) || norm === 'driver_license_code95')
  })

  const rows = useMemo(() => {
    const built = docTypes.flatMap((type) => {
      const norm = normalizeDocTypeCode(type.code)
      if (CODE95_TYPES.has(norm) && (!code95Required || !separateCode95)) return []
      if (only && !only.has(norm)) return []
      if (!only && !groups && (exclude.has(norm) || legalDocumentSlot(type))) return []
      const matches = docs.filter((doc) => normalizeDocTypeCode(doc.type_code || doc.doc_type || '') === norm)
      const doc = preferredDoc(matches)
      if (!doc) return []
      return [{ type, norm, doc }]
    })
    const licences = built.filter((row) => LICENCE_TYPES.has(row.norm))
    if (licences.length < 2) return built
    const keep = licences.find((row) => documentHasFiles(row.doc))
      || licences.find((row) => row.norm === 'driver_license')
      || licences[0]
    return built.filter((row) => !LICENCE_TYPES.has(row.norm) || row === keep)
  }, [code95Required, docTypes, docs, exclude, groups, only, separateCode95])

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
  const persistPresence = async (
    norm: string,
    next: boolean,
    type?: { code?: string | null; process_type?: string | null },
  ) => {
    const stepKey = PRESENCE_STEP[norm]
    const patchKey = stepKey ? PRESENCE_PATCH[stepKey] : undefined
    const presencePatch = patchKey
      ? { [patchKey]: next }
      : { document_presence: { [LICENCE_TYPES.has(norm) ? 'driver_license' : norm]: next } }
    const role = type ? stayDocumentRole(type) : null
    if (next && role === 'visa') {
      const current = step('stay_basis')?.stored
      const basis = current === 'visa_c' || current === 'visa_d' ? current : 'visa_d'
      await patchFacts({ ...presencePatch, stay_basis: basis, stay_card_kind: null })
      return
    }
    if (next && role === 'card') {
      const code = normalizeDocTypeCode(type?.code)
      const kind = code.includes('rezydent') ? 'rezydent' : 'pobytu'
      await patchFacts({ ...presencePatch, stay_basis: 'karta_pobytu', stay_card_kind: kind })
      return
    }
    await patchFacts(presencePatch)
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

  const contextLine = (doc: Document) => {
    const meta = (doc.meta_json || doc.meta || {}) as Record<string, unknown>
    const listed = (value: unknown) => (Array.isArray(value) ? value.map(String).filter(Boolean) : [])
    const categories = listed(meta.categories)
    if (categories.length) return categories.join('/')
    const classes = listed(meta.classes)
    if (classes.length) return classes.join(', ')
    if (typeof meta.visa_type === 'string' && meta.visa_type) return meta.visa_type
    return ''
  }
  const permitOptions = (norm: string) =>
    getDocumentFieldsConfig(norm).find((field) => field.key === 'work_permit_type')?.options || []
  const permitLabel = (norm: string, value: string) => {
    const option = permitOptions(norm).find((item) => item.value === value)
    if (!option) return value
    return option.labelKey ? t(option.labelKey, { defaultValue: option.label }) : option.label
  }

  const renderRow = (row: (typeof rows)[number]) => {
    const hasFile = documentHasFiles(row.doc)
    const procedure = isProcedureDocument(row.norm)
    const storedPresence = readPresence(row.norm)
    const presence = storedPresence === true || storedPresence === false
      ? storedPresence
      : (hasFile ? true : null)
    const fileName = row.doc.files?.[0]?.name || ''
    const uploadedAt = row.doc.files?.[0]?.uploaded_at
    const licence = LICENCE_TYPES.has(row.norm)
    const country = licence ? issuingCountry : ''
    const showSharedCode95 = licence && code95Required && Boolean(issuingCountry) && !separateCode95 && presence === true
    const needsCountry = licence && code95Required && !issuingCountry && presence !== false
    const stayRole = stayDocumentRole(row.type)
    const phase: DocumentStatusKind | null = procedure
      ? (hasFile ? null : row.doc.status === 'in_progress' ? 'received' : row.doc.ordered_at ? 'ordered' : 'absent')
      : null
    const showMetadata = Boolean(hasFile || (stayRole && presence === true))
    const showFacts = Boolean((licence && (presence === true || needsCountry)) || showSharedCode95)
    const expanded = (needsCountry || openCode === row.norm) && (showMetadata || showFacts)
    const meta = (row.doc.meta_json || row.doc.meta || {}) as Record<string, unknown>
    const storedPermit = typeof meta.work_permit_type === 'string' ? meta.work_permit_type : ''
    const selectedPermit = permitType[row.norm] ?? storedPermit
    const setPresence = (next: boolean) => {
      if (!canManage) return
      if (next) setOpenCode(row.norm)
      else setOpenCode((current) => (current === row.norm ? null : current))
      void persistPresence(row.norm, next, row.type)
    }
    const uploadControl = (appearance: 'button' | 'link') => (
      <DocumentUploadAction
        appearance={appearance}
        label={uploading[row.doc.id]
          ? t('common.saving')
          : hasFile
            ? t('admin.documents.actions.replace', { defaultValue: 'Replace' })
            : t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
        disabled={!canManage || uploading[row.doc.id]}
        onFile={(file) => {
          setOpenCode(row.norm)
          void onUpload(row.doc, file).then(() => {
            if (readPresence(row.norm) !== true) void persistPresence(row.norm, true, row.type)
          })
        }}
      />
    )
    const markedRequired = (typeLevel[row.type.code] || 'required') === 'required'
      || (licence && Object.entries(typeLevel).some(([code, level]) => level === 'required' && LICENCE_TYPES.has(normalizeDocTypeCode(code))))
    const requirement = (
      <StatusBadge
        size="sm"
        shape="pill"
        semantic={markedRequired ? 'warning' : 'neutral'}
        label={markedRequired
          ? t('app.candidate_card.ia.required_mark', { defaultValue: 'Required' })
          : t('app.candidate_card.ia.preferred_mark', { defaultValue: 'Preferred' })}
      />
    )
    const fileKind = hasFile ? statusKind(row.doc, true) : (phase === 'received' ? 'received' : 'missing')
    const fileStatus = procedure && !hasFile && phase === 'absent' ? (
      <label className="workspace-editor block w-full max-w-[14rem]">
        <span className="sr-only">{t('admin.documents.forms.fields.work_permit_type', { defaultValue: 'Permit type' })}</span>
        <select
          className="input"
          disabled={!canManage}
          value={selectedPermit}
          onChange={(event) => setPermitType((prev) => ({ ...prev, [row.norm]: event.target.value }))}
        >
          <option value="">{t('app.candidate_card.ia.doc_choose_type', { defaultValue: 'Choose type' })}</option>
          {permitOptions(row.norm).map((option) => (
            <option key={option.value} value={option.value}>
              {option.labelKey ? t(option.labelKey, { defaultValue: option.label }) : option.label}
            </option>
          ))}
        </select>
      </label>
    ) : procedure && !hasFile && phase === 'ordered' ? (
      <span className="truncate text-sm text-slate-700">{statusLabel('ordered', row.doc)}</span>
    ) : (
      <span className="inline-flex min-w-0 items-center gap-2">
        {hasFile ? <DocumentFile name={fileName} /> : null}
        {procedure && storedPermit ? (
          <span className="truncate text-xs text-slate-500">{permitLabel(row.norm, storedPermit)}</span>
        ) : null}
        {(procedure ? hasFile || phase === 'received' : presence !== false) ? (
          <DocumentStatusBadge kind={fileKind} label={statusLabel(fileKind, row.doc)} />
        ) : null}
      </span>
    )
    let action: ReactNode = null
    if (procedure && !hasFile && phase === 'absent') {
      action = (
        <Button
          type="button"
          variant="primary"
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
          variant="primary"
          size="compact"
          disabled={!canManage || coreSaving[row.doc.id]}
          onClick={() => void recordProcedure(row.doc, { status: 'in_progress' })}
        >
          {t('app.candidate_card.ia.doc_mark_received', { defaultValue: 'Document received' })}
        </Button>
      )
    } else if ((procedure && phase === 'received' && !hasFile) || (!procedure && presence === true && !hasFile)) {
      action = uploadControl('button')
    } else if (hasFile) {
      action = (
        <Button type="button" variant="link" onClick={() => openDoc(row.doc)}>
          {t('admin.documents.actions.open', { defaultValue: 'Open' })}
        </Button>
      )
    }
    const reviewKind = statusKind(row.doc, true)
    const metadataForm = showMetadata ? (
      <DocumentMetadataForm
        doc={row.doc}
        metadataValues={metadataEdits[row.doc.id] ?? {}}
        disabled={!canManage}
        omitKeys={licence ? ['country'] : undefined}
        getFieldValue={getFieldValue}
        onChange={updateFieldValue}
      />
    ) : null
    const details = expanded ? (
      <DocumentDetails
        file={hasFile ? (
          <div className="space-y-2">
            <div className="text-xs text-slate-500">{t('app.candidate_card.ia.doc_file_heading', { defaultValue: 'File' })}</div>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <DocumentFile name={fileName} />
              <DocumentStatusBadge kind={reviewKind} label={statusLabel(reviewKind, row.doc)} />
            </div>
            {uploadedAt ? (
              <div className="text-xs text-slate-500">
                {t('app.candidate_card.ia.doc_uploaded_on', {
                  defaultValue: 'Uploaded {date}',
                  values: { date: formatDate(uploadedAt) },
                })}
              </div>
            ) : null}
            <InlineActions
              items={[
                {
                  key: 'open',
                  node: (
                    <Button type="button" variant="link" onClick={() => openDoc(row.doc)}>
                      {t('admin.documents.actions.open', { defaultValue: 'Open' })}
                    </Button>
                  ),
                },
                { key: 'replace', node: canManage ? uploadControl('link') : null },
                {
                  key: 'remove',
                  node: canManage ? (
                    <Button type="button" variant="linkDanger" onClick={() => deleteDocumentFile(row.doc)}>
                      {t('app.candidate_card.ia.doc_remove', { defaultValue: 'Remove file' })}
                    </Button>
                  ) : null,
                },
              ]}
            />
            <InlineActions
              items={[
                reviewKind !== 'approved' ? {
                  key: 'approve',
                  node: (
                    <Button type="button" variant="link" disabled={!canManage} onClick={() => approveDocument(row.doc)}>
                      {t('admin.documents.actions.approve', { defaultValue: 'Approve' })}
                    </Button>
                  ),
                } : { key: 'approve', node: null },
                reviewKind !== 'rejected' ? {
                  key: 'reject',
                  node: (
                    <Button type="button" variant="linkDanger" disabled={!canManage} onClick={() => rejectDocument(row.doc)}>
                      {t('admin.documents.actions.reject', { defaultValue: 'Reject' })}
                    </Button>
                  ),
                } : { key: 'reject', node: null },
              ]}
            />
          </div>
        ) : null}
        metadata={(showMetadata || showFacts) ? (
          <div className="space-y-3">
            <MetadataGrid title={showMetadata ? t('app.candidate_card.ia.doc_data_heading', { defaultValue: 'Document data' }) : undefined}>
              {licence && (presence === true || needsCountry) ? (
                <label className="block">
                  <div className="text-xs text-slate-500">{t('app.candidate_card.ia.issuing_country', { defaultValue: 'Issuing country' })}</div>
                  <select
                    className="input"
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
                  <div className="text-xs text-slate-500">{t('app.candidate_card.ia.code95_valid_to', { defaultValue: 'Code 95 valid to' })}</div>
                  <DateInput
                    disabled={!canManage}
                    value={step('code95')?.valid_to || ''}
                    onValueChange={(next) => void patchFacts({ code95_valid_to: next || 'unknown' })}
                  />
                </label>
              ) : null}
              {metadataForm}
            </MetadataGrid>
            {showMetadata && canManage ? (
              <div className="flex items-center justify-end gap-2">
                <Button type="button" variant="secondary" size="compact" onClick={() => discardEdits(row.doc)}>
                  {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="compact"
                  disabled={coreSaving[row.doc.id]}
                  onClick={() => saveCoreFields(row.doc)}
                >
                  {coreSaving[row.doc.id] ? t('common.saving') : t('common.actions.save', { defaultValue: 'Save' })}
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      />
    ) : null

    const subtitle = contextLine(row.doc) || (licence && country
      ? (countries || []).find((item) => item.value === country)?.label || ''
      : '')
    return (
      <DocumentRequirementRow
        key={row.norm}
        title={licence
          ? t('admin.documents.type_codes.driver_license', { defaultValue: 'Driving licence' })
          : getLabel(row.type.code, row.type.name, row.type.title)}
        subtitle={subtitle || null}
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
        onToggle={(presence === true && (hasFile || Boolean(stayRole) || licence)) || (procedure && hasFile)
          ? () => setOpenCode((current) => (current === row.norm ? null : row.norm))
          : undefined}
        details={details}
      />
    )
  }

  if (groups && renderGroups) {
    const nodes: Record<string, ReactNode> = {}
    for (const group of groups) {
      const wanted = expandTypeCodes(group.types)
      const stayBasis = step('stay_basis')?.stored || ''
      const cardChosen = rows.some((row) => {
        if (stayDocumentRole(row.type) !== 'card') return false
        const stored = readPresence(row.norm)
        return stored === true || (stored !== false && documentHasFiles(row.doc))
      })
      const grouped = rows.filter((row) => {
        const inGroup = wanted.has(row.norm) || legalDocumentSlot(row.type) === group.key
        if (!inGroup) return false
        if (group.key !== 'stay') return true
        if (stayDocumentRole(row.type) !== 'decision') return true
        return cardChosen || stayBasis === 'karta_pobytu'
      })
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
    <WorkspaceSection
      title={t('app.candidate_card.ia.documents_list', { defaultValue: 'Documents' })}
      description={t('app.candidate_card.ia.doc_list_hint', { defaultValue: 'The document list comes from the candidate profile.' })}
    >
      <DocumentRequirementList columns={columns}>{ordered.map(renderRow)}</DocumentRequirementList>
    </WorkspaceSection>
  )
}
