import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
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
import { MetadataGrid } from '../../components/ui/MetadataGrid'
import { OverflowMenu, type OverflowMenuItem } from '../../components/ui/OverflowMenu'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import DateInput from '../../components/controls/DateInput'
import { useI18n } from '../../i18n'
import { runtimeBadgeFromDocument } from '../../utils/runtimeBadgePresentation'
import type { OperatorFactsView } from '../candidates/OperatorFactsSurface'
import { DocumentMetadataForm } from './components/DocumentMetadataForm'
import { getDocumentFieldsConfig, isProcedureDocument } from './documentFieldsConfig'
import { computeTodayIso, documentHasFiles, formatDate, isSyntheticDocumentId, legalDocumentSlot, normalizeDocTypeCode, stayDocumentRole } from './documentUtils'
import { codesKnownToContract, matchesContract, stayContractGroups, workContractGroups } from './legalizationDocumentSelection'
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

function placeholderDocument(candidateId: string, code: string, processType?: string | null): Document {
  return {
    id: `synthetic::${code}::${candidateId}`,
    candidate_id: candidateId,
    doc_type: code,
    type_code: code,
    process_type: processType || undefined,
    status: 'missing',
    files: [],
    meta_json: { synthetic: true, doc_type: code },
    has_files: false,
  } as Document
}

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
  const status = String(doc.status || '').toLowerCase()
  if (status === 'rejected' || status === 'cancelled') return 'rejected'
  if (status === 'expired') return 'expired'
  if (status === 'approved' || status === 'verified' || status === 'completed') return 'approved'
  const badge = runtimeBadgeFromDocument(doc).badge
  if (badge === 'rejected') return 'rejected'
  if (badge === 'expired') return 'expired'
  return 'review'
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
  hasEdits,
  catalogTypes = [],
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
  hasEdits?: (docId: string) => boolean
  catalogTypes?: Array<{ code: string; name?: string | null; title?: Record<string, string> | null; process_type?: string | null; aliases?: string[] | null }>
}) {
  const { t } = useI18n()
  const [facts, setFacts] = useState<OperatorFactsView | null>(null)
  const factsRequest = useRef(0)
  const [openCode, setOpenCode] = useState<string | null>(null)
  const [editingCode, setEditingCode] = useState<string | null>(null)
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
    const request = ++factsRequest.current
    let cancelled = false
    void api.get<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`).then((response) => {
      if (!cancelled && request === factsRequest.current) setFacts(response.data)
    }).catch(() => {
      if (!cancelled && request === factsRequest.current) setFacts(null)
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
    const request = ++factsRequest.current
    const response = await api.put<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`, patch)
    if (request === factsRequest.current) setFacts(response.data)
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
  const clearPresence = async (norm: string) => {
    const stepKey = PRESENCE_STEP[norm]
    const patchKey = stepKey ? PRESENCE_PATCH[stepKey] : undefined
    if (patchKey) {
      await patchFacts({ [patchKey]: 'unknown' })
      return
    }
    await patchFacts({
      document_presence: { [LICENCE_TYPES.has(norm) ? 'driver_license' : norm]: null },
    })
  }

  const statusLabel = (kind: DocumentStatusKind, doc?: Document) => {
    if (kind === 'approved') return t('admin.documents.status_labels.approved', { defaultValue: 'Approved' })
    if (kind === 'rejected') return t('admin.documents.status_labels.rejected', { defaultValue: 'Rejected' })
    if (kind === 'review') return t('app.candidate_card.ia.doc_in_review', { defaultValue: 'In review' })
    if (kind === 'uploaded') return t('app.candidate_card.ia.doc_uploaded', { defaultValue: 'Uploaded' })
    if (kind === 'ordered') {
      const date = formatDate(doc?.ordered_at)
      if (!date) return t('app.candidate_card.ia.doc_ordered', { defaultValue: 'Ordered' })
      return t('app.candidate_card.ia.ordered_on', {
        defaultValue: 'Ordered {date}',
        values: { date },
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

  const renderRow = (row: (typeof rows)[number], forceRequired = false) => {
    const hasFile = documentHasFiles(row.doc)
    const procedure = isProcedureDocument(row.norm)
    const storedPresence = readPresence(row.norm)
    const presence = storedPresence === true || storedPresence === false
      ? storedPresence
      : (hasFile ? true : null)
    const fileName = row.doc.files?.[0]?.name || ''
    const licence = LICENCE_TYPES.has(row.norm)
    const country = licence ? issuingCountry : ''
    const showSharedCode95 = licence && code95Required && Boolean(issuingCountry) && !separateCode95 && presence === true
    const needsCountry = licence && code95Required && !issuingCountry && presence !== false
    const stayRole = stayDocumentRole(row.type)
    const ordered = Boolean(procedure && !hasFile && (row.doc.ordered_at || row.doc.status === 'in_progress'))
    const procedurePresence: boolean | 'ordered' | null = !procedure
      ? presence
      : hasFile || presence === true
        ? true
        : presence === false
          ? false
          : ordered
            ? 'ordered'
            : null
    const showMetadata = Boolean(hasFile || (stayRole && presence === true) || (procedure && procedurePresence !== false && procedurePresence !== null))
    const showFacts = Boolean((licence && (presence === true || needsCountry)) || showSharedCode95)
    const expanded = (needsCountry || openCode === row.norm) && (showMetadata || showFacts)
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
    const markedRequired = forceRequired
      || stayDocumentRole(row.type) === 'decision'
      || (typeLevel[row.type.code] || 'required') === 'required'
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
    const fileKind = hasFile ? statusKind(row.doc, true) : 'missing'
    const fileStatus = procedurePresence === 'ordered' ? (
      <span className="truncate text-sm text-slate-700">{statusLabel('ordered', row.doc)}</span>
    ) : (
      <span className="inline-flex min-w-0 items-center gap-2">
        {hasFile ? <DocumentFile name={fileName} /> : null}
        {(procedure ? hasFile || procedurePresence === true : presence !== false) ? (
          <DocumentStatusBadge kind={fileKind} label={statusLabel(fileKind, row.doc)} />
        ) : null}
      </span>
    )
    const reviewKind = statusKind(row.doc, true)
    const menuItems: OverflowMenuItem[] = []
    if (procedure && !hasFile && ordered && canManage) {
      menuItems.push({
        id: 'received',
        label: t('app.candidate_card.ia.doc_mark_received', { defaultValue: 'Document received' }),
        disabled: Boolean(coreSaving[row.doc.id]),
        onSelect: () => void recordProcedure(row.doc, { status: 'in_progress' }),
      })
    }
    if (hasFile && canManage) {
      menuItems.push({
        id: 'replace',
        label: t('admin.documents.actions.replace', { defaultValue: 'Replace' }),
        disabled: Boolean(uploading[row.doc.id]),
        onSelect: () => document.getElementById(`doc-replace-${row.doc.id}`)?.click(),
      })
      menuItems.push({
        id: 'remove',
        label: t('app.candidate_card.ia.doc_remove', { defaultValue: 'Remove file' }),
        tone: 'danger',
        onSelect: () => deleteDocumentFile(row.doc),
      })
    }
    if (hasFile && canManage && reviewKind !== 'approved') {
      menuItems.push({
        id: 'approve',
        label: t('admin.documents.actions.approve', { defaultValue: 'Approve' }),
        onSelect: () => approveDocument(row.doc),
      })
    }
    if (hasFile && canManage && reviewKind !== 'rejected') {
      menuItems.push({
        id: 'reject',
        label: t('admin.documents.actions.reject', { defaultValue: 'Reject' }),
        tone: 'danger',
        onSelect: () => rejectDocument(row.doc),
      })
    }
    let primary: ReactNode = null
    if (hasFile) {
      primary = (
        <Button type="button" variant="link" onClick={() => openDoc(row.doc)}>
          {t('admin.documents.actions.open', { defaultValue: 'Open' })}
        </Button>
      )
    } else if (procedurePresence === true || (!procedure && presence === true)) {
      primary = uploadControl('button')
    }
    const action = (
      <div className="flex items-center justify-end gap-1">
        {primary}
        {hasFile && canManage ? (
          <DocumentUploadAction
            appearance="hidden"
            inputId={`doc-replace-${row.doc.id}`}
            label={t('admin.documents.actions.replace', { defaultValue: 'Replace' })}
            disabled={uploading[row.doc.id]}
            onFile={(file) => void onUpload(row.doc, file)}
          />
        ) : null}
        {menuItems.length ? (
          <OverflowMenu
            label={t('app.candidate_card.ia.doc_more_actions', { defaultValue: 'More actions' })}
            items={menuItems}
          />
        ) : null}
      </div>
    )
    const editing = editingCode === row.norm
    const metadataValues = metadataEdits[row.doc.id] ?? {}
    const readField = (key: string, kind: string) => {
      const raw = getFieldValue(row.doc, key, metadataValues)
      if (Array.isArray(raw)) return raw.filter(Boolean).join(', ')
      if (raw == null || raw === '') return ''
      if (kind === 'date') return formatDate(String(raw))
      if (kind === 'select') {
        const option = getDocumentFieldsConfig(row.norm).find((field) => field.key === key)?.options?.find((item) => item.value === raw)
        if (!option) return String(raw)
        return option.labelKey ? t(option.labelKey, { defaultValue: option.label }) : option.label
      }
      return String(raw)
    }
    const countryLabel = !country || country === 'unknown'
      ? t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })
      : ((countries || []).find((item) => item.value === country)?.label || country)
    const details = expanded ? (
      <DocumentDetails>
        <MetadataGrid title={t('app.candidate_card.ia.doc_data_heading', { defaultValue: 'Document data' })}>
          {editing ? (
            <>
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
              {showMetadata ? (
                <DocumentMetadataForm
                  doc={row.doc}
                  metadataValues={metadataValues}
                  disabled={!canManage}
                  omitKeys={licence ? ['country'] : procedure ? ['ordered_at'] : undefined}
                  getFieldValue={getFieldValue}
                  onChange={updateFieldValue}
                />
              ) : null}
            </>
          ) : (
            <>
              {licence ? (
                <div>
                  <div className="text-xs text-slate-500">{t('app.candidate_card.ia.issuing_country', { defaultValue: 'Issuing country' })}</div>
                  <div className="mt-1 text-sm text-slate-900">{countryLabel || '—'}</div>
                </div>
              ) : null}
              {showSharedCode95 ? (
                <div>
                  <div className="text-xs text-slate-500">{t('app.candidate_card.ia.code95_valid_to', { defaultValue: 'Code 95 valid to' })}</div>
                  <div className="mt-1 text-sm text-slate-900">{formatDate(step('code95')?.valid_to) || '—'}</div>
                </div>
              ) : null}
              {showMetadata ? getDocumentFieldsConfig(row.norm)
                .filter((field) => !(licence && field.key === 'country') && !(procedure && field.key === 'ordered_at'))
                .map((field) => (
                  <div key={field.key}>
                    <div className="text-xs text-slate-500">
                      {field.labelKey ? t(field.labelKey, { defaultValue: field.label }) : field.label}
                    </div>
                    <div className="mt-1 text-sm text-slate-900">{readField(field.key, field.type) || '—'}</div>
                  </div>
                )) : null}
            </>
          )}
        </MetadataGrid>
        {canManage ? (
          <div className="mt-3 flex items-center justify-end gap-2">
            {editing ? (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  size="compact"
                  onClick={() => {
                    discardEdits(row.doc)
                    setEditingCode(null)
                  }}
                >
                  {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="compact"
                  disabled={coreSaving[row.doc.id] || !hasEdits?.(row.doc.id)}
                  onClick={() => {
                    saveCoreFields(row.doc)
                    setEditingCode(null)
                  }}
                >
                  {coreSaving[row.doc.id] ? t('common.saving') : t('common.actions.save', { defaultValue: 'Save' })}
                </Button>
              </>
            ) : (
              <Button type="button" variant="secondary" size="compact" onClick={() => setEditingCode(row.norm)}>
                {t('common.actions.edit', { defaultValue: 'Edit' })}
              </Button>
            )}
          </div>
        ) : null}
      </DocumentDetails>
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
        presence={procedure ? (
          <PresenceToggle
            value={procedurePresence}
            yesLabel={yes}
            noLabel={no}
            orderedLabel={t('app.candidate_card.ia.doc_ordered', { defaultValue: 'Ordered' })}
            disabled={!canManage}
            onChange={(next) => {
              if (!next && (row.doc.ordered_at || ordered)) void recordProcedure(row.doc, { ordered_at: null })
              setPresence(next)
            }}
            onOrdered={() => {
              if (procedurePresence === 'ordered' || hasFile) return
              setOpenCode(row.norm)
              if (storedPresence === true || storedPresence === false) void clearPresence(row.norm)
              void recordProcedure(row.doc, { ordered_at: row.doc.ordered_at || computeTodayIso() })
            }}
          />
        ) : (
          <PresenceToggle value={presence} yesLabel={yes} noLabel={no} disabled={!canManage} onChange={setPresence} />
        )}
        fileStatus={fileStatus}
        action={action}
        expanded={expanded}
        onToggle={(showMetadata || showFacts)
          ? () => setOpenCode((current) => (current === row.norm ? null : row.norm))
          : undefined}
        details={details}
      />
    )
  }

  if (groups && renderGroups) {
    const nodes: Record<string, ReactNode> = {}
    const legal = facts?.legalization
    const workLabel = step('work')?.operator_label || ''
    const catalogs = [...docTypes, ...catalogTypes]
    const contractFor = (key: string) => {
      if (key === 'stay') {
        return legal?.selection.stay_required === true ? stayContractGroups(legal.selected_stay) : []
      }
      if (key === 'work') {
        return legal?.selection.work_required === true
          ? workContractGroups(workLabel, legal.applicable_work)
          : []
      }
      return []
    }
    const rowMatches = (
      row: { norm: string; type: { code?: string | null } },
      known: Set<string>,
    ) => matchesContract(row.type.code, known) || matchesContract(row.norm, known)
    for (const group of groups) {
      const contract = contractFor(group.key)
      if (group.key !== 'stay' && group.key !== 'work') {
        const wanted = expandTypeCodes(group.types)
        const grouped = rows.filter((row) => wanted.has(row.norm) || legalDocumentSlot(row.type) === group.key)
        nodes[group.key] = grouped.length
          ? <DocumentRequirementList columns={columns}>{grouped.map((row) => renderRow(row))}</DocumentRequirementList>
          : null
        continue
      }
      const used = new Set<string>()
      const visible = contract.flatMap((evidenceGroup) => {
        const known = codesKnownToContract(evidenceGroup.codes)
        const matches = rows.filter((row) => !used.has(row.doc.id) && rowMatches(row, known))
        let best = matches.find((row) => documentHasFiles(row.doc))
          || matches.find((row) => !isSyntheticDocumentId(row.doc.id) && row.doc.ordered_at)
          || matches.find((row) => !isSyntheticDocumentId(row.doc.id))
          || matches[0]
        if (!best) {
          const stored = docs.find((doc) => (
            !isSyntheticDocumentId(doc.id)
            && !used.has(doc.id)
            && (matchesContract(doc.type_code, known) || matchesContract(doc.doc_type, known))
          ))
          const type = catalogs.find((item) => matchesContract(item.code, known))
          if (stored && type) {
            best = { type, norm: normalizeDocTypeCode(type.code), doc: stored }
          } else if (stored) {
            const code = stored.type_code || stored.doc_type || ''
            best = { type: { code, name: code }, norm: normalizeDocTypeCode(code), doc: stored }
          } else if (type) {
            best = {
              type,
              norm: normalizeDocTypeCode(type.code),
              doc: placeholderDocument(
                candidateId,
                type.code,
                'process_type' in type ? type.process_type : undefined,
              ),
            }
          }
        }
        if (!best) return []
        used.add(best.doc.id)
        return [best]
      })
      nodes[group.key] = visible.length
        ? <DocumentRequirementList columns={columns}>{visible.map((row) => renderRow(row, true))}</DocumentRequirementList>
        : null
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
      <DocumentRequirementList columns={columns}>{ordered.map((row) => renderRow(row))}</DocumentRequirementList>
    </WorkspaceSection>
  )
}
