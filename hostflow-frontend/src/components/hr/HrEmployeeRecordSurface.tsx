import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
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
import { Input, Checkbox, CheckboxMultiSelect, SearchableSelect } from '../candidate/shared/FormComponents'
import { useI18n } from '../../i18n'
import { usePlatformCountryOptions, usePlatformDialCodeOptions } from '../../hooks/usePlatformCatalogOptions'
import { PREFERRED_CONTACT_VALUES } from '../../data/preferredContactChannels'
import CandidateDocuments from '../../modules/documents/CandidateDocuments'
import { CandidateQuickTaskModal } from '../../modules/candidates/components/CandidateQuickTaskModal'
import CandidateNotesRailSection from '../candidate/CandidateNotesRailSection'
import CandidateTimelinePanel from '../candidate/CandidateTimelinePanel'
import type { CandidateNote, StageHistoryEntry } from '../../modules/candidate-card/types'
import { translateStageLabel } from '../../utils/stageLabels'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { useToast } from '../Toast'
import { StatusBadge } from '../ui/StatusBadge'
import { ActionMenu, type ActionMenuItem } from '../ui/ActionMenu'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Chip } from '../ui/Chip'
import { ProgressStepper } from '../ui/ProgressStepper'
import { documentSeverityToSemantic, type StatusBadgeSemantic } from '../ui/statusBadgeSemantics'
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
  return key ? t(key) : null
}

function displayValue(value: string | null, label: string, locale: 'en' | 'ru' | 'pl', t?: Translate): string {
  if (!value) return '—'
  if (looksTechnical(value)) return '—'
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return formatDay(value)
  if (t) {
    const mapped = knownOptionLabel(t, value)
    if (mapped) return mapped
  }
  if (value.trim().length === 2 && (label === 'Obywatelstwo' || label === 'Citizenship')) {
    return getRegionDisplayName(value, locale)
  }
  return value
}

function displayStatus(status: string): string | null {
  if (HIDDEN_STATUS.has(status)) return null
  if (status === 'not_applicable') return 'Not required'
  if (status === 'satisfied') return 'Verified'
  if (status === 'unresolved') return 'To verify'
  if (status === 'pending') return 'Pending'
  if (status === 'blocking') return 'Blocking'
  if (status === 'waived') return 'Waived'
  if (status === 'current') return 'Current'
  return null
}

const EMPTY_ROW: Record<string, string> = {
  'dane_osobowe.birth_date': 'Data urodzenia nieuzupełniona',
  'dane_osobowe.citizenship': 'Obywatelstwo nieustalone',
  'dane_osobowe.phone': 'Brak telefonu',
  'dane_osobowe.email': 'Brak adresu e-mail',
  'dane_osobowe.address': 'Adres nieuzupełniony',
  'dane_osobowe.pesel': 'PESEL nieuzupełniony',
  'legalizacja.stay_basis': 'Brak danych o podstawie pobytu',
  'legalizacja.work_basis': 'Prawo do pracy nieustalone',
  'legalizacja.valid_for_this_employment': 'Ważność dla tego zatrudnienia nieustalona',
}

const EMPTY_GROUP: Record<string, string> = {
  dane_osobowe: 'Brak danych osobowych',
  legalizacja: 'Brak danych o legalizacji',
  kwalifikacje: 'Brak zarejestrowanych uprawnień',
  badania: 'Brak zarejestrowanych badań',
  zatrudnienie: 'Brak danych o zatrudnieniu',
  formalnosci: 'Brak formalności do wykonania',
  dokumenty: 'Brak dokumentów',
  historia: 'Brak zdarzeń',
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

function meaningfulValue(row: HrEmployeeRecordRow, locale: 'en' | 'ru' | 'pl'): string {
  const shown = displayValue(row.value, row.label, locale)
  if (shown !== '—') return shown
  return EMPTY_ROW[row.id] || 'Nieuzupełnione'
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
  }, [employeeId])

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

  return (
    <div className="min-w-0 space-y-4">
      <EmployeeHero
        employeeId={employeeId}
        surface={surface}
        locale={locale}
        manage={manage}
        onOpen={openPath}
        onReload={load}
      />
      {error ? <p className="alert-error">{error}</p> : null}
      <div className="card min-w-0 p-3">
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-4 lg:pr-6">

          <div className="tabs flex-wrap gap-x-1 gap-y-0" role="tablist">
            {RECORD_TABS.map((id) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                className={clsx('tab cursor-pointer border-0 bg-transparent', tab === id && 'tab-active')}
                onClick={() => setTab(id)}
              >
                {activeGroup(id)?.label || id}
              </button>
            ))}
          </div>

          <section id={`record-group-${tab}`} className="app-surface p-4">
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
                group={activeGroup('legalizacja')!}
                legal={surface.legal}
                writable={canEdit && surface.state === 'preparing'}
                onError={setError}
                onSaved={() => {
                  void load()
                }}
              />
            ) : null}
            {tab === 'kwalifikacje' ? (
              <div className="space-y-6">
                <FactSections group={activeGroup('kwalifikacje')} locale={locale} approvedLabel={t('admin.documents.status_labels.approved', { defaultValue: 'Approved' })} />
                {activeGroup('badania') ? (
                  <div id="record-group-badania">
                    <h3>
                      {activeGroup('badania')!.label}
                      {factCoverage(activeGroup('badania'))
                        ? ` · ${factCoverage(activeGroup('badania'))} ${t('admin.documents.status_labels.approved', { defaultValue: 'Approved' })}`
                        : ''}
                    </h3>
                    <GroupBody group={activeGroup('badania')!} locale={locale} />
                  </div>
                ) : null}
              </div>
            ) : null}
            {tab === 'zatrudnienie' && activeGroup('zatrudnienie') ? (
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
            ) : null}
            {tab === 'formalnosci' && activeGroup('formalnosci') ? (
              <CompactGroup group={activeGroup('formalnosci')!} locale={locale} documents={surface.documents} />
            ) : null}
            {tab === 'dokumenty' && surface.candidate_id ? (
              <CandidateDocuments candidateId={surface.candidate_id} hideHeader onDocumentsChanged={() => void load()} />
            ) : null}
          </section>
        </div>

        <aside
          id="hr-verification"
          data-candidate-control-rail
          className="flex w-full min-w-0 flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-3.5rem)] lg:overflow-y-auto"
        >
          <RecordTasks
            candidateId={surface.candidate_id}
            candidateLabel={surface.header.name}
            locked={returned}
          />
          {surface.candidate_id ? (
            <RecordNotes candidateId={surface.candidate_id} locked={returned} />
          ) : null}
          {surface.candidate_id ? <RecordTimeline candidateId={surface.candidate_id} /> : null}
        </aside>
      </div>
      </div>
    </div>
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
  const phaseLabel = t(`app.hr.employee_record.status.${overview.phase}`, {
    defaultValue:
      overview.phase === 'active'
        ? 'Zatrudniony · Aktywny'
        : overview.phase === 'preparing'
          ? 'Przygotowanie do zatrudnienia'
          : overview.phase === 'returned'
            ? 'Wrócił do rekrutacji'
            : overview.phase === 'ended'
              ? 'Zatrudnienie zakończone'
              : overview.phase,
  })
  const semantic: StatusBadgeSemantic = overview.phase === 'active'
    ? 'ok'
    : overview.phase === 'preparing'
      ? 'warning'
      : overview.phase === 'returned'
        ? 'info'
        : 'neutral'
  const citizenship = overview.citizenship ? getRegionDisplayName(overview.citizenship, locale) : ''
  const contractRow = rowById(groups, 'zatrudnienie.contract_basis')
  const contract = contractRow ? displayValue(overview.contract_basis, contractRow.label, locale, t) : displayValue(overview.contract_basis, '', locale, t)
  const role = [surface.header.position, surface.header.employer].filter(Boolean).join(' · ')
  const formalities = path.find((step) => step.id === 'formalities')
  const medicalRows = groupById(groups, 'badania')?.rows || []
  const medicalMark = medicalRows.length === 0
    ? null
    : medicalRows.every((row) => row.status === 'satisfied' || row.status === 'not_applicable')
      ? '✓'
      : medicalRows.some((row) => row.status === 'blocking' || row.status === 'pending')
        ? '⚠'
        : '—'
  const action = surface.current_process.next_action
  const actionTarget = overview.notice_target || surface.current_process.target_row_id
  const actionLabel = actionTarget === 'legalizacja'
    ? 'Otwórz legalizację'
    : actionTarget === 'zatrudnienie'
      ? 'Otwórz warunki'
      : actionTarget === 'formalnosci'
        ? 'Otwórz formalności'
        : 'Otwórz'
  const lifecycleItems: ActionMenuItem[] = []
  if (manage && overview.phase === 'preparing') {
    lifecycleItems.push(
      { id: 'return', label: 'Wróć do rekrutacji', onSelect: () => setReturnOpen(true) },
      { id: 'terms', label: 'Zmień warunki Employment', onSelect: () => onOpen('zatrudnienie') },
    )
  }
  if (manage && overview.phase === 'active') {
    lifecycleItems.push(
      { id: 'terms', label: 'Otwórz warunki Employment', onSelect: () => onOpen('zatrudnienie') },
      { id: 'end', label: 'Zakończ zatrudnienie', danger: true, onSelect: () => setEndOpen(true) },
    )
  }
  if (overview.phase === 'returned' && surface.candidate_id) {
    lifecycleItems.push({ id: 'recruitment', label: 'Otwórz sprawę w Recruitment', onSelect: () => onOpen('recruitment') })
  }

  const progressPosition = Math.min(
    path.length,
    path.filter((step) => step.mark === 'completed').length + (path.some((step) => step.mark === 'current' || step.mark === 'blocked') ? 1 : 0),
  )

  const standardDomainChips = [
    citizenship
      ? `${countryFlag(overview.citizenship)} ${citizenship}`.trim()
      : null,
    `Pobyt ${overview.stay_basis && overview.stay_basis !== 'none' ? '✓' : '—'}${overview.stay_until ? ` ${formatDay(overview.stay_until)}` : ''}`,
    `Prawo do pracy ${overview.work_status === 'eligible' ? '✓' : overview.work_status === 'pending' ? '⚠' : '—'}${overview.work_until ? ` ${formatDay(overview.work_until)}` : ''}`,
    `Umowa ${contract !== '—' ? contract : '—'}`,
    `ZUS ${formalities?.mark === 'completed' ? '✓' : formalities?.mark === 'current' || formalities?.mark === 'blocked' ? '⚠' : '—'}`,
    medicalMark ? `Badania ${medicalMark}` : null,
  ].filter((value): value is string => Boolean(value))
  const domainChips = overview.phase === 'returned'
    ? [
        citizenship ? `${countryFlag(overview.citizenship)} ${citizenship}`.trim() : null,
        `Pobyt ${overview.stay_basis && overview.stay_basis !== 'none' ? '✓' : '—'}${overview.stay_until ? ` ${formatDay(overview.stay_until)}` : ''}`,
        'Prawo do pracy —',
        'Employment zakończone',
      ].filter((value): value is string => Boolean(value))
    : standardDomainChips

  return (
    <>
      <section className="card min-w-0 overflow-visible p-4 sm:p-5" aria-labelledby="employee-lifecycle-heading">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 id="employee-lifecycle-heading" className="truncate text-xl font-semibold text-slate-950">{surface.header.name}</h2>
            {role ? <p className="mt-1 text-sm text-slate-600">{role}</p> : null}
          </div>
          <ActionMenu items={lifecycleItems} label="Działania lifecycle" />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <StatusBadge label={phaseLabel.toLocaleUpperCase(locale)} semantic={semantic} />
          {overview.phase === 'active' && contract !== '—' ? <StatusBadge label={contract} semantic="neutral" /> : null}
          {overview.phase === 'active' && overview.start_on ? <StatusBadge label={`od ${formatDay(overview.start_on)}`} semantic="neutral" /> : null}
        </div>

        {overview.phase === 'returned' ? (
          <div className="mt-3 text-sm text-slate-600">
            <p className="font-medium text-slate-900">HR processing stopped</p>
            <p>Waiting for Recruitment update</p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2" aria-label="Status domen pracownika">
          {domainChips.map((label) => <Chip key={label} behavior="static" size="md" label={label} />)}
        </div>

        {overview.phase === 'returned' ? (
          <Alert
            className="mt-4"
            semantic="info"
            title="Proces HR zatrzymany"
            action={surface.candidate_id ? <Button size="sm" onClick={() => onOpen('recruitment')}>Otwórz sprawę w Recruitment</Button> : null}
          >
            Oczekuje na ponowne przekazanie przez Recruitment.
          </Alert>
        ) : overview.notice === 'healthy' ? (
          <Alert className="mt-4" semantic="success" title="Wszystko w porządku">
            {overview.nearest_label && overview.nearest_on
              ? `Najbliższy termin: ${overview.nearest_label} · ${formatDay(overview.nearest_on)}`
              : 'Brak pilnych działań.'}
          </Alert>
        ) : overview.phase !== 'ended' ? (
          <Alert
            className="mt-4"
            semantic="warning"
            title="Wymaga uwagi"
            action={actionTarget ? <Button size="sm" onClick={() => onOpen(actionTarget)}>{actionLabel}</Button> : null}
          >
            {action?.reason || action?.title || `${overview.attention_count} rzeczy wymagają działania.`}
          </Alert>
        ) : null}
      </section>

      {overview.phase === 'preparing' ? (
        <section className="card min-w-0 p-4 sm:p-5" aria-labelledby="employment-preparation-heading">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 id="employment-preparation-heading" className="text-xs font-semibold uppercase tracking-wide text-slate-700">
              Przygotowanie do zatrudnienia
            </h3>
            <span className="text-sm font-semibold text-slate-700">{progressPosition} / {path.length}</span>
          </div>
          <ProgressStepper
            label="Przygotowanie do zatrudnienia"
            steps={path.map((step) => ({
              id: step.id,
              label: step.label,
              state: step.mark,
              detail: (step.mark === 'current' || step.mark === 'blocked') && action?.title ? action.title : null,
              onOpen: step.target ? () => onOpen(step.target) : null,
            }))}
          />
        </section>
      ) : overview.phase === 'active' ? (
        <p className="px-1 text-sm font-medium text-slate-700">Employment active{overview.start_on ? ` · od ${formatDay(overview.start_on)}` : ''}</p>
      ) : overview.phase === 'ended' ? (
        <p className="px-1 text-sm font-medium text-slate-700">Employment zakończone{surface.header.ended_on ? ` · ${formatDay(surface.header.ended_on)}` : ''}</p>
      ) : (
        <p className="px-1 text-sm font-medium text-slate-700">HR process zatrzymany · Returned to Recruitment</p>
      )}

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
  approvedLabel,
}: {
  group?: HrEmployeeRecordGroup
  locale: 'en' | 'ru' | 'pl'
  approvedLabel: string
}) {
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
  if (!sections.length) return <p>{group.empty}</p>
  return (
    <div className="space-y-6" id={`record-group-${group.id}`}>
      {sections.map((rows) => (
        <div key={rows[0].id}>
          <h3>
            {rows[0].label}
            {factCoverage({ ...group, rows }) ? ` · ${factCoverage({ ...group, rows })} ${approvedLabel}` : ''}
          </h3>
          <GroupBody group={{ ...group, rows }} locale={locale} />
        </div>
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
    <section className="card w-full p-4">
      <h3>
        {t('app.hr.employee_record.tasks', { defaultValue: 'Zadania' })} {items.length}
      </h3>
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
    </section>
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
    <CandidateNotesRailSection
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
    <CandidateTimelinePanel
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

function evidenceSemantic(code: string | null): StatusBadgeSemantic {
  if (code === 'approved') return documentSeverityToSemantic('ok')
  if (code === 'expired' || code === 'rejected') return documentSeverityToSemantic('bad')
  if (code === 'missing' || code === 'not_required') return 'neutral'
  return documentSeverityToSemantic('info')
}

function GroupBody({ group, locale }: { group: HrEmployeeRecordGroup; locale: 'en' | 'ru' | 'pl' }) {
  const { t } = useI18n()
  if (group.rows.length === 0) {
    return <p>{EMPTY_GROUP[group.id] || 'Nieuzupełnione'}</p>
  }
  if (group.id === 'kwalifikacje' || group.id === 'badania') {
    return (
      <div className="mt-3 space-y-3">
        {group.rows.map((row) => (
          <div key={row.id} id={`record-row-${row.id}`}>
            <p>{row.label}</p>
            {(row.details || []).map((detail) => (
              <div key={detail.label} className="grid grid-cols-[8.5rem_minmax(0,1fr)] items-baseline gap-2">
                <div className="label mb-0">{detail.label}</div>
                <p>{displayValue(detail.value, detail.label, locale)}</p>
              </div>
            ))}
            <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] items-baseline gap-2">
              <div className="label mb-0">Evidence</div>
              <p>
                <StatusBadge
                  label={evidenceLabel(row.evidence, t)}
                  semantic={evidenceSemantic(row.evidence)}
                  size="sm"
                />
              </p>
            </div>
          </div>
        ))}
      </div>
    )
  }
  return (
    <div className="mt-3 space-y-2">
      {group.rows.map((row) => {
        const status = displayStatus(row.status)
        const evidence = row.evidence && !looksTechnical(row.evidence) ? row.evidence : null
        return (
          <div key={row.id} id={`record-row-${row.id}`} className="grid grid-cols-[8.5rem_minmax(0,1fr)] items-baseline gap-2">
            <div className="label mb-0">{row.label}</div>
            <p>
              {meaningfulValue(row, locale)}
              {status ? <span className="badge ml-2">{status}</span> : null}
              {evidence ? ` · ${evidence}` : ''}
            </p>
          </div>
        )
      })}
    </div>
  )
}

const AUTO_SAVE_DELAY_MS = 1500

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

function useAutosave(fingerprint: string, enabled: boolean, save: () => Promise<boolean>) {
  const saved = useRef<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveRef = useRef(save)
  useEffect(() => {
    saveRef.current = save
  })
  useEffect(() => {
    if (saved.current === null) saved.current = fingerprint
    if (!enabled) return
    if (saved.current === fingerprint) return
    if (timer.current) clearTimeout(timer.current)
    const pending = fingerprint
    timer.current = setTimeout(() => {
      timer.current = null
      void saveRef.current().then((ok) => {
        if (ok) saved.current = pending
      })
    }, AUTO_SAVE_DELAY_MS)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [fingerprint, enabled])
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
  const [firstName, setFirstName] = useState(person?.first_name || '')
  const [lastName, setLastName] = useState(person?.last_name || '')
  const [birth, setBirth] = useState(person?.birth_date || '')
  const [citizenship, setCitizenship] = useState(person?.citizenship || '')
  const [phone, setPhone] = useState(person?.phone || '')
  const [phoneCountry, setPhoneCountry] = useState(person?.phone_country || '')
  const [email, setEmail] = useState(person?.email || '')
  const [preferredContact, setPreferredContact] = useState(person?.preferred_contact || '')
  const [address, setAddress] = useState<HrEmployeeRecordAddress>(() => addressDraft(person?.address))
  const [regDiff, setRegDiff] = useState(Boolean(person?.reg_address_diff))
  const [regAddress, setRegAddress] = useState<HrEmployeeRecordAddress>(() => addressDraft(person?.reg_address))
  const [pesel, setPesel] = useState(person?.pesel || '')
  const [languages, setLanguages] = useState(person?.languages || '')
  const languageValues = languages.split(',').map((part) => part.trim()).filter(Boolean)
  const payload: HrEmployeeRecordPersonIn = {
    first_name: firstName,
    last_name: lastName,
    birth_date: birth,
    citizenship,
    phone,
    phone_country: phoneCountry,
    email,
    preferred_contact: preferredContact,
    address,
    reg_address_diff: regDiff,
    reg_address: regAddress,
    pesel,
    languages,
  }
  const fingerprint = JSON.stringify(payload)
  useAutosave(fingerprint, writable && Boolean(firstName.trim() && lastName.trim()), async () => {
    try {
      const result = await updateHrEmployeeRecordPerson(employeeId, payload)
      if (result.accepted === false) {
        onError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
        return false
      }
      onError(null)
      onSaved()
      return true
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
      return false
    }
  })
  const setAddressPart = (key: keyof HrEmployeeRecordAddress, value: string) => {
    setAddress((current) => ({ ...current, [key]: value }))
  }
  const setRegPart = (key: keyof HrEmployeeRecordAddress, value: string) => {
    setRegAddress((current) => ({ ...current, [key]: value }))
  }
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{t('app.candidate_card.sections.basic.title')}</h3>
        <Input label={t('app.candidate_card.fields.first_name')} value={firstName} readOnly={!writable} onChange={(event) => setFirstName(event.target.value)} />
        <Input label={t('app.candidate_card.fields.last_name')} value={lastName} readOnly={!writable} onChange={(event) => setLastName(event.target.value)} />
        <Input label={t('app.candidate_card.fields.birth_date')} type="date" value={birth} readOnly={!writable} onChange={(event) => setBirth(event.target.value)} />
        <label className="block">
          <div className="label">{t('app.candidate_card.fields.citizenship')}</div>
          <SearchableSelect
            options={countries}
            value={citizenship}
            onChange={setCitizenship}
            disabled={!writable}
            placeholder={selectTexts.empty}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
          />
        </label>
        <Input label="PESEL" value={pesel} readOnly={!writable} onChange={(event) => setPesel(event.target.value)} />
        <Input label={t('app.candidate_card.fields.short_id')} value={person?.short_id || ''} readOnly />
        <div className="lg:col-span-2">
          <div className="label">{t('app.candidate_card.fields.languages')}</div>
          <CheckboxMultiSelect
            options={languagesCatalog}
            values={languageValues}
            onChange={(values) => setLanguages(values.join(','))}
            disabled={!writable}
            placeholder={selectTexts.multiNone}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
            multiSelectedLabel={selectTexts.multiSelected}
          />
        </div>
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{t('app.candidate_card.intake.steps.contacts')}</h3>
        <label className="block">
          <div className="label">{t('app.candidate_card.fields.phone')}</div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
            <div className="sm:w-64">
              <SearchableSelect
                options={dialCodes}
                value={phoneCountry}
                onChange={setPhoneCountry}
                disabled={!writable}
                placeholder={selectTexts.empty}
                searchPlaceholder={selectTexts.search}
                noResultsLabel={selectTexts.noResults}
              />
            </div>
            <div className="min-w-0 flex-1">
              <Input value={phone} readOnly={!writable} onChange={(event) => setPhone(event.target.value)} />
            </div>
          </div>
        </label>
        <Input label={t('app.candidate_card.fields.email')} value={email} readOnly={!writable} onChange={(event) => setEmail(event.target.value)} />
        <label className="block">
          <div className="label">{t('app.candidate_card.fields.preferred_contact')}</div>
          <select className="input" value={preferredContact} disabled={!writable} onChange={(event) => setPreferredContact(event.target.value)}>
            {PREFERRED_CONTACT_VALUES.map((value) => (
              <option key={value || 'none'} value={value}>
                {t(`app.candidate_card.contacts.options.${value || 'none'}`)}
              </option>
            ))}
          </select>
        </label>
      </section>
      <AddressFields
        title={t('app.candidate_card.sections.personal.address_current')}
        address={address}
        countries={countries}
        writable={writable}
        selectTexts={selectTexts}
        onChange={setAddressPart}
        t={t}
      />
      <Checkbox
        label={t('app.candidate_card.fields.address.diff')}
        checked={regDiff}
        onChange={writable ? setRegDiff : undefined}
      />
      {regDiff ? (
        <AddressFields
          title={t('app.candidate_card.sections.personal.address_registered')}
          address={regAddress}
          countries={countries}
          writable={writable}
          selectTexts={selectTexts}
          onChange={setRegPart}
          t={t}
        />
      ) : null}
    </div>
  )
}

function AddressFields({
  title,
  address,
  countries,
  writable,
  selectTexts,
  onChange,
  t,
}: {
  title: string
  address: HrEmployeeRecordAddress
  countries: { value: string; label: string }[]
  writable: boolean
  selectTexts: { empty: string; search: string; noResults: string }
  onChange: (key: keyof HrEmployeeRecordAddress, value: string) => void
  t: Translate
}) {
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <h3 className="lg:col-span-2">{title}</h3>
      <label className="block lg:col-span-2">
        <div className="label">{t('app.candidate_card.fields.address.country')}</div>
        <SearchableSelect
          options={countries}
          value={address.country}
          onChange={(value) => onChange('country', value)}
          disabled={!writable}
          placeholder={selectTexts.empty}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
        />
      </label>
      <Input label={t('app.candidate_card.fields.address.city')} value={address.city} readOnly={!writable} onChange={(event) => onChange('city', event.target.value)} />
      <Input label={t('app.candidate_card.fields.address.zip')} value={address.zip} readOnly={!writable} onChange={(event) => onChange('zip', event.target.value)} />
      <div className="lg:col-span-2">
        <Input label={t('app.candidate_card.fields.address.street')} value={address.street} readOnly={!writable} onChange={(event) => onChange('street', event.target.value)} />
      </div>
      <Input label={t('app.candidate_card.fields.address.house')} value={address.house} readOnly={!writable} onChange={(event) => onChange('house', event.target.value)} />
      <Input label={t('app.candidate_card.fields.address.apt')} value={address.apt} readOnly={!writable} onChange={(event) => onChange('apt', event.target.value)} />
    </section>
  )
}

function LegalForm({
  employeeId,
  group,
  legal,
  writable,
  onError,
  onSaved,
}: {
  employeeId: string
  group: HrEmployeeRecordGroup
  legal: HrEmployeeRecordSurface['legal']
  writable: boolean
  onError: (message: string | null) => void
  onSaved: () => void
}) {
  const { t, locale } = useI18n()
  const [citizenshipClass, setCitizenshipClass] = useState(legal?.citizenship_class || 'third_country')
  const [stay, setStay] = useState(legal?.stay_basis && legal.stay_basis !== 'none' ? legal.stay_basis : 'none')
  const [basis, setBasis] = useState(legal?.work_authorization_basis || 'separate_required')
  const [valid, setValid] = useState(legal?.valid_for_this_employment || 'operator_verification')
  const payload: HrDriverLegalIn = {
    citizenship_class: citizenshipClass,
    stay_basis: stay,
    work_authorization_basis: basis,
    valid_for_this_employment: valid,
  }
  const fingerprint = JSON.stringify(payload)
  useAutosave(fingerprint, writable, async () => {
    try {
      const result = await confirmHrDriverLegal(employeeId, payload)
      if (result.reason === 'not_preparing') {
        onError(result.reason)
        return false
      }
      onError(null)
      onSaved()
      return true
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
      return false
    }
  })
  const statusRows = group.rows.filter((row) => row.id === 'legalizacja.status')
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'legalizacja.stay_basis', t('app.candidate_card.fields.poland_basis'))}</h3>
        <CatalogSelect
          label={t('app.candidate_card.fields.citizenship')}
          value={citizenshipClass}
          options={['pl', 'eu_eea_ch', 'third_country']}
          onChange={setCitizenshipClass}
          disabled={!writable}
          t={t}
        />
        <CatalogSelect
          label={rowLabel(group, 'legalizacja.stay_basis', t('app.candidate_card.fields.poland_basis'))}
          value={stay}
          options={['not_required', 'visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none']}
          onChange={setStay}
          disabled={!writable}
          t={t}
        />
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'legalizacja.work_basis', t('app.candidate_card.fields.residency_status'))}</h3>
        <CatalogSelect
          label={rowLabel(group, 'legalizacja.work_basis', t('app.candidate_card.fields.residency_status'))}
          value={basis}
          options={['not_required', 'included_in_stay', 'separate_required']}
          onChange={setBasis}
          disabled={!writable}
          t={t}
        />
      </section>
      <section className="space-y-3">
        <h3>{rowLabel(group, 'legalizacja.valid_for_this_employment', t('common.labels.status'))}</h3>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <CatalogSelect
            label={rowLabel(group, 'legalizacja.valid_for_this_employment', t('common.labels.status'))}
            value={valid}
            options={['yes', 'no', 'operator_verification']}
            onChange={setValid}
            disabled={!writable}
            t={t}
          />
        </div>
        <GroupBody group={{ ...group, rows: statusRows }} locale={locale} />
      </section>
    </div>
  )
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
  const [position, setPosition] = useState(terms?.position || '')
  const [contractBasis, setContractBasis] = useState(terms?.contract_basis || '')
  const [workTime, setWorkTime] = useState(terms?.work_time_value || '')
  const [workTimeUnit, setWorkTimeUnit] = useState(terms?.work_time_unit || 'fte')
  const [workSystem, setWorkSystem] = useState(terms?.work_system || '')
  const [workplace, setWorkplace] = useState(terms?.workplace || '')
  const [amount, setAmount] = useState(terms?.compensation_amount || '')
  const [currency, setCurrency] = useState(terms?.compensation_currency || 'PLN')
  const [period, setPeriod] = useState(terms?.compensation_unit || 'month')
  const [duration, setDuration] = useState(terms?.duration || 'indefinite')
  const [fixedEnd, setFixedEnd] = useState(terms?.fixed_term_end || '')
  const [probation, setProbation] = useState(terms?.probation_status || 'none')
  const [probationEnd, setProbationEnd] = useState(terms?.probation_end || '')
  const [planned, setPlanned] = useState(terms?.intended_start_date || '')
  const payload: HrDriverTermsIn = {
    position,
    contract_basis: contractBasis,
    work_time_value: workTime,
    work_time_unit: workTimeUnit,
    work_system: workSystem,
    workplace,
    compensation_amount: amount,
    compensation_currency: currency,
    compensation_unit: period,
    duration,
    fixed_term_end: duration === 'fixed' ? fixedEnd || null : null,
    probation_status: probation,
    probation_end: probation === 'dated' ? probationEnd || null : null,
    intended_start_date: planned,
  }
  const fingerprint = JSON.stringify(payload)
  useAutosave(fingerprint, writable, async () => {
    try {
      const result = await confirmHrDriverTerms(employeeId, payload)
      if (result.accepted === false) {
        onError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
        return false
      }
      onError(null)
      onSaved()
      return true
    } catch {
      onError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
      return false
    }
  })
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'zatrudnienie.position', t('app.candidate_card.employment.placeholders.position'))}</h3>
        <Input label={rowLabel(group, 'zatrudnienie.employer', t('app.candidate_card.employment.columns.employer', { defaultValue: 'Pracodawca' }))} value={rowById([group], 'zatrudnienie.employer')?.value || ''} readOnly />
        <Input label={rowLabel(group, 'zatrudnienie.position', t('app.candidate_card.employment.placeholders.position'))} value={position} readOnly={!writable} onChange={(event) => setPosition(event.target.value)} />
        <Input label={rowLabel(group, 'zatrudnienie.contract_basis', t('app.candidate_card.employment.columns.position'))} value={contractBasis} readOnly={!writable} onChange={(event) => setContractBasis(event.target.value)} />
        <Input label={rowLabel(group, 'zatrudnienie.workplace', t('app.candidate_card.fields.address.city'))} value={workplace} readOnly={!writable} onChange={(event) => setWorkplace(event.target.value)} />
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))}</h3>
        <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={workTime} readOnly={!writable} onChange={(event) => setWorkTime(event.target.value)} />
        <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={workTimeUnit} readOnly={!writable} onChange={(event) => setWorkTimeUnit(event.target.value)} />
        <Input label={rowLabel(group, 'zatrudnienie.work_system', t('public.company_intake.fields.work_system'))} value={workSystem} readOnly={!writable} onChange={(event) => setWorkSystem(event.target.value)} />
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'zatrudnienie.compensation', t('app.hr.employee_detail.payroll_base_rate'))}</h3>
        <Input label={rowLabel(group, 'zatrudnienie.compensation', t('app.hr.employee_detail.payroll_base_rate'))} value={amount} readOnly={!writable} onChange={(event) => setAmount(event.target.value)} />
        <Input label={t('app.hr.employee_detail.payroll_currency')} value={currency} readOnly={!writable} onChange={(event) => setCurrency(event.target.value)} />
        <Input label={t('app.hr.employee_detail.payroll_pay_type')} value={period} readOnly={!writable} onChange={(event) => setPeriod(event.target.value)} />
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <h3 className="lg:col-span-2">{rowLabel(group, 'zatrudnienie.planned_start', t('app.candidate_card.employment.columns.start'))}</h3>
        <CatalogSelect label={rowLabel(group, 'zatrudnienie.duration', t('app.candidate_card.employment.columns.end'))} value={duration} options={['indefinite', 'fixed']} onChange={setDuration} disabled={!writable} t={t} />
        {duration === 'fixed' ? (
          <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={fixedEnd} readOnly={!writable} onChange={(event) => setFixedEnd(event.target.value)} />
        ) : null}
        <CatalogSelect label={rowLabel(group, 'zatrudnienie.probation', t('app.hr.employee_detail.workforce_journey.contract'))} value={probation} options={['none', 'dated']} onChange={setProbation} disabled={!writable} t={t} />
        {probation === 'dated' ? (
          <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={probationEnd} readOnly={!writable} onChange={(event) => setProbationEnd(event.target.value)} />
        ) : null}
        <Input label={rowLabel(group, 'zatrudnienie.planned_start', t('app.candidate_card.employment.columns.start'))} type="date" value={planned} readOnly={!writable} onChange={(event) => setPlanned(event.target.value)} />
        <Input label={rowLabel(group, 'zatrudnienie.actual_start', t('app.candidate_card.employment.columns.start'))} value={rowById([group], 'zatrudnienie.actual_start')?.value || ''} readOnly />
      </section>
    </div>
  )
}

function rowLabel(group: HrEmployeeRecordGroup, id: string, fallback: string): string {
  return group.rows.find((row) => row.id === id)?.label || fallback
}

function CatalogSelect({
  label,
  value,
  options,
  onChange,
  disabled,
  t,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
  disabled?: boolean
  t: Translate
}) {
  return (
    <label className="block">
      <div className="label">{label}</div>
      <select className="input" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {knownOptionLabel(t, option) || option}
          </option>
        ))}
      </select>
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
  return t(`admin.documents.status_labels.${code || 'missing'}`, { defaultValue: code || 'Missing' })
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
  const filled = group.rows.filter((row) => displayValue(row.value, row.label, locale) !== '—')
  if (group.id === 'dokumenty') {
    const total = documents?.total ?? 0
    const attention = documents?.attention ?? 0
    return (
      <>
        <p>
          {total} dokumentów
          {attention > 0 ? ` · ${attention} wymaga uwagi` : ''}
        </p>
        <Link to={CRM_APP_PATHS.documents} className="btn-secondary btn-sm">
          Otwórz dokumenty
        </Link>
      </>
    )
  }
  if (group.id === 'formalnosci') {
    const zus = group.rows.find((row) => row.id === 'formalnosci.zus')
    return (
      <>
        <p>{zus ? meaningfulValue(zus, locale) : EMPTY_GROUP.formalnosci}</p>
        <Link to={CRM_APP_PATHS.hrZusWorkspace} className="btn-secondary btn-sm">
          Open
        </Link>
      </>
    )
  }
  if (filled.length === 0) {
    return <p>{EMPTY_GROUP[group.id] || 'Nieuzupełnione'}</p>
  }
  return (
    <>
      {filled.map((row) => (
        <p key={row.id} id={`record-row-${row.id}`}>
          {row.label}: {meaningfulValue(row, locale)}
        </p>
      ))}
    </>
  )
}
