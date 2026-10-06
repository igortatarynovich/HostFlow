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
import { NotesCapability } from '../../platform/capabilities/notes/NotesCapability'
import { StatusBadge } from '../ui/StatusBadge'
import { documentSeverityToSemantic, type StatusBadgeSemantic } from '../ui/statusBadgeSemantics'
import { getLanguageDisplayName, getRegionDisplayName } from '../../utils/catalogLocale'

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
  const status = statusSummary(surface, groups, t)
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

  return (
    <div className="card min-w-0 p-3">
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-4 lg:pr-6">
          <EmployeeHero
            surface={surface}
            status={status}
            groups={groups}
            locale={locale}
            onOpenGroup={(groupId) => {
              const next = TAB_FOR_GROUP[groupId]
              if (next) setTab(next)
            }}
            onOpenAction={runAction}
          />
          {error ? <p className="alert-error">{error}</p> : null}

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
            <section className="card w-full p-4">
              <NotesCapability
                entity={{ resourceType: 'candidate', resourceId: surface.candidate_id }}
                patching={false}
                readOnly={returned}
                onClose={() => undefined}
                onRefresh={() => undefined}
              />
            </section>
          ) : null}
          <RecordHistory group={activeGroup('historia')} />
        </aside>
      </div>
    </div>
  )
}

function statusSummary(
  surface: HrEmployeeRecordSurface,
  groups: HrEmployeeRecordGroup[],
  t: Translate,
): { headline: string; semantic: StatusBadgeSemantic; context: string[]; primary: string | null; secondary: string | null } {
  const action = surface.current_process.next_action
  const returned = surface.current_process.destination === 'recruitment' || action?.code === 'returned_to_recruitment'
  const position = surface.header.position
  const employer = surface.header.employer
  const contract = rowById(groups, 'zatrudnienie.contract_basis')?.value
  const actual = rowById(groups, 'zatrudnienie.actual_start')?.value
  const planned = rowById(groups, 'zatrudnienie.planned_start')?.value || surface.header.planned_start
  const context = [[position, employer].filter(Boolean).join(' · ')].filter(Boolean)
  const issues = urgentIssues(groups)
  const lead = issues[0]
  const rest = Math.max(issues.length - 1, 0) + (surface.current_process.missing?.length || 0)

  if (returned) {
    return {
      headline: t('app.hr.employee_record.status.returned', { defaultValue: 'Wrócił do rekrutacji' }),
      semantic: 'info',
      context,
      primary: action?.reason || t('app.hr.employee_record.status.waiting_recruitment', { defaultValue: 'Oczekuje na aktualizację przez Recruitment' }),
      secondary: null,
    }
  }
  if (surface.state === 'ended') {
    if (surface.header.ended_on) {
      context.push(`${t('app.hr.employee_record.status.ended_on', { defaultValue: 'Zakończono' })} ${formatDay(surface.header.ended_on)}`)
    }
    return {
      headline: t('app.hr.employee_record.status.ended', { defaultValue: 'Zatrudnienie zakończone' }),
      semantic: 'neutral',
      context,
      primary: null,
      secondary: null,
    }
  }
  if (surface.state === 'preparing') {
    if (planned) {
      context.push(`${t('app.hr.employee_record.status.planned_start', { defaultValue: 'Planowany start' })}: ${formatDay(planned)}`)
    }
    return {
      headline: t('app.hr.employee_record.status.preparing', { defaultValue: 'Przygotowanie do zatrudnienia' }),
      semantic: 'warning',
      context,
      primary: rest > 0
        ? `${rest} ${t('app.hr.employee_record.status.actions_required', { defaultValue: 'rzeczy wymagają działania' })}`
        : null,
      secondary: action ? `${t('app.hr.employee_record.status.next_action', { defaultValue: 'Następne działanie' })}: ${action.title}` : null,
    }
  }

  if (actual || planned) {
    const when = formatDay(actual || planned)
    context.push([`Od ${when}`, contract].filter(Boolean).join(' · '))
  }
  const urgent = lead && lead.kind !== 'soon' ? lead : null
  const attention = urgent || (action ? null : lead)
  if (attention) {
    return {
      headline: t('app.hr.employee_record.status.active', { defaultValue: 'Zatrudniony · Aktywny' }),
      semantic: attention.kind === 'soon' ? 'warning' : 'bad',
      context,
      primary: [issueLine(t, attention), rest > 0 ? `+ ${rest}` : null].filter(Boolean).join(' · '),
      secondary: action ? `${t('app.hr.employee_record.status.next_action', { defaultValue: 'Następne działanie' })}: ${action.title}` : null,
    }
  }
  if (action) {
    return {
      headline: t('app.hr.employee_record.status.active', { defaultValue: 'Zatrudniony · Aktywny' }),
      semantic: 'warning',
      context,
      primary: `${t('app.hr.employee_record.status.next_action', { defaultValue: 'Następne działanie' })}: ${action.title}`,
      secondary: lead ? issueLine(t, lead) : null,
    }
  }
  return {
    headline: surface.state === 'active'
      ? t('app.hr.employee_record.status.active', { defaultValue: 'Zatrudniony · Aktywny' })
      : t('app.hr.employee_record.status.none', { defaultValue: 'Brak zatrudnienia' }),
    semantic: surface.state === 'active' ? 'ok' : 'neutral',
    context,
    primary: surface.state === 'active'
      ? t('app.hr.employee_record.status.healthy', { defaultValue: 'Wszystko w porządku' })
      : null,
    secondary: surface.state === 'active'
      ? t('app.hr.employee_record.status.no_action', { defaultValue: 'Brak wymaganych działań' })
      : null,
  }
}

function urgentIssues(groups: HrEmployeeRecordGroup[]): { kind: 'blocking' | 'expired' | 'soon'; label: string; days: number; group: string }[] {
  const byLabel = new Map<string, { kind: 'blocking' | 'expired' | 'soon'; label: string; days: number; group: string }>()
  for (const group of groups) {
    if (group.id === 'historia') continue
    for (const row of group.rows) {
      const until = row.details?.find((detail) => detail.label === 'Ważne do')?.value
      const days = until ? daysUntil(until) : null
      let next: { kind: 'blocking' | 'expired' | 'soon'; label: string; days: number; group: string } | null = null
      if (row.status === 'blocking') next = { kind: 'blocking', label: row.label, days: days ?? -1, group: group.id }
      else if (days !== null && days < 0) next = { kind: 'expired', label: row.label, days, group: group.id }
      else if (row.evidence === 'expired' || row.evidence === 'rejected') {
        next = { kind: 'expired', label: row.label, days: days ?? -1, group: group.id }
      } else if (days !== null && days <= 30) next = { kind: 'soon', label: row.label, days, group: group.id }
      if (!next) continue
      const current = byLabel.get(row.label)
      if (!current || rankIssue(next) < rankIssue(current) || (rankIssue(next) === rankIssue(current) && next.days < current.days)) {
        byLabel.set(row.label, next)
      }
    }
  }
  return [...byLabel.values()].sort((left, right) => rankIssue(left) - rankIssue(right) || left.days - right.days)
}

function rankIssue(issue: { kind: 'blocking' | 'expired' | 'soon' }): number {
  if (issue.kind === 'blocking') return 0
  if (issue.kind === 'expired') return 1
  return 2
}

function daysUntil(iso: string): number | null {
  const day = iso.slice(0, 10)
  const target = new Date(`${day}T00:00:00`)
  if (Number.isNaN(target.getTime())) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target.getTime() - today.getTime()) / 86400000)
}

function issueLine(t: Translate, issue: { kind: 'blocking' | 'expired' | 'soon'; label: string; days: number; group?: string }): string {
  if (issue.kind === 'soon') {
    const unit = issue.days === 1
      ? t('app.hr.employee_record.status.day', { defaultValue: 'dzień' })
      : t('app.hr.employee_record.status.days', { defaultValue: 'dni' })
    return `${issue.label} ${t('app.hr.employee_record.status.expires_in', { defaultValue: 'wygasa za' })} ${issue.days} ${unit}`
  }
  if (issue.kind === 'expired') return `${issue.label} ${t('app.hr.employee_record.status.expired_word', { defaultValue: 'wygasł' })}`
  return issue.label
}

function EmployeeHero({
  surface,
  status,
  groups,
  locale,
  onOpenGroup,
  onOpenAction,
}: {
  surface: HrEmployeeRecordSurface
  status: ReturnType<typeof statusSummary>
  groups: HrEmployeeRecordGroup[]
  locale: 'en' | 'ru' | 'pl'
  onOpenGroup: (groupId: string) => void
  onOpenAction: () => void
}) {
  const { t } = useI18n()
  const lead = urgentIssues(groups)[0]
  const action = surface.current_process.next_action
  const showIssue = Boolean(lead && (lead.kind !== 'soon' || !action))
  const citizenship = surface.person?.citizenship ? getRegionDisplayName(surface.person.citizenship, locale) : ''
  const stayRow = rowById(groups, 'legalizacja.stay_basis')
  const workRow = rowById(groups, 'legalizacja.work_basis')
  const stay = stayRow ? displayValue(stayRow.value, stayRow.label, locale, t) : ''
  const work = workRow ? displayValue(workRow.value, workRow.label, locale, t) : ''
  const identity = [citizenship, stay, work].filter((part) => part && part !== '—').join(' · ')
  const contractEnd = surface.terms?.duration === 'fixed' ? surface.terms.fixed_term_end : null
  const role = [surface.header.position, surface.header.employer].filter(Boolean).join(' · ')
  const until = lead
    ? groups.find((group) => group.id === lead.group)?.rows.find((row) => row.label === lead.label)?.details?.find((detail) => detail.label === 'Ważne do')?.value
    : null
  const needsOpen = status.semantic === 'bad' || status.semantic === 'warning'
  return (
    <div className="min-w-0 rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-md">
      <h2 className="text-white">{surface.header.name}</h2>
      {role ? <p>{role}</p> : null}
      <StatusBadge inverse label={status.headline} semantic={status.semantic} />
      {identity ? <p>{identity}</p> : null}
      {contractEnd ? (
        <p>
          {t('app.candidate_card.employment.columns.end', { defaultValue: 'Umowa do' })} {formatDay(contractEnd)}
        </p>
      ) : null}
      {status.primary ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p>{status.primary}{until && showIssue ? ` · ${formatDay(until)}` : ''}</p>
          {needsOpen ? (
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => (showIssue && lead ? onOpenGroup(lead.group) : onOpenAction())}
            >
              {t('common.actions.open', { defaultValue: 'Otwórz' })}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
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

function RecordHistory({ group }: { group?: HrEmployeeRecordGroup }) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const rows = group?.rows || []
  const shown = expanded ? rows : rows.slice(0, 5)
  return (
    <section className="card w-full p-4">
      <h3>{group?.label || t('app.hr.employee_record.history', { defaultValue: 'Historia' })}</h3>
      {shown.map((row) => (
        <p key={row.id}>
          {row.value ? `${formatDay(row.value)} ` : ''}
          {row.label}
        </p>
      ))}
      {rows.length > 5 ? (
        <button type="button" className="btn-secondary btn-sm" onClick={() => setExpanded((value) => !value)}>
          {expanded
            ? t('common.actions.close', { defaultValue: 'Zamknij' })
            : t('app.hr.employee_record.show_history', { defaultValue: 'Pokaż wszystko' })}
        </button>
      ) : null}
    </section>
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
