import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, listReminders } from '../../api/client'
import type { ReminderRecord } from '../../api/types'
import {
  confirmHrDriverLegal,
  confirmHrDriverTerms,
  getHrEmployeeRecordSurface,
  recordHrDriverReady,
  startHrDriverEmployment,
  updateHrEmployeeRecordPerson,
  type HrDriverLegalIn,
  type HrDriverTermsIn,
  type HrEmployeeRecordGroup,
  type HrEmployeeRecordAddress,
  type HrEmployeeRecordPersonIn,
  type HrEmployeeRecordRow,
  type HrEmployeeRecordSurface,
} from '../../api/workforce'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { Combobox } from '../ui/Combobox'
import { Checkbox, Input } from '../ui/FieldControls'
import { MultiCombobox } from '../ui/MultiCombobox'
import { useI18n } from '../../i18n'
import { usePlatformCountryOptions, usePlatformDialCodeOptions } from '../../hooks/usePlatformCatalogOptions'
import { PREFERRED_CONTACT_VALUES } from '../../data/preferredContactChannels'
import CandidateDocuments from '../../modules/documents/CandidateDocuments'
import OperatorFactsSurface from '../../modules/candidates/OperatorFactsSurface'
import { CandidateQuickTaskModal } from '../../modules/candidates/components/CandidateQuickTaskModal'
import type { CandidateNote, StageHistoryEntry } from '../../modules/candidate-card/types'
import ActivityRailWidget from '../../platform/entity-workspace/ActivityRailWidget'
import { EntityRecordHeader } from '../../platform/entity-workspace/EntityRecordHeader'
import NotesRailWidget from '../../platform/entity-workspace/NotesRailWidget'
import { RequirementRowFrame } from '../../platform/entity-workspace/RequirementRow'
import {
  EntityRecordSection as CardAccordion,
  EntityRecordSurface,
  EntityRecordTabs,
  RailWidget,
} from '../../platform/entity-workspace/entityRecordSurface'
import { evidenceStatusLabelKey, type RequirementRowStatus } from '../../platform/entity-workspace/requirementRowStatus'
import { translateStageLabel } from '../../utils/stageLabels'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { useToast } from '../Toast'
import { Button } from '../ui/Button'
import { InlineFieldRow } from '../ui/InlineFieldRow'
import { OverflowMenu, type OverflowMenuItem } from '../ui/OverflowMenu'
import { StagePipeline } from '../ui/StagePipeline'
import { getLanguageDisplayName, getRegionDisplayName } from '../../utils/catalogLocale'
import { EndEmploymentModal, ReturnToRecruitmentModal } from './EmployeeLifecycleModals'

const HIDDEN_STATUS = new Set(['recorded', 'missing', 'canonical', 'process'])

type Translate = (key: string, options?: { defaultValue?: string }) => string

const KNOWN_OPTION_KEY: Record<string, string> = {
  visa_d: 'app.candidate_card.status.poland_basis.visa_d',
  visa_c: 'app.candidate_card.status.poland_basis.visa_c',
  karta_pobytu: 'app.candidate_card.status.poland_basis.karta_pobytu',
  waiting_for_trc: 'app.candidate_card.status.poland_basis.waiting_for_trc',
  eu_citizen: 'app.candidate_card.status.poland_basis.eu_citizen',
  other: 'app.candidate_card.status.poland_basis.other',
  none: 'app.candidate_card.status.poland_basis.none',
  not_required: 'app.hr.work_eligibility.status.not_required',
  yes: 'common.yes',
  no: 'common.no',
}

function formatDay(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [year, month, day] = iso.slice(0, 10).split('-')
  if (!year || !month || !day) return iso
  return `${day}.${month}.${year}`
}

function looksTechnical(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return true
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(trimmed)
}

function knownOptionLabel(t: Translate, value: string): string | null {
  const key = KNOWN_OPTION_KEY[value]
  if (!key) return null
  const label = t(key, { defaultValue: '' })
  return label && label !== key ? label : null
}

function catalogLabel(t: Translate, value: string): string {
  if (!value) return ''
  const known = knownOptionLabel(t, value)
  if (known) return known
  const keys = [
    `app.candidate_card.operator_facts.stay_option.${value}`,
    `app.candidate_card.operator_facts.work_option.${value}`,
    `app.candidate_card.operator_facts.citizenship_class.${value}`,
    `app.hr.employee_record.chain.${value}`,
  ]
  for (const key of keys) {
    const label = t(key, { defaultValue: '' })
    if (label && label !== key) return label
  }
  return ''
}

function copyOrEmpty(t: Translate, key: string, fallbackKey: string): string {
  const label = t(key, { defaultValue: '' })
  if (label && label !== key) return label
  const fallback = t(fallbackKey, { defaultValue: '' })
  return fallback && fallback !== fallbackKey ? fallback : ''
}

function groupTitle(t: Translate, id: string): string {
  return copyOrEmpty(t, `app.hr.employee_record.groups.${id}`, 'app.hr.employee_record.empty.generic')
}

function emptyCopy(t: Translate, code: string | null | undefined): string {
  if (!code) return copyOrEmpty(t, 'app.hr.employee_record.empty.generic', 'app.hr.employee_record.empty.generic')
  return copyOrEmpty(t, `app.hr.employee_record.empty.${code}`, 'app.hr.employee_record.empty.generic')
}

function actionCopy(t: Translate, code: string, part: 'title' | 'reason'): string {
  const key = `app.hr.employee_record.next_action.${code}.${part}`
  const label = t(key, { defaultValue: '' })
  return label && label !== key ? label : ''
}

function ownsNextAction(stepId: string, code: string | undefined, targetRowId: string | null): boolean {
  if (!code) return false
  if (code === 'confirm_terms') return stepId === 'terms'
  if (code === 'register_zus') return stepId === 'formalities'
  if (code === 'start_work_authorization' || code === 'confirm_legal') return stepId === 'legal'
  if (code === 'start_employment') return stepId === 'start'
  if (code === 'record_ready') return stepId === 'ready'
  if (code === 'confirm_fact' || code === 'resolve_requirement') {
    const group = (targetRowId || '').split('.')[0]
    if (group === 'legalizacja') return stepId === 'legal'
    if (group === 'zatrudnienie') return stepId === 'terms'
    if (group === 'formalnosci') return stepId === 'formalities'
    return stepId === 'verification'
  }
  return false
}

function pathTitle(t: Translate, stepId: string, target: string | null): string {
  if (stepId === 'verification') {
    return groupTitle(t, target === 'dane_osobowe' ? 'dane_osobowe' : 'kwalifikacje')
  }
  return copyOrEmpty(t, `app.hr.employee_record.path.${stepId}`, 'app.hr.employee_record.empty.generic')
}

function displayValue(value: string | null, label: string, locale: 'en' | 'ru' | 'pl', t?: Translate): string {
  if (!value) return '—'
  if (looksTechnical(value)) return '—'
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return formatDay(value)
  if (t) {
    const mapped = catalogLabel(t, value)
    if (mapped) return mapped
  }
  if (value.trim().length === 2 && (label === 'Obywatelstwo' || label === 'Citizenship')) {
    return getRegionDisplayName(value, locale)
  }
  if (/^[a-z0-9_]+$/.test(value.trim())) return '—'
  return value
}

const RECORD_TABS = ['dane_osobowe', 'legalizacja', 'kwalifikacje', 'zatrudnienie', 'formalnosci', 'dokumenty'] as const

const TAB_FOR_GROUP: Record<string, (typeof RECORD_TABS)[number]> = {
  dane_osobowe: 'dane_osobowe',
  legalizacja: 'legalizacja',
  kwalifikacje: 'kwalifikacje',
  badania: 'kwalifikacje',
  zatrudnienie: 'zatrudnienie',
  formalnosci: 'formalnosci',
  dokumenty: 'dokumenty',
}

function groupById(groups: HrEmployeeRecordGroup[], id: string): HrEmployeeRecordGroup | undefined {
  return groups.find((group) => group.id === id)
}

function rowById(groups: HrEmployeeRecordGroup[], id: string): HrEmployeeRecordRow | undefined {
  for (const group of groups) {
    const row = group.rows.find((item) => item.id === id)
    if (row) return row
  }
  return undefined
}

function meaningfulValue(row: HrEmployeeRecordRow, locale: 'en' | 'ru' | 'pl', t: Translate): string {
  const shown = displayValue(row.value, row.label, locale, t)
  if (shown !== '—') return shown
  return t('app.hr.employee_record.empty.missing', { defaultValue: 'Not filled in' })
}

export default function HrEmployeeRecordSurface({
  employeeId,
  manage,
}: {
  employeeId: string
  manage: boolean
}) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const [surface, setSurface] = useState<HrEmployeeRecordSurface | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState<(typeof RECORD_TABS)[number]>('dane_osobowe')
  const [documentFocus, setDocumentFocus] = useState<string | undefined>(undefined)

  const load = useCallback(async () => {
    const next = await getHrEmployeeRecordSurface(employeeId)
    setSurface(next)
    return next
  }, [employeeId])

  useEffect(() => {
    let cancelled = false
    setSurface(null)
    setError(null)
    getHrEmployeeRecordSurface(employeeId)
      .then((next) => {
        if (!cancelled) setSurface(next)
      })
      .catch(() => {
        if (!cancelled) {
          setError(t('app.hr.employee_record.load_error', { defaultValue: 'Could not load the employee record.' }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [employeeId, t])

  useEffect(() => {
    setTab('dane_osobowe')
    setDocumentFocus(undefined)
  }, [employeeId])

  const openDocuments = (typeCode?: string) => {
    setDocumentFocus(typeCode)
    setTab('dokumenty')
  }

  const openTarget = (target: string | null) => {
    if (!target) return
    const groupId = target.startsWith('group:') ? target.slice('group:'.length) : target.split('.')[0]
    const next = TAB_FOR_GROUP[groupId]
    if (next) setTab(next)
  }

  const openGroup = (groupId: string) => {
    const next = TAB_FOR_GROUP[groupId]
    if (next) setTab(next)
  }

  const finishSave = async (accepted: boolean, reason?: string | null) => {
    if (!accepted) {
      setError(reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
      return
    }
    setError(null)
    await load()
  }

  if (error && !surface) return <p className="alert-error">{error}</p>
  if (!surface) {
    return <p>{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  const groups = surface.groups
  const action = surface.current_process.next_action
  const returned =
    surface.current_process.destination === 'recruitment' || action?.code === 'returned_to_recruitment'
  const canEdit = manage && !returned
  const recruitmentHref = surface.candidate_id
    ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(surface.candidate_id)}`
    : null
  const activeGroup = (id: string) => groupById(groups, id)
  const runAction = () => {
    if (!action) return
    if (action.code === 'confirm_terms') openGroup('zatrudnienie')
    else if (action.code === 'confirm_legal' || action.code === 'start_work_authorization') openGroup('legalizacja')
    else if (action.code === 'record_ready') {
      setSaving(true)
      void recordHrDriverReady(employeeId)
        .then((result) => finishSave(result.accepted !== false, result.reason))
        .catch(() => setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' })))
        .finally(() => setSaving(false))
    } else if (action.code === 'register_zus') {
      navigate(CRM_APP_PATHS.hrZusWorkspace)
    } else if (surface.current_process.destination === 'recruitment' && recruitmentHref) {
      navigate(recruitmentHref)
    } else if (action.code === 'start_employment') {
      setSaving(true)
      void startHrDriverEmployment(employeeId)
        .then((result) => finishSave(result.activated === true, result.reason))
        .catch(() => setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' })))
        .finally(() => setSaving(false))
    } else openTarget(surface.current_process.target_row_id)
  }

  const openPath = (target: string | null) => {
    if (!target) return
    if (target === 'recruitment' && recruitmentHref) navigate(recruitmentHref)
    else if (target === 'formalnosci') navigate(CRM_APP_PATHS.hrZusWorkspace)
    else if (target === 'ready' || target === 'start') runAction()
    else {
      const next = TAB_FOR_GROUP[target]
      if (next) setTab(next)
    }
  }

  const qualificationCoverage = factCoverage(activeGroup('kwalifikacje') || { id: 'kwalifikacje', label: '', rows: [], empty: null })
  const medicalCoverage = factCoverage(activeGroup('badania') || { id: 'badania', label: '', rows: [], empty: null })

  return (
    <EntityRecordSurface
      header={(
        <EmployeeHero
          employeeId={employeeId}
          surface={surface}
          locale={locale}
          manage={manage}
          onOpen={openPath}
          onReload={load}
        />
      )}
      banner={error ? <p className="alert-error">{error}</p> : null}
      rail={(
        <>
          <RecordTasks
            candidateId={surface.candidate_id}
            candidateLabel={surface.header.name}
            locked={returned}
          />
          {surface.candidate_id ? (
            <RecordNotes candidateId={surface.candidate_id} locked={returned} />
          ) : null}
          {surface.candidate_id ? <RecordTimeline candidateId={surface.candidate_id} /> : null}
        </>
      )}
    >
          <EntityRecordTabs
            value={tab}
            onChange={setTab}
            tabs={RECORD_TABS.map((id) => ({ id, label: groupTitle(t, id) }))}
          />
          <div className="min-w-0 space-y-3" id={`record-group-${tab}`}>
            {tab === 'dane_osobowe' ? (
              <PersonForm
                key={employeeId}
                employeeId={employeeId}
                person={surface.person}
                writable={canEdit}
                onError={setError}
                onSaved={() => {
                  void load()
                }}
              />
            ) : null}
            {tab === 'legalizacja' && activeGroup('legalizacja') ? (
              <LegalForm
                key={employeeId}
                employeeId={employeeId}
                candidateId={surface.candidate_id}
                contextLabel={[surface.header.employer, surface.header.position].filter(Boolean).join(' · ')}
                group={activeGroup('legalizacja')!}
                legal={surface.legal}
                writable={canEdit && surface.state === 'preparing'}
                onOpenDocuments={() => openDocuments()}
                onError={setError}
                onSaved={() => {
                  void load()
                }}
              />
            ) : null}
            {tab === 'kwalifikacje' ? (
              <div className="space-y-3">
                <CardAccordion
                  title={groupTitle(t, 'kwalifikacje')}
                  defaultOpen
                  summary={qualificationCoverage ? `${qualificationCoverage} ${t('app.candidate_card.requirements_checklist.status.satisfied', { defaultValue: 'Confirmed' })}` : null}
                >
                  <FactSections
                    group={activeGroup('kwalifikacje')}
                    locale={locale}
                    onOpenDocuments={() => openDocuments()}
                  />
                </CardAccordion>
                <CardAccordion
                  title={groupTitle(t, 'badania')}
                  summary={medicalCoverage ? `${medicalCoverage} ${t('app.candidate_card.requirements_checklist.status.satisfied', { defaultValue: 'Confirmed' })}` : null}
                >
                  {activeGroup('badania') ? (
                    <GroupBody
                      group={activeGroup('badania')!}
                      locale={locale}
                      onOpenDocuments={() => openDocuments()}
                    />
                  ) : (
                    <p className="text-sm text-slate-500">{emptyCopy(t, 'not_materialized')}</p>
                  )}
                </CardAccordion>
              </div>
            ) : null}
            {tab === 'zatrudnienie' && activeGroup('zatrudnienie') ? (
              <CardAccordion title={groupTitle(t, 'zatrudnienie')} defaultOpen>
                <TermsForm
                  key={employeeId}
                  employeeId={employeeId}
                  group={activeGroup('zatrudnienie')!}
                  terms={surface.terms}
                  writable={canEdit && surface.state === 'preparing'}
                  onError={setError}
                  onSaved={() => {
                    void load()
                  }}
                />
              </CardAccordion>
            ) : null}
            {tab === 'formalnosci' && activeGroup('formalnosci') ? (
              <CardAccordion title={groupTitle(t, 'formalnosci')} defaultOpen>
                <CompactGroup group={activeGroup('formalnosci')!} locale={locale} documents={surface.documents} />
              </CardAccordion>
            ) : null}
            {tab === 'dokumenty' && surface.candidate_id ? (
              <div className="space-y-3">
                {(activeGroup('dokumenty')?.rows || [])
                  .filter((row) => row.id === 'dokumenty.passport')
                  .map((row) => (
                    <RequirementFactRow
                      key={row.id}
                      row={row}
                      locale={locale}
                      onOpenDocuments={() => openDocuments(row.id.slice('dokumenty.'.length))}
                    />
                  ))}
                <CandidateDocuments
                  candidateId={surface.candidate_id}
                  hideHeader
                  inlineWorkspace
                  initialType={documentFocus}
                  mutationsLocked={returned}
                  onDocumentsChanged={() => void load()}
                />
              </div>
            ) : null}
          </div>
    </EntityRecordSurface>
  )
}

function EmployeeHero({
  employeeId,
  surface,
  locale,
  manage,
  onOpen,
  onReload,
}: {
  employeeId: string
  surface: HrEmployeeRecordSurface
  locale: 'en' | 'ru' | 'pl'
  manage: boolean
  onOpen: (target: string | null) => void
  onReload: () => Promise<HrEmployeeRecordSurface>
}) {
  const { t } = useI18n()
  const [returnOpen, setReturnOpen] = useState(false)
  const [endOpen, setEndOpen] = useState(false)
  const overview = surface.overview
  const path = surface.path || []
  if (!overview) return null
  const groups = surface.groups
  const phaseLabel = copyOrEmpty(t, `app.hr.employee_record.phase.${overview.phase}`, 'app.hr.employee_record.empty.generic')
  const citizenship = overview.citizenship ? getRegionDisplayName(overview.citizenship, locale) : ''
  const contractRow = rowById(groups, 'zatrudnienie.contract_basis')
  const contract = contractRow ? displayValue(overview.contract_basis, contractRow.label, locale, t) : displayValue(overview.contract_basis, '', locale, t)
  const formalities = path.find((step) => step.id === 'formalities')
  const medicalRows = groupById(groups, 'badania')?.rows || []
  const medicalMark = medicalRows.length === 0
    ? null
    : medicalRows.every((row) => row.status === 'satisfied' || row.status === 'not_applicable')
      ? t('app.hr.employee_record.context.known', { defaultValue: 'In place' })
      : medicalRows.some((row) => row.status === 'blocking' || row.status === 'pending')
        ? t('app.hr.employee_record.context.open', { defaultValue: 'Open' })
        : '—'
  const action = surface.current_process.next_action
  const noticeTarget = surface.current_process.destination === 'recruitment'
    ? 'recruitment'
    : surface.current_process.target_row_id
  const lifecycleItems: OverflowMenuItem[] = []
  if (manage && overview.phase === 'preparing') {
    lifecycleItems.push(
      { id: 'return', label: t('app.hr.employee_record.lifecycle.return', { defaultValue: 'Return to recruitment' }), onSelect: () => setReturnOpen(true) },
      { id: 'terms', label: t('app.hr.employee_record.lifecycle.change_terms', { defaultValue: 'Change employment terms' }), onSelect: () => onOpen('zatrudnienie') },
    )
  }
  if (manage && overview.phase === 'active') {
    lifecycleItems.push(
      { id: 'terms', label: t('app.hr.employee_record.lifecycle.open_terms', { defaultValue: 'Open employment terms' }), onSelect: () => onOpen('zatrudnienie') },
      { id: 'end', label: t('app.hr.employee_record.lifecycle.end', { defaultValue: 'End employment' }), onSelect: () => setEndOpen(true), tone: 'danger' },
    )
  }
  if (overview.phase === 'returned' && surface.candidate_id) {
    lifecycleItems.push({
      id: 'recruitment',
      label: t('app.hr.employee_record.lifecycle.open_recruitment', { defaultValue: 'Open in recruitment' }),
      onSelect: () => onOpen('recruitment'),
    })
  }

  const stayLabel = overview.stay_basis && overview.stay_basis !== 'none'
    ? catalogLabel(t, overview.stay_basis) || t('app.hr.employee_record.context.known', { defaultValue: 'In place' })
    : '—'
  const workLabel = overview.work_status === 'eligible'
    ? t('app.hr.employee_record.context.known', { defaultValue: 'In place' })
    : overview.work_status === 'pending'
      ? t('app.hr.employee_record.context.open', { defaultValue: 'Open' })
      : '—'
  const zusLabel = formalities?.mark === 'completed'
    ? t('app.hr.employee_record.context.known', { defaultValue: 'In place' })
    : formalities?.mark === 'current' || formalities?.mark === 'blocked'
      ? t('app.hr.employee_record.context.open', { defaultValue: 'Open' })
      : '—'
  const contextLine = [
    citizenship ? `${countryFlag(overview.citizenship)} ${citizenship}`.trim() : null,
    `${t('app.hr.employee_record.context.stay', { defaultValue: 'Stay' })} ${stayLabel}`,
    `${t('app.hr.employee_record.context.work', { defaultValue: 'Right to work' })} ${overview.phase === 'returned' ? '—' : workLabel}`,
    overview.phase === 'returned'
      ? t('app.hr.employee_record.phase.ended', { defaultValue: 'Employment ended' })
      : `${t('app.hr.employee_record.context.contract', { defaultValue: 'Contract' })} ${contract}`,
    `${t('app.hr.employee_record.context.zus', { defaultValue: 'ZUS' })} ${zusLabel}`,
    medicalMark ? `${t('app.hr.employee_record.context.medical', { defaultValue: 'Medical' })} ${medicalMark}` : null,
    overview.phase === 'active' && overview.start_on
      ? t('app.hr.employee_record.context.since', { defaultValue: 'since {date}', values: { date: formatDay(overview.start_on) } })
      : null,
  ].filter((value): value is string => Boolean(value))
  const noticeTitle = action ? actionCopy(t, action.code, 'title') : ''
  const noticeReason = action ? actionCopy(t, action.code, 'reason') : ''

  return (
    <>
      <EntityRecordHeader
        compact
        title={surface.header.name || '—'}
        code={surface.person?.short_id || null}
        actions={
          <OverflowMenu
            label={t('app.hr.employee_record.lifecycle.menu', { defaultValue: 'Lifecycle actions' })}
            items={lifecycleItems}
            appearance="inverse"
          />
        }
        summary={
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-800">
            <span className="font-medium text-slate-900">
              {surface.header.employer || '—'}
              {surface.header.position ? (
                <>
                  <span className="mx-1.5 font-normal text-slate-400">/</span>
                  {surface.header.position}
                </>
              ) : null}
            </span>
            <span className="text-slate-300" aria-hidden>·</span>
            <span className="font-semibold text-brand-800">{phaseLabel}</span>
            <span className="text-slate-300" aria-hidden>·</span>
            <span className="min-w-0 text-slate-700">{contextLine.join(' · ')}</span>
            {noticeReason ? <span className="text-xs text-slate-600">{noticeReason}</span> : null}
            {noticeTitle && noticeTarget ? (
              <button type="button" className="text-xs font-medium text-brand-700 hover:underline" onClick={() => onOpen(noticeTarget)}>
                {noticeTitle}
              </button>
            ) : null}
          </div>
        }
        pipeline={overview.phase === 'preparing' ? (
          <StagePipeline
            ariaLabel={t('app.hr.employee_record.phase.preparing', { defaultValue: 'Preparing for employment' })}
            stages={path.map((step) => {
              const owns = ownsNextAction(step.id, action?.code, surface.current_process.target_row_id)
              const secondary = owns
                ? noticeTitle
                : step.mark === 'blocked'
                  ? t('app.hr.employee_record.mark.blocked', { defaultValue: 'Blocked' })
                  : step.mark === 'not_applicable'
                    ? t('app.hr.employee_record.mark.not_applicable', { defaultValue: 'Not applicable' })
                    : null
              return {
                code: step.id,
                label: pathTitle(t, step.id, step.target),
                mark: step.mark,
                secondary,
                onSelect: step.target ? () => onOpen(step.target) : null,
              }
            })}
          />
        ) : null}
      />

      <ReturnToRecruitmentModal
        employeeId={employeeId}
        open={returnOpen}
        onClose={() => setReturnOpen(false)}
        onCompleted={onReload}
      />
      <EndEmploymentModal
        employeeId={employeeId}
        open={endOpen}
        onClose={() => setEndOpen(false)}
        onCompleted={onReload}
      />
    </>
  )
}

function countryFlag(code: string | null): string {
  const normalized = String(code || '').trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(normalized)) return ''
  return String.fromCodePoint(...normalized.split('').map((letter) => 127397 + letter.charCodeAt(0)))
}

function FactSections({
  group,
  locale,
  onOpenDocuments,
}: {
  group?: HrEmployeeRecordGroup
  locale: 'en' | 'ru' | 'pl'
  onOpenDocuments: () => void
}) {
  const { t } = useI18n()
  if (!group) return null
  const buckets: { keys: string[] }[] = [
    { keys: ['driving_licence', 'code_95'] },
    { keys: ['tachograph_card'] },
  ]
  const used = new Set<string>()
  const sections = buckets
    .map((bucket) => {
      const rows = group.rows.filter((row) => bucket.keys.some((key) => row.id.endsWith(`.${key}`)))
      rows.forEach((row) => used.add(row.id))
      return rows
    })
    .filter((rows) => rows.length > 0)
  const rest = group.rows.filter((row) => !used.has(row.id))
  if (rest.length) sections.push(rest)
  if (!sections.length) return <p className="text-sm text-slate-500">{emptyCopy(t, group.empty)}</p>
  return (
    <div id={`record-group-${group.id}`}>
      {sections.map((rows) => (
        <GroupBody key={rows[0].id} group={{ ...group, rows }} locale={locale} onOpenDocuments={onOpenDocuments} />
      ))}
    </div>
  )
}

function RecordTasks({
  candidateId,
  candidateLabel,
  locked,
}: {
  candidateId: string | null
  candidateLabel: string
  locked: boolean
}) {
  const { t } = useI18n()
  const [items, setItems] = useState<ReminderRecord[]>([])
  const [adding, setAdding] = useState(false)

  const loadTasks = useCallback(async () => {
    if (!candidateId) {
      setItems([])
      return
    }
    try {
      const response = await listReminders({
        entityType: 'candidate',
        entityId: candidateId,
        status: ['pending', 'new', 'overdue'],
        limit: 5,
      })
      const rows = Array.isArray(response?.items) ? response.items : []
      setItems(rows)
    } catch {
      setItems([])
    }
  }, [candidateId])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  const tasksHref = `${CRM_APP_PATHS.tasks}?tab=tasks&t_status=active&t_entity=candidate&t_q=${encodeURIComponent(
    String(candidateLabel || candidateId || '').slice(0, 80),
  )}`

  return (
    <RailWidget title={`${t('app.hr.employee_record.tasks', { defaultValue: 'Tasks' })} ${items.length}`}>
      <div>
      {items.slice(0, 3).map((item) => (
        <p key={item.id}>
          {item.title || t('app.candidate_card.reminders.untitled', { defaultValue: 'Zadanie' })}
          {item.due_at ? ` · ${formatDay(item.due_at)}` : ''}
        </p>
      ))}
      {locked || !candidateId ? null : (
        <button type="button" className="btn-secondary btn-sm" onClick={() => setAdding(true)}>
          {t('app.hr.employee_record.add_task', { defaultValue: 'Dodaj' })}
        </button>
      )}
      <Link to={tasksHref} className="btn-secondary btn-sm">
        {t('app.hr.employee_record.show_history', { defaultValue: 'Pokaż wszystkie' })}
      </Link>
      {candidateId ? (
        <CandidateQuickTaskModal
          open={adding}
          onClose={() => {
            setAdding(false)
            void loadTasks()
          }}
          candidateId={candidateId}
          candidateLabel={candidateLabel}
          t={t}
        />
      ) : null}
      </div>
    </RailWidget>
  )
}

function RecordNotes({ candidateId, locked }: { candidateId: string; locked: boolean }) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [notes, setNotes] = useState<CandidateNote[]>([])
  const [loading, setLoading] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get<CandidateNote[]>(`/candidates/${candidateId}/notes`)
      setNotes(Array.isArray(data) ? data : [])
    } catch {
      setNotes([])
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void load()
  }, [load])

  const add = async () => {
    const text = draft.trim()
    if (!text || locked) return
    setSending(true)
    try {
      await api.post(`/candidates/${candidateId}/notes`, { text, visibility: 'internal' })
      setDraft('')
      await load()
      notify({ title: t('app.candidate_card.messages.note_added'), variant: 'success' })
    } catch {
      notify({ title: t('app.candidate_card.notes.save_failed'), variant: 'error' })
    } finally {
      setSending(false)
    }
  }

  return (
    <NotesRailWidget
      notes={notes}
      notesLoading={loading}
      newNote={draft}
      noteSending={sending}
      onNewNoteChange={setDraft}
      onAddNote={() => void add()}
      onRefreshNotes={() => void load()}
      readOnly={locked}
    />
  )
}

function RecordTimeline({ candidateId }: { candidateId: string }) {
  const { t, locale } = useI18n()
  const [stageHistory, setStageHistory] = useState<StageHistoryEntry[]>([])
  const [notes, setNotes] = useState<CandidateNote[]>([])
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [historyResult, notesResult, remindersResult] = await Promise.allSettled([
        api.get<Array<Record<string, unknown>>>(`/candidates/${candidateId}/stage-history`),
        api.get<CandidateNote[]>(`/candidates/${candidateId}/notes`),
        listReminders({
          entityType: 'candidate',
          entityId: candidateId,
          status: ['pending', 'new', 'overdue', 'done', 'cancelled'],
        }),
      ])
      if (historyResult.status === 'fulfilled') {
        const entries = Array.isArray(historyResult.value.data) ? historyResult.value.data : []
        setStageHistory(
          entries.map((item, index) => ({
            id: String(item.id ?? `${item.to_code ?? 'stage'}-${item.at ?? index}`),
            from_code: item.from_code ? String(item.from_code) : null,
            to_code: item.to_code ? String(item.to_code) : null,
            at: item.at ? String(item.at) : null,
            actor: item.actor ? String(item.actor) : item.actor_name ? String(item.actor_name) : null,
            reason: item.reason ? String(item.reason) : null,
          })),
        )
      }
      if (notesResult.status === 'fulfilled') {
        setNotes(Array.isArray(notesResult.value.data) ? notesResult.value.data : [])
      }
      if (remindersResult.status === 'fulfilled') {
        const items = remindersResult.value?.items
        setReminders(Array.isArray(items) ? items : [])
      }
      const failed = [historyResult, notesResult, remindersResult].find((result) => result.status === 'rejected')
      if (failed && failed.status === 'rejected') {
        setError(getFriendlyErrorInfo(failed.reason, t('app.candidate_card.notes.save_failed')))
      }
    } finally {
      setLoading(false)
    }
  }, [candidateId, t])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <ActivityRailWidget
      locale={locale}
      stageHistory={stageHistory}
      notes={notes}
      reminders={reminders}
      loading={loading}
      timelineError={error}
      resolveStageLabel={(code) => translateStageLabel(t, code, code)}
      onRequestLoad={() => void load()}
      defaultOpen
      includeStageChanges
      variant="info"
      collapsedCount={8}
    />
  )
}

function factCoverage(group: HrEmployeeRecordGroup): string | null {
  if (group.id !== 'kwalifikacje' && group.id !== 'badania') return null
  const applicable = group.rows.filter((row) => row.status !== 'not_applicable')
  if (applicable.length === 0) return null
  const confirmed = applicable.filter((row) => row.evidence === 'approved').length
  return `${confirmed}/${applicable.length}`
}

function resolutionBadgeStatus(status: string): RequirementRowStatus {
  if (status === 'satisfied') return 'approved'
  if (status === 'waived') return 'superseded'
  if (status === 'blocking') return 'rejected'
  if (status === 'not_applicable') return 'not_applicable'
  if (status === 'pending') return 'pending_review'
  return 'missing'
}

function resolutionLabel(t: Translate, status: string): string {
  return t(evidenceStatusLabelKey(resolutionBadgeStatus(status)), { defaultValue: '' })
}

function evidenceLinked(code: string | null): boolean {
  return Boolean(code && code !== 'missing' && code !== 'not_required')
}

function RequirementFactRow({
  row,
  locale,
  onOpenDocuments,
}: {
  row: HrEmployeeRecordRow
  locale: 'en' | 'ru' | 'pl'
  onOpenDocuments?: () => void
}) {
  const { t } = useI18n()
  const linked = evidenceLinked(row.evidence)
  return (
    <div id={`record-row-${row.id}`} data-testid="hr-requirement-row">
      <RequirementRowFrame label={row.label} status={resolutionBadgeStatus(row.status)}>
        <div className="pb-2 pl-0">
          {row.status === 'not_applicable' ? (
            <p className="mt-2 text-xs text-slate-500">
              {t('app.candidate_card.requirements_checklist.not_applicable_hint', {
                defaultValue: 'Not required for this candidate profile.',
              })}
            </p>
          ) : (
            <div className="mt-2 space-y-3">
              {(row.details || []).map((detail) => (
                <div key={detail.label} className="grid grid-cols-[8.5rem_minmax(0,1fr)] items-baseline gap-2 text-xs">
                  <div className="text-slate-500">{detail.label}</div>
                  <p className="font-medium text-slate-900">{displayValue(detail.value, detail.label, locale, t)}</p>
                </div>
              ))}
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                  {t('app.candidate_card.requirements_checklist.linked_documents', { defaultValue: 'Linked documents' })}
                </div>
                {linked ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm mt-1 flex w-full items-center justify-between gap-2 text-left"
                    onClick={onOpenDocuments}
                    disabled={!onOpenDocuments}
                  >
                    <span className="font-medium text-slate-900">{evidenceLabel(row.evidence, t)}</span>
                    <span className="text-[11px] text-slate-600">
                      {t('app.candidate_card.ia.legalization_open_document', { defaultValue: 'Open in Documents' })}
                    </span>
                  </button>
                ) : (
                  <div className="mt-1 space-y-2">
                    <p className="text-xs text-slate-600">
                      {t('app.candidate_card.requirements_checklist.no_linked_documents', {
                        defaultValue: 'No documents linked yet.',
                      })}
                    </p>
                    {onOpenDocuments ? (
                      <button type="button" className="text-xs font-medium text-brand-700 hover:underline" onClick={onOpenDocuments}>
                        {t('app.candidate_card.ia.legalization_open_document', { defaultValue: 'Open in Documents' })}
                      </button>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </RequirementRowFrame>
    </div>
  )
}

function GroupBody({
  group,
  locale,
  onOpenDocuments,
}: {
  group: HrEmployeeRecordGroup
  locale: 'en' | 'ru' | 'pl'
  onOpenDocuments?: () => void
}) {
  const { t } = useI18n()
  if (group.rows.length === 0) {
    return <p className="text-sm text-slate-500">{emptyCopy(t, group.empty)}</p>
  }
  if (group.id === 'kwalifikacje' || group.id === 'badania') {
    return (
      <div className="mt-1">
        {group.rows.map((row) => (
          <RequirementFactRow key={row.id} row={row} locale={locale} onOpenDocuments={onOpenDocuments} />
        ))}
      </div>
    )
  }
  return (
    <div className="mt-3 space-y-2">
      {group.rows.map((row) => {
        const status = HIDDEN_STATUS.has(row.status) ? '' : resolutionLabel(t, row.status)
        const evidence = row.evidence && !looksTechnical(row.evidence) ? catalogLabel(t, row.evidence) : ''
        return (
          <div key={row.id} id={`record-row-${row.id}`} className="flex items-baseline justify-between gap-6 py-1">
            <div className="text-sm text-slate-500">{row.label}</div>
            <p className="text-right text-sm font-medium text-slate-900">
              {meaningfulValue(row, locale, t)}
              {status ? <span className="ml-2 text-xs font-medium text-slate-500">{status}</span> : null}
              {evidence ? ` · ${evidence}` : ''}
            </p>
          </div>
        )
      })}
    </div>
  )
}

const EMPTY_ADDRESS: HrEmployeeRecordAddress = {
  country: '',
  city: '',
  street: '',
  house: '',
  apt: '',
  zip: '',
}

function addressDraft(value: HrEmployeeRecordAddress | string | null | undefined): HrEmployeeRecordAddress {
  if (value && typeof value === 'object') return { ...EMPTY_ADDRESS, ...value }
  if (typeof value === 'string' && value.trim()) return { ...EMPTY_ADDRESS, street: value.trim() }
  return { ...EMPTY_ADDRESS }
}

type PersonField =
  | 'first_name'
  | 'last_name'
  | 'birth_date'
  | 'citizenship'
  | 'pesel'
  | 'languages'
  | 'phone'
  | 'email'
  | 'preferred_contact'
  | 'address'
  | 'reg_address'

function personPayload(person: HrEmployeeRecordSurface['person']): HrEmployeeRecordPersonIn {
  return {
    first_name: person?.first_name || '',
    last_name: person?.last_name || '',
    birth_date: person?.birth_date || '',
    citizenship: person?.citizenship || '',
    phone: person?.phone || '',
    phone_country: person?.phone_country || '',
    email: person?.email || '',
    preferred_contact: person?.preferred_contact || '',
    address: addressDraft(person?.address),
    reg_address_diff: Boolean(person?.reg_address_diff),
    reg_address: addressDraft(person?.reg_address),
    pesel: person?.pesel || '',
    languages: person?.languages || '',
  }
}

function formatAddressLine(
  address: HrEmployeeRecordAddress,
  countryLabel: (code: string) => string,
): string {
  return [countryLabel(address.country), address.city, address.zip, address.street, address.house, address.apt]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(', ')
}

function PersonForm({
  employeeId,
  person,
  writable,
  onError,
  onSaved,
}: {
  employeeId: string
  person: HrEmployeeRecordSurface['person']
  writable: boolean
  onError: (message: string | null) => void
  onSaved: () => void
}) {
  const { t, locale } = useI18n()
  const countries = usePlatformCountryOptions(locale)
  const dialCodes = usePlatformDialCodeOptions()
  const languagesCatalog = useLanguageOptions(locale)
  const selectTexts = useMemo(
    () => ({
      empty: t('app.candidate_card.select.empty'),
      search: t('app.candidate_card.select.search'),
      noResults: t('app.candidate_card.select.no_results'),
      multiNone: t('app.candidate_card.select.multi_none'),
      multiSelected: (count: number) => t('app.candidate_card.select.multi_selected', { values: { count } }),
    }),
    [t],
  )
  const serverKey = JSON.stringify(personPayload(person))
  const personRef = useRef(person)
  personRef.current = person
  const [draft, setDraft] = useState<HrEmployeeRecordPersonIn>(() => personPayload(person))
  const [openField, setOpenField] = useState<PersonField | null>(null)
  const savingRef = useRef(false)
  useEffect(() => {
    setDraft(personPayload(personRef.current))
    setOpenField(null)
  }, [serverKey])
  const countryLabel = (code: string) => countries.find((item) => item.value === code)?.label || code
  const languageValues = draft.languages.split(',').map((part) => part.trim()).filter(Boolean)
  const languageLabel = languageValues
    .map((code) => languagesCatalog.find((item) => item.value === code)?.label || code)
    .join(', ')
  const dialLabel = dialCodes.find((item) => item.value === draft.phone_country)?.label || draft.phone_country
  const phoneLabel = [dialLabel, draft.phone].filter(Boolean).join(' ')
  const commit = async () => {
    if (!writable) {
      setOpenField(null)
      return
    }
    if (savingRef.current) return
    if (JSON.stringify(draft) === serverKey) {
      setOpenField(null)
      return
    }
    savingRef.current = true
    try {
      const result = await updateHrEmployeeRecordPerson(employeeId, draft)
      if (result.accepted === false) {
        onError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
        return
      }
      onError(null)
      setOpenField(null)
      onSaved()
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
    } finally {
      savingRef.current = false
    }
  }
  const setAddressPart = (key: keyof HrEmployeeRecordAddress, value: string) => {
    setDraft((current) => ({ ...current, address: { ...current.address, [key]: value } }))
  }
  const setRegPart = (key: keyof HrEmployeeRecordAddress, value: string) => {
    setDraft((current) => ({ ...current, reg_address: { ...current.reg_address, [key]: value } }))
  }
  return (
    <div className="space-y-3">
    <CardAccordion title={t('app.candidate_card.ia.sections.identity')} defaultOpen summary={[draft.first_name, draft.last_name].filter(Boolean).join(' ')}>
      <div>
      <InlineFieldRow
        label={t('app.candidate_card.fields.first_name')}
        value={draft.first_name}
        editing={openField === 'first_name'}
        canEdit={writable}
        onEdit={() => setOpenField('first_name')}
        onDone={() => void commit()}
      >
        <Input label={t('app.candidate_card.fields.first_name')} value={draft.first_name} onChange={(event) => setDraft((current) => ({ ...current, first_name: event.target.value }))} />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.last_name')}
        value={draft.last_name}
        editing={openField === 'last_name'}
        canEdit={writable}
        onEdit={() => setOpenField('last_name')}
        onDone={() => void commit()}
      >
        <Input label={t('app.candidate_card.fields.last_name')} value={draft.last_name} onChange={(event) => setDraft((current) => ({ ...current, last_name: event.target.value }))} />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.birth_date')}
        value={draft.birth_date ? formatDay(draft.birth_date) : ''}
        editing={openField === 'birth_date'}
        canEdit={writable}
        onEdit={() => setOpenField('birth_date')}
        onDone={() => void commit()}
      >
        <Input label={t('app.candidate_card.fields.birth_date')} type="date" value={draft.birth_date} onChange={(event) => setDraft((current) => ({ ...current, birth_date: event.target.value }))} />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.citizenship')}
        value={countryLabel(draft.citizenship)}
        editing={openField === 'citizenship'}
        canEdit={writable}
        onEdit={() => setOpenField('citizenship')}
        onDone={() => void commit()}
      >
        <div className="label">{t('app.candidate_card.fields.citizenship')}</div>
        <Combobox
          options={countries}
          value={draft.citizenship}
          onChange={(value) => setDraft((current) => ({ ...current, citizenship: value }))}
          placeholder={selectTexts.empty}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
        />
      </InlineFieldRow>
      <InlineFieldRow
        label="PESEL"
        value={draft.pesel}
        editing={openField === 'pesel'}
        canEdit={writable}
        onEdit={() => setOpenField('pesel')}
        onDone={() => void commit()}
      >
        <Input label="PESEL" value={draft.pesel} onChange={(event) => setDraft((current) => ({ ...current, pesel: event.target.value }))} />
      </InlineFieldRow>
      <InlineFieldRow label={t('app.candidate_card.fields.short_id')} value={person?.short_id || ''} editing={false} canEdit={false} onEdit={() => undefined} onDone={() => undefined}>
        <Input label={t('app.candidate_card.fields.short_id')} value={person?.short_id || ''} readOnly />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.languages')}
        value={languageLabel}
        editing={openField === 'languages'}
        canEdit={writable}
        onEdit={() => setOpenField('languages')}
        onDone={() => void commit()}
        wide
      >
        <div className="label">{t('app.candidate_card.fields.languages')}</div>
        <MultiCombobox
          options={languagesCatalog}
          values={languageValues}
          onChange={(values) => setDraft((current) => ({ ...current, languages: values.join(',') }))}
          placeholder={selectTexts.multiNone}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
          multiSelectedLabel={selectTexts.multiSelected}
        />
      </InlineFieldRow>
      </div>
    </CardAccordion>
    <CardAccordion title={t('app.candidate_card.ia.sections.contact')} summary={[draft.phone, draft.email].filter(Boolean).join(' · ')}>
      <div>
      <InlineFieldRow
        label={t('app.candidate_card.fields.phone')}
        value={phoneLabel}
        editing={openField === 'phone'}
        canEdit={writable}
        onEdit={() => setOpenField('phone')}
        onDone={() => void commit()}
        wide
      >
        <div className="label">{t('app.candidate_card.fields.phone')}</div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
          <div className="sm:w-56">
            <Combobox
              options={dialCodes}
              value={draft.phone_country}
              onChange={(value) => setDraft((current) => ({ ...current, phone_country: value }))}
              placeholder={selectTexts.empty}
              searchPlaceholder={selectTexts.search}
              noResultsLabel={selectTexts.noResults}
            />
          </div>
          <div className="min-w-0 flex-1">
            <Input value={draft.phone} onChange={(event) => setDraft((current) => ({ ...current, phone: event.target.value }))} />
          </div>
        </div>
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.email')}
        value={draft.email}
        editing={openField === 'email'}
        canEdit={writable}
        onEdit={() => setOpenField('email')}
        onDone={() => void commit()}
      >
        <Input label={t('app.candidate_card.fields.email')} value={draft.email} onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))} />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.fields.preferred_contact')}
        value={t(`app.candidate_card.contacts.options.${draft.preferred_contact || 'none'}`)}
        editing={openField === 'preferred_contact'}
        canEdit={writable}
        onEdit={() => setOpenField('preferred_contact')}
        onDone={() => void commit()}
      >
        <div className="label">{t('app.candidate_card.fields.preferred_contact')}</div>
        <select className="input" value={draft.preferred_contact} onChange={(event) => setDraft((current) => ({ ...current, preferred_contact: event.target.value }))}>
          {PREFERRED_CONTACT_VALUES.map((value) => (
            <option key={value || 'none'} value={value}>
              {t(`app.candidate_card.contacts.options.${value || 'none'}`)}
            </option>
          ))}
        </select>
      </InlineFieldRow>
      </div>
    </CardAccordion>
    <CardAccordion title={t('app.candidate_card.ia.sections.address')} summary={formatAddressLine(draft.address, countryLabel)}>
      <div>
      <InlineFieldRow
        label={t('app.candidate_card.sections.personal.address_current')}
        value={formatAddressLine(draft.address, countryLabel)}
        editing={openField === 'address'}
        canEdit={writable}
        onEdit={() => setOpenField('address')}
        onDone={() => void commit()}
        wide
      >
        <AddressEditor address={draft.address} countries={countries} selectTexts={selectTexts} onChange={setAddressPart} t={t} />
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.sections.personal.address_registered')}
        value={draft.reg_address_diff ? formatAddressLine(draft.reg_address, countryLabel) : t('app.candidate_card.ia.same_as_residence', { defaultValue: 'Same as the residence address' })}
        editing={openField === 'reg_address'}
        canEdit={writable}
        onEdit={() => setOpenField('reg_address')}
        onDone={() => void commit()}
        wide
      >
        <Checkbox
          label={t('app.candidate_card.fields.address.diff')}
          checked={draft.reg_address_diff}
          onChange={(value) => setDraft((current) => ({ ...current, reg_address_diff: value }))}
        />
        {draft.reg_address_diff ? (
          <div className="mt-3">
            <AddressEditor address={draft.reg_address} countries={countries} selectTexts={selectTexts} onChange={setRegPart} t={t} />
          </div>
        ) : null}
      </InlineFieldRow>
      </div>
    </CardAccordion>
    </div>
  )
}

function AddressEditor({
  address,
  countries,
  selectTexts,
  onChange,
  t,
}: {
  address: HrEmployeeRecordAddress
  countries: { value: string; label: string }[]
  selectTexts: { empty: string; search: string; noResults: string }
  onChange: (key: keyof HrEmployeeRecordAddress, value: string) => void
  t: Translate
}) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <label className="block md:col-span-2">
        <div className="label">{t('app.candidate_card.fields.address.country')}</div>
        <Combobox
          options={countries}
          value={address.country}
          onChange={(value) => onChange('country', value)}
          placeholder={selectTexts.empty}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
        />
      </label>
      <Input label={t('app.candidate_card.fields.address.city')} value={address.city} onChange={(event) => onChange('city', event.target.value)} />
      <Input label={t('app.candidate_card.fields.address.zip')} value={address.zip} onChange={(event) => onChange('zip', event.target.value)} />
      <div className="md:col-span-2">
        <Input label={t('app.candidate_card.fields.address.street')} value={address.street} onChange={(event) => onChange('street', event.target.value)} />
      </div>
      <Input label={t('app.candidate_card.fields.address.house')} value={address.house} onChange={(event) => onChange('house', event.target.value)} />
      <Input label={t('app.candidate_card.fields.address.apt')} value={address.apt} onChange={(event) => onChange('apt', event.target.value)} />
    </div>
  )
}

type LegalField = 'citizenship_class' | 'stay_basis' | 'work_authorization_basis' | 'valid_for_this_employment'

function legalPayload(legal: HrEmployeeRecordSurface['legal']): HrDriverLegalIn {
  return {
    citizenship_class: legal?.citizenship_class || '',
    stay_basis: legal?.stay_basis || '',
    work_authorization_basis: legal?.work_authorization_basis || '',
    valid_for_this_employment: legal?.valid_for_this_employment || '',
  }
}

function chainOptionLabel(t: Translate, value: string): string {
  return catalogLabel(t, value)
}

function LegalForm({
  employeeId,
  candidateId,
  contextLabel,
  group,
  legal,
  writable,
  onOpenDocuments,
  onError,
  onSaved,
}: {
  employeeId: string
  candidateId: string | null
  contextLabel: string
  group: HrEmployeeRecordGroup
  legal: HrEmployeeRecordSurface['legal']
  writable: boolean
  onOpenDocuments: () => void
  onError: (message: string | null) => void
  onSaved: () => void
}) {
  const { t, locale } = useI18n()
  const countries = usePlatformCountryOptions(locale)
  const serverKey = JSON.stringify(legalPayload(legal))
  const legalRef = useRef(legal)
  legalRef.current = legal
  const [draft, setDraft] = useState<HrDriverLegalIn>(() => legalPayload(legal))
  const [openField, setOpenField] = useState<LegalField | null>(null)
  const [confirming, setConfirming] = useState(false)
  useEffect(() => {
    setDraft(legalPayload(legalRef.current))
    setOpenField(null)
  }, [serverKey])
  const dirty = JSON.stringify(draft) !== serverKey
  const closeField = () => setOpenField(null)
  const labelOf = (value: string) => chainOptionLabel(t, value)
  const confirmReading = async () => {
    if (!writable || openField !== null || !dirty || confirming) return
    setConfirming(true)
    try {
      const result = await confirmHrDriverLegal(employeeId, draft)
      if (result.accepted === false) {
        onError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
        return
      }
      onError(null)
      onSaved()
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
    } finally {
      setConfirming(false)
    }
  }
  const statusRows = group.rows.filter((row) => row.id === 'legalizacja.status')
  return (
    <div className="space-y-3">
      {candidateId ? (
        <OperatorFactsSurface
          candidateId={candidateId}
          countries={countries}
          region="legalization"
          contextLabel={contextLabel}
          onOpenDocuments={onOpenDocuments}
        />
      ) : null}
      <CardAccordion title={t('app.hr.employee_record.legal_chain', { defaultValue: 'Eligibility for this employment' })} defaultOpen>
      <div>
        <InlineFieldRow
          label={t('app.candidate_card.fields.citizenship')}
          value={labelOf(draft.citizenship_class)}
          editing={openField === 'citizenship_class'}
          canEdit={writable}
          onEdit={() => setOpenField('citizenship_class')}
          onDone={closeField}
        >
          <CatalogSelect
            label={t('app.candidate_card.fields.citizenship')}
            value={draft.citizenship_class}
            options={['pl', 'eu_eea_ch', 'third_country']}
            onChange={(value) => setDraft((current) => ({ ...current, citizenship_class: value }))}
            labelFor={labelOf}
            t={t}
          />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'legalizacja.stay_basis', t('app.candidate_card.fields.poland_basis'))}
          value={labelOf(draft.stay_basis)}
          editing={openField === 'stay_basis'}
          canEdit={writable}
          onEdit={() => setOpenField('stay_basis')}
          onDone={closeField}
        >
          <CatalogSelect
            label={rowLabel(group, 'legalizacja.stay_basis', t('app.candidate_card.fields.poland_basis'))}
            value={draft.stay_basis}
            options={['not_required', 'visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none']}
            onChange={(value) => setDraft((current) => ({ ...current, stay_basis: value }))}
            labelFor={labelOf}
            t={t}
          />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'legalizacja.work_basis', t('app.candidate_card.fields.residency_status'))}
          value={labelOf(draft.work_authorization_basis)}
          editing={openField === 'work_authorization_basis'}
          canEdit={writable}
          onEdit={() => setOpenField('work_authorization_basis')}
          onDone={closeField}
        >
          <CatalogSelect
            label={rowLabel(group, 'legalizacja.work_basis', t('app.candidate_card.fields.residency_status'))}
            value={draft.work_authorization_basis}
            options={['not_required', 'included_in_stay', 'separate_required']}
            onChange={(value) => setDraft((current) => ({ ...current, work_authorization_basis: value }))}
            labelFor={labelOf}
            t={t}
          />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'legalizacja.valid_for_this_employment', t('common.labels.status'))}
          value={labelOf(draft.valid_for_this_employment)}
          editing={openField === 'valid_for_this_employment'}
          canEdit={writable}
          onEdit={() => setOpenField('valid_for_this_employment')}
          onDone={closeField}
        >
          <CatalogSelect
            label={rowLabel(group, 'legalizacja.valid_for_this_employment', t('common.labels.status'))}
            value={draft.valid_for_this_employment}
            options={['yes', 'no', 'operator_verification']}
            onChange={(value) => setDraft((current) => ({ ...current, valid_for_this_employment: value }))}
            labelFor={labelOf}
            t={t}
          />
        </InlineFieldRow>
      </div>
      <GroupBody group={{ ...group, rows: statusRows }} locale={locale} />
      {writable && dirty ? (
        <Button variant="primary" size="sm" disabled={confirming || openField !== null} onClick={() => void confirmReading()}>
          {confirming
            ? t('common.saving', { defaultValue: 'Saving…' })
            : t('app.hr.employee_record.confirm_legal', { defaultValue: 'Confirm legal eligibility' })}
        </Button>
      ) : null}
      </CardAccordion>
    </div>
  )
}

type TermsField =
  | 'position'
  | 'contract_basis'
  | 'workplace'
  | 'work_time'
  | 'work_system'
  | 'compensation'
  | 'duration'
  | 'probation'
  | 'planned_start'

function termsPayload(terms: HrEmployeeRecordSurface['terms']): HrDriverTermsIn {
  const duration = terms?.duration || ''
  const probation = terms?.probation_status || ''
  return {
    position: terms?.position || '',
    contract_basis: terms?.contract_basis || '',
    work_time_value: terms?.work_time_value || '',
    work_time_unit: terms?.work_time_unit || '',
    work_system: terms?.work_system || '',
    workplace: terms?.workplace || '',
    compensation_amount: terms?.compensation_amount || '',
    compensation_currency: terms?.compensation_currency || '',
    compensation_unit: terms?.compensation_unit || '',
    duration,
    fixed_term_end: duration === 'fixed' ? terms?.fixed_term_end || null : null,
    probation_status: probation,
    probation_end: probation === 'dated' ? terms?.probation_end || null : null,
    intended_start_date: terms?.intended_start_date || '',
  }
}

function TermsForm({
  employeeId,
  group,
  terms,
  writable,
  onError,
  onSaved,
}: {
  employeeId: string
  group: HrEmployeeRecordGroup
  terms: HrEmployeeRecordSurface['terms']
  writable: boolean
  onError: (message: string | null) => void
  onSaved: () => void
}) {
  const { t } = useI18n()
  const serverKey = JSON.stringify(termsPayload(terms))
  const termsRef = useRef(terms)
  termsRef.current = terms
  const [draft, setDraft] = useState<HrDriverTermsIn>(() => termsPayload(terms))
  const [openField, setOpenField] = useState<TermsField | null>(null)
  const [confirming, setConfirming] = useState(false)
  useEffect(() => {
    setDraft(termsPayload(termsRef.current))
    setOpenField(null)
  }, [serverKey])
  const dirty = JSON.stringify(draft) !== serverKey
  const optionLabel = (value: string) => catalogLabel(t, value)
  const closeField = () => setOpenField(null)
  const confirmSnapshot = async () => {
    if (!writable || openField !== null || !dirty || confirming) return
    setConfirming(true)
    try {
      const result = await confirmHrDriverTerms(employeeId, draft)
      if (result.accepted === false) {
        onError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
        return
      }
      onError(null)
      onSaved()
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
    } finally {
      setConfirming(false)
    }
  }
  const employer = rowById([group], 'zatrudnienie.employer')?.value || ''
  const actualStart = rowById([group], 'zatrudnienie.actual_start')?.value || ''
  const workTimeLabel = [draft.work_time_value, draft.work_time_unit].filter(Boolean).join(' ')
  const compensationLabel = [draft.compensation_amount, draft.compensation_currency, draft.compensation_unit].filter(Boolean).join(' ')
  const durationLabel = [
    optionLabel(draft.duration),
    draft.duration === 'fixed' && draft.fixed_term_end ? formatDay(draft.fixed_term_end) : '',
  ].filter(Boolean).join(' · ')
  const probationLabel = [
    optionLabel(draft.probation_status),
    draft.probation_status === 'dated' && draft.probation_end ? formatDay(draft.probation_end) : '',
  ].filter(Boolean).join(' · ')
  return (
    <div>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.employer', t('app.candidate_card.employment.columns.employer', { defaultValue: 'Employer' }))}
          value={employer}
          editing={false}
          canEdit={false}
          onEdit={() => undefined}
          onDone={() => undefined}
        >
          <span />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.position', t('app.candidate_card.employment.placeholders.position'))}
          value={draft.position}
          editing={openField === 'position'}
          canEdit={writable}
          onEdit={() => setOpenField('position')}
          onDone={closeField}
        >
          <Input label={rowLabel(group, 'zatrudnienie.position', t('app.candidate_card.employment.placeholders.position'))} value={draft.position} onChange={(event) => setDraft((current) => ({ ...current, position: event.target.value }))} />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.contract_basis', t('app.candidate_card.employment.columns.position'))}
          value={draft.contract_basis}
          editing={openField === 'contract_basis'}
          canEdit={writable}
          onEdit={() => setOpenField('contract_basis')}
          onDone={closeField}
        >
          <Input label={rowLabel(group, 'zatrudnienie.contract_basis', t('app.candidate_card.employment.columns.position'))} value={draft.contract_basis} onChange={(event) => setDraft((current) => ({ ...current, contract_basis: event.target.value }))} />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.workplace', t('app.candidate_card.fields.address.city'))}
          value={draft.workplace}
          editing={openField === 'workplace'}
          canEdit={writable}
          onEdit={() => setOpenField('workplace')}
          onDone={closeField}
        >
          <Input label={rowLabel(group, 'zatrudnienie.workplace', t('app.candidate_card.fields.address.city'))} value={draft.workplace} onChange={(event) => setDraft((current) => ({ ...current, workplace: event.target.value }))} />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))}
          value={workTimeLabel}
          editing={openField === 'work_time'}
          canEdit={writable}
          onEdit={() => setOpenField('work_time')}
          onDone={closeField}
          wide
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={draft.work_time_value} onChange={(event) => setDraft((current) => ({ ...current, work_time_value: event.target.value }))} />
            <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={draft.work_time_unit} onChange={(event) => setDraft((current) => ({ ...current, work_time_unit: event.target.value }))} />
          </div>
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.work_system', t('public.company_intake.fields.work_system'))}
          value={draft.work_system}
          editing={openField === 'work_system'}
          canEdit={writable}
          onEdit={() => setOpenField('work_system')}
          onDone={closeField}
        >
          <Input label={rowLabel(group, 'zatrudnienie.work_system', t('public.company_intake.fields.work_system'))} value={draft.work_system} onChange={(event) => setDraft((current) => ({ ...current, work_system: event.target.value }))} />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.compensation', t('app.hr.employee_detail.payroll_base_rate'))}
          value={compensationLabel}
          editing={openField === 'compensation'}
          canEdit={writable}
          onEdit={() => setOpenField('compensation')}
          onDone={closeField}
          wide
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Input label={rowLabel(group, 'zatrudnienie.compensation', t('app.hr.employee_detail.payroll_base_rate'))} value={draft.compensation_amount} onChange={(event) => setDraft((current) => ({ ...current, compensation_amount: event.target.value }))} />
            <Input label={t('app.hr.employee_detail.payroll_currency')} value={draft.compensation_currency} onChange={(event) => setDraft((current) => ({ ...current, compensation_currency: event.target.value }))} />
            <Input label={t('app.hr.employee_detail.payroll_pay_type')} value={draft.compensation_unit} onChange={(event) => setDraft((current) => ({ ...current, compensation_unit: event.target.value }))} />
          </div>
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.duration', t('app.candidate_card.employment.columns.end'))}
          value={durationLabel}
          editing={openField === 'duration'}
          canEdit={writable}
          onEdit={() => setOpenField('duration')}
          onDone={closeField}
          wide
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <CatalogSelect
              label={rowLabel(group, 'zatrudnienie.duration', t('app.candidate_card.employment.columns.end'))}
              value={draft.duration}
              options={['indefinite', 'fixed']}
              onChange={(value) => setDraft((current) => ({
                ...current,
                duration: value,
                fixed_term_end: value === 'fixed' ? current.fixed_term_end : null,
              }))}
              t={t}
            />
            {draft.duration === 'fixed' ? (
              <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={draft.fixed_term_end || ''} onChange={(event) => setDraft((current) => ({ ...current, fixed_term_end: event.target.value || null }))} />
            ) : null}
          </div>
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.probation', t('app.hr.employee_detail.workforce_journey.contract'))}
          value={probationLabel}
          editing={openField === 'probation'}
          canEdit={writable}
          onEdit={() => setOpenField('probation')}
          onDone={closeField}
          wide
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <CatalogSelect
              label={rowLabel(group, 'zatrudnienie.probation', t('app.hr.employee_detail.workforce_journey.contract'))}
              value={draft.probation_status}
              options={['none', 'dated']}
              onChange={(value) => setDraft((current) => ({
                ...current,
                probation_status: value,
                probation_end: value === 'dated' ? current.probation_end : null,
              }))}
              t={t}
            />
            {draft.probation_status === 'dated' ? (
              <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={draft.probation_end || ''} onChange={(event) => setDraft((current) => ({ ...current, probation_end: event.target.value || null }))} />
            ) : null}
          </div>
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.planned_start', t('app.candidate_card.employment.columns.start'))}
          value={draft.intended_start_date ? formatDay(draft.intended_start_date) : ''}
          editing={openField === 'planned_start'}
          canEdit={writable}
          onEdit={() => setOpenField('planned_start')}
          onDone={closeField}
        >
          <Input label={rowLabel(group, 'zatrudnienie.planned_start', t('app.candidate_card.employment.columns.start'))} type="date" value={draft.intended_start_date} onChange={(event) => setDraft((current) => ({ ...current, intended_start_date: event.target.value }))} />
        </InlineFieldRow>
        <InlineFieldRow
          label={rowLabel(group, 'zatrudnienie.actual_start', t('app.candidate_card.employment.columns.start'))}
          value={actualStart ? formatDay(actualStart) : ''}
          editing={false}
          canEdit={false}
          onEdit={() => undefined}
          onDone={() => undefined}
        >
          <span />
        </InlineFieldRow>
      {writable && dirty ? (
        <Button variant="primary" size="sm" disabled={confirming || openField !== null} onClick={() => void confirmSnapshot()}>
          {confirming
            ? t('common.saving', { defaultValue: 'Saving…' })
            : t('app.hr.employee_record.confirm_terms', { defaultValue: 'Confirm employment terms' })}
        </Button>
      ) : null}
    </div>
  )
}

function rowLabel(_group: HrEmployeeRecordGroup, _id: string, fallback: string): string {
  return fallback
}

function CatalogSelect({
  label,
  value,
  options,
  onChange,
  disabled,
  labelFor,
  t,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
  disabled?: boolean
  labelFor?: (value: string) => string
  t: Translate
}) {
  return (
    <label className="block">
      <div className="label">{label}</div>
      <Combobox
        value={value}
        disabled={disabled}
        options={options.map((option) => ({
          value: option,
          label: (labelFor ? labelFor(option) : knownOptionLabel(t, option)) || option,
        }))}
        onChange={onChange}
      />
    </label>
  )
}

function useLanguageOptions(locale: 'en' | 'ru' | 'pl') {
  const [options, setOptions] = useState<{ value: string; label: string }[]>([])
  useEffect(() => {
    let cancelled = false
    void api
      .get('/catalogs/languages')
      .then((response) => {
        const rows = Array.isArray(response.data) ? response.data : []
        const next = rows
          .map((row: { code?: string; id?: string }) => {
            const code = String(row.code ?? row.id ?? '')
            return { value: code, label: getLanguageDisplayName(code, locale) || code }
          })
          .filter((option) => option.value && option.label)
          .sort((left, right) => left.label.localeCompare(right.label, locale))
        if (!cancelled) setOptions(next)
      })
      .catch(() => {
        if (!cancelled) setOptions([])
      })
    return () => {
      cancelled = true
    }
  }, [locale])
  return options
}

function evidenceLabel(code: string | null, t: (key: string, options?: { defaultValue?: string }) => string): string {
  if (code === 'not_required') {
    return t('app.hr.work_eligibility.status.not_required', { defaultValue: 'Not required' })
  }
  const key = `admin.documents.status_labels.${code || 'missing'}`
  const label = t(key, { defaultValue: '' })
  return label && label !== key ? label : t('admin.documents.status_labels.missing', { defaultValue: 'Missing' })
}

function CompactGroup({
  group,
  locale,
  documents,
}: {
  group: HrEmployeeRecordGroup
  locale: 'en' | 'ru' | 'pl'
  documents?: { total: number; attention: number }
}) {
  const { t } = useI18n()
  const filled = group.rows.filter((row) => displayValue(row.value, row.label, locale, t) !== '—')
  if (group.id === 'dokumenty') {
    const total = documents?.total ?? 0
    const attention = documents?.attention ?? 0
    return (
      <>
        <p className="text-sm text-slate-700">
          {t('app.hr.employee_record.documents_count', { defaultValue: '{count} documents', values: { count: total } })}
          {attention > 0 ? ` · ${t('app.hr.employee_record.documents_attention', { defaultValue: '{count} need attention', values: { count: attention } })}` : ''}
        </p>
        <Link to={CRM_APP_PATHS.documents} className="btn-secondary btn-sm">
          {t('app.candidate_card.ia.open_documents', { defaultValue: 'Open documents' })}
        </Link>
      </>
    )
  }
  if (group.id === 'formalnosci') {
    const zus = group.rows.find((row) => row.id === 'formalnosci.zus')
    return (
      <>
        <p className="text-sm text-slate-700">{zus ? meaningfulValue(zus, locale, t) : emptyCopy(t, group.empty)}</p>
        <Link to={CRM_APP_PATHS.hrZusWorkspace} className="btn-secondary btn-sm">
          {t('app.hr.employee_record.formalities_open', { defaultValue: 'Open ZUS' })}
        </Link>
      </>
    )
  }
  if (filled.length === 0) {
    return <p className="text-sm text-slate-500">{emptyCopy(t, group.empty)}</p>
  }
  return (
    <>
      {filled.map((row) => (
        <p key={row.id} id={`record-row-${row.id}`} className="text-sm text-slate-700">
          {row.label}: {meaningfulValue(row, locale, t)}
        </p>
      ))}
    </>
  )
}
