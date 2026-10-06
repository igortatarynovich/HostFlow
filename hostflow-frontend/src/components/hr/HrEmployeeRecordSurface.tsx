import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
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
  type HrEmployeeRecordPersonIn,
  type HrEmployeeRecordRow,
  type HrEmployeeRecordSurface,
} from '../../api/workforce'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { Input, CheckboxMultiSelect, SearchableSelect } from '../candidate/shared/FormComponents'
import { useI18n } from '../../i18n'
import { usePlatformCountryOptions } from '../../hooks/usePlatformCatalogOptions'
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

const COMPACT_GROUPS = new Set(['formalnosci', 'dokumenty', 'historia'])

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
  const [surface, setSurface] = useState<HrEmployeeRecordSurface | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editingGroup, setEditingGroup] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

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

  const openTarget = (target: string | null) => {
    if (!target) return
    const elementId = target.startsWith('group:') ? `record-group-${target.slice('group:'.length)}` : `record-row-${target}`
    document.getElementById(elementId)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const openGroup = (groupId: string) => {
    setEditingGroup(groupId)
    document.getElementById(`record-group-${groupId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const finishSave = async (accepted: boolean, reason?: string | null) => {
    if (!accepted) {
      setError(reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
      return
    }
    setEditingGroup(null)
    setError(null)
    await load()
  }

  if (error && !surface) return <p className="alert-error">{error}</p>
  if (!surface) {
    return <p>{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  const groups = surface.groups
  const action = surface.current_process.next_action
  const recruitmentHref = surface.candidate_id
    ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(surface.candidate_id)}`
    : null
  const headerLine = [surface.header.position, surface.header.employer].filter(Boolean).join(' · ')
  const summary = summaryLines(groups, surface.header.planned_start, locale)
  const blockers = groups
    .flatMap((group) => group.rows)
    .filter((row) => row.status === 'blocking' || row.status === 'unresolved')
  const recordGroups = groups.filter((group) => !COMPACT_GROUPS.has(group.id))
  const compactGroups = groups.filter((group) => COMPACT_GROUPS.has(group.id))

  return (
    <div className="card min-w-0 p-3">
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-4 lg:pr-6">
          <header className="space-y-3">
            <div>
              <h2>{surface.header.name}</h2>
              {headerLine ? <p>{headerLine}</p> : null}
              <p>{employmentSentence(surface.state)}</p>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {summary.map((line) => (
                <div key={line.label} className="grid grid-cols-[7.5rem_minmax(0,1fr)] items-baseline gap-2">
                  <div className="label mb-0">{line.label}</div>
                  <p>{line.value}</p>
                </div>
              ))}
            </div>
          </header>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {recordGroups.map((group) => (
              <section
                key={group.id}
                id={`record-group-${group.id}`}
                className={group.id === 'zatrudnienie' ? 'app-surface p-4 lg:col-span-2' : 'app-surface p-4'}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3>
                    {group.label}
                    {factCoverage(group)
                      ? ` · ${factCoverage(group)} ${t('admin.documents.status_labels.approved', { defaultValue: 'Approved' })}`
                      : ''}
                  </h3>
                  {groupAction(group, surface, manage) ? (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => setEditingGroup(editingGroup === group.id ? null : group.id)}
                    >
                      {editingGroup === group.id ? 'Anuluj' : groupAction(group, surface, manage)}
                    </button>
                  ) : null}
                </div>
                {editingGroup === group.id && group.id === 'dane_osobowe' ? (
                  <PersonForm
                    person={surface.person}
                    saving={saving}
                    onSave={async (body) => {
                      setSaving(true)
                      try {
                        const result = await updateHrEmployeeRecordPerson(employeeId, body)
                        await finishSave(result.accepted !== false, result.reason)
                      } catch {
                        setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
                      } finally {
                        setSaving(false)
                      }
                    }}
                  />
                ) : editingGroup === group.id && group.id === 'legalizacja' ? (
                  <LegalForm
                    group={group}
                    legal={surface.legal}
                    saving={saving}
                    onSave={async (body) => {
                      setSaving(true)
                      try {
                        const result = await confirmHrDriverLegal(employeeId, body)
                        await finishSave(result.accepted !== false, result.reason)
                      } catch {
                        setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
                      } finally {
                        setSaving(false)
                      }
                    }}
                  />
                ) : editingGroup === group.id && group.id === 'zatrudnienie' ? (
                  <TermsForm
                    group={group}
                    terms={surface.terms}
                    saving={saving}
                    onSave={async (body) => {
                      setSaving(true)
                      try {
                        const result = await confirmHrDriverTerms(employeeId, body)
                        await finishSave(result.accepted !== false, result.reason)
                      } catch {
                        setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' }))
                      } finally {
                        setSaving(false)
                      }
                    }}
                  />
                ) : (
                  <GroupBody group={group} locale={locale} />
                )}
              </section>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {compactGroups.map((group) => (
              <section key={group.id} id={`record-group-${group.id}`} className="app-surface p-4">
                <h3>{group.label}</h3>
                <CompactGroup group={group} locale={locale} documents={surface.documents} />
              </section>
            ))}
          </div>
        </div>

        <aside
          id="hr-verification"
          data-candidate-control-rail
          className="flex w-full min-w-0 flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-3.5rem)] lg:overflow-y-auto"
        >
          <section className="card w-full p-4">
            <h3>{t('app.hr.employee_record.current_process', { defaultValue: 'Current process' })}</h3>
            {action ? (
              <>
                <p>{action.title}</p>
                <p>{action.reason}</p>
                {surface.current_process.missing && surface.current_process.missing.length > 0 ? (
                  <p>Missing: {surface.current_process.missing.join(', ')}</p>
                ) : null}
                {surface.current_process.destination === 'recruitment' && recruitmentHref ? (
                  <Link to={recruitmentHref} className="btn-primary btn-sm">
                    {t('app.hr.employee_record.open_recruitment', { defaultValue: 'Open recruitment case' })}
                  </Link>
                ) : action.code === 'register_zus' ? (
                  <Link to={CRM_APP_PATHS.hrZusWorkspace} className="btn-primary btn-sm">
                    Open
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={saving}
                    onClick={() => {
                      if (action.code === 'confirm_terms') openGroup('zatrudnienie')
                      else if (action.code === 'confirm_legal' || action.code === 'start_work_authorization') openGroup('legalizacja')
                      else if (action.code === 'record_ready') {
                        setSaving(true)
                        void recordHrDriverReady(employeeId)
                          .then((result) => finishSave(result.accepted !== false, result.reason))
                          .catch(() => setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' })))
                          .finally(() => setSaving(false))
                      } else if (action.code === 'start_employment') {
                        setSaving(true)
                        void startHrDriverEmployment(employeeId)
                          .then((result) => finishSave(result.activated === true, result.reason))
                          .catch(() => setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save.' })))
                          .finally(() => setSaving(false))
                      } else openTarget(surface.current_process.target_row_id)
                    }}
                  >
                    {processButton(action.code)}
                  </button>
                )}
              </>
            ) : (
              <p>{t('app.hr.employee_record.no_action', { defaultValue: 'No open action.' })}</p>
            )}
            {error ? <p className="alert-error">{error}</p> : null}
          </section>

          <section className="card w-full p-4">
            <h3>{t('app.hr.employee_record.blockers', { defaultValue: 'Blockers' })}</h3>
            {blockers.length === 0 ? (
              <p>{t('app.hr.employee_record.no_blockers', { defaultValue: 'Brak blokerów' })}</p>
            ) : (
              blockers.map((row) => (
                <p key={row.id}>
                  {row.label}: {meaningfulValue(row, locale)}
                </p>
              ))
            )}
          </section>

          {surface.candidate_id ? (
            <>
              <section className="card w-full p-4">
                <NotesCapability
                  entity={{ resourceType: 'candidate', resourceId: surface.candidate_id }}
                  patching={false}
                  onClose={() => undefined}
                  onRefresh={() => undefined}
                />
              </section>
            </>
          ) : null}
        </aside>
      </div>
    </div>
  )
}

function employmentSentence(state: string | null): string {
  if (state === 'ended') return 'Employment ended'
  if (state === 'active') return 'Employment active'
  if (state === 'preparing') return 'Employment preparing'
  return 'No employment'
}

function summaryLines(
  groups: HrEmployeeRecordGroup[],
  plannedStart: string | null,
  locale: 'en' | 'ru' | 'pl',
): { label: string; value: string }[] {
  const phone = rowById(groups, 'dane_osobowe.phone')
  const email = rowById(groups, 'dane_osobowe.email')
  const citizenship = rowById(groups, 'dane_osobowe.citizenship')
  const actual = rowById(groups, 'zatrudnienie.actual_start')
  const planned = rowById(groups, 'zatrudnienie.planned_start')
  const start = displayValue(actual?.value || planned?.value || plannedStart, 'Data', locale)
  return [
    { label: 'Telefon', value: phone ? meaningfulValue(phone, locale) : 'Brak telefonu' },
    { label: 'Email', value: email ? meaningfulValue(email, locale) : 'Brak adresu e-mail' },
    { label: 'Obywatelstwo', value: citizenship ? meaningfulValue(citizenship, locale) : 'Obywatelstwo nieustalone' },
    { label: 'Employment', value: start === '—' ? 'Termin nieustalony' : `${start} — …` },
  ]
}

function processButton(code: string): string {
  if (code === 'confirm_terms') return 'Complete terms'
  if (code === 'start_work_authorization') return 'Rozpocznij procedurę'
  if (code === 'start_employment') return 'Start employment'
  if (code === 'record_ready') return 'Record Ready to Start'
  return 'Open'
}

function groupAction(group: HrEmployeeRecordGroup, surface: HrEmployeeRecordSurface, manage: boolean): string | null {
  if (!manage) return null
  if (group.id === 'dane_osobowe') return 'Edytuj'
  if (surface.state !== 'preparing') return null
  if (group.id === 'zatrudnienie') return surface.terms ? 'Edytuj' : 'Uzupełnij'
  if (group.id !== 'legalizacja') return null
  const stay = group.rows.find((row) => row.id === 'legalizacja.stay_basis')
  if (!stay?.value) return 'Uzupełnij podstawę pobytu'
  return 'Zweryfikuj'
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

function PersonForm({
  person,
  saving,
  onSave,
}: {
  person: HrEmployeeRecordSurface['person']
  saving: boolean
  onSave: (body: HrEmployeeRecordPersonIn) => void
}) {
  const { t, locale } = useI18n()
  const countries = usePlatformCountryOptions(locale)
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
  const [email, setEmail] = useState(person?.email || '')
  const [address, setAddress] = useState(person?.address || '')
  const [pesel, setPesel] = useState(person?.pesel || '')
  const [languages, setLanguages] = useState(person?.languages || '')
  const languageValues = languages.split(',').map((part) => part.trim()).filter(Boolean)
  return (
    <form
      className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({
          first_name: firstName,
          last_name: lastName,
          birth_date: birth,
          citizenship,
          phone,
          email,
          address,
          pesel,
          languages,
        })
      }}
    >
      <Input label={t('app.candidate_card.fields.first_name')} value={firstName} onChange={(event) => setFirstName(event.target.value)} />
      <Input label={t('app.candidate_card.fields.last_name')} value={lastName} onChange={(event) => setLastName(event.target.value)} />
      <Input label={t('app.candidate_card.fields.birth_date')} type="date" value={birth} onChange={(event) => setBirth(event.target.value)} />
      <label className="block">
        <div className="label">{t('app.candidate_card.fields.citizenship')}</div>
        <SearchableSelect
          options={countries}
          value={citizenship}
          onChange={setCitizenship}
          placeholder={selectTexts.empty}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
        />
      </label>
      <Input label={t('app.candidate_card.fields.phone')} value={phone} onChange={(event) => setPhone(event.target.value)} />
      <Input label={t('app.candidate_card.fields.email')} value={email} onChange={(event) => setEmail(event.target.value)} />
      <Input
        label={t('app.candidate_card.sections.personal.address_current')}
        value={address}
        onChange={(event) => setAddress(event.target.value)}
      />
      <Input label="PESEL" value={pesel} onChange={(event) => setPesel(event.target.value)} />
      <div className="lg:col-span-2">
        <div className="label">{t('app.candidate_card.fields.languages')}</div>
        <CheckboxMultiSelect
          options={languagesCatalog}
          values={languageValues}
          onChange={(values) => setLanguages(values.join(','))}
          placeholder={selectTexts.multiNone}
          searchPlaceholder={selectTexts.search}
          noResultsLabel={selectTexts.noResults}
          multiSelectedLabel={selectTexts.multiSelected}
        />
      </div>
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        {saving ? t('common.saving') : t('common.actions.save')}
      </button>
    </form>
  )
}

function LegalForm({
  group,
  legal,
  saving,
  onSave,
}: {
  group: HrEmployeeRecordGroup
  legal: HrEmployeeRecordSurface['legal']
  saving: boolean
  onSave: (body: HrDriverLegalIn) => void
}) {
  const { t } = useI18n()
  const [citizenshipClass, setCitizenshipClass] = useState(legal?.citizenship_class || 'third_country')
  const [stay, setStay] = useState(legal?.stay_basis && legal.stay_basis !== 'none' ? legal.stay_basis : 'none')
  const [basis, setBasis] = useState(legal?.work_authorization_basis || 'separate_required')
  const [valid, setValid] = useState(legal?.valid_for_this_employment || 'operator_verification')
  return (
    <form
      className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({
          citizenship_class: citizenshipClass,
          stay_basis: stay,
          work_authorization_basis: basis,
          valid_for_this_employment: valid,
        })
      }}
    >
      <CatalogSelect
        label={t('app.candidate_card.fields.citizenship')}
        value={citizenshipClass}
        options={['pl', 'eu_eea_ch', 'third_country']}
        onChange={setCitizenshipClass}
        t={t}
      />
      <CatalogSelect
        label={rowLabel(group, 'legalizacja.stay_basis', t('app.candidate_card.fields.poland_basis'))}
        value={stay}
        options={['not_required', 'visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none']}
        onChange={setStay}
        t={t}
      />
      <CatalogSelect
        label={rowLabel(group, 'legalizacja.work_basis', t('app.candidate_card.fields.residency_status'))}
        value={basis}
        options={['not_required', 'included_in_stay', 'separate_required']}
        onChange={setBasis}
        t={t}
      />
      <CatalogSelect
        label={rowLabel(group, 'legalizacja.valid_for_this_employment', t('common.labels.status'))}
        value={valid}
        options={['yes', 'no', 'operator_verification']}
        onChange={setValid}
        t={t}
      />
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        {saving ? t('common.saving') : t('common.actions.save')}
      </button>
    </form>
  )
}

function TermsForm({
  group,
  terms,
  saving,
  onSave,
}: {
  group: HrEmployeeRecordGroup
  terms: HrEmployeeRecordSurface['terms']
  saving: boolean
  onSave: (body: HrDriverTermsIn) => void
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
  return (
    <form
      className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({
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
        })
      }}
    >
      <Input label={rowLabel(group, 'zatrudnienie.position', t('app.candidate_card.employment.placeholders.position'))} value={position} onChange={(event) => setPosition(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.contract_basis', t('app.candidate_card.employment.columns.position'))} value={contractBasis} onChange={(event) => setContractBasis(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={workTime} onChange={(event) => setWorkTime(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.work_time', t('app.candidate_card.employment.columns.start'))} value={workTimeUnit} onChange={(event) => setWorkTimeUnit(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.work_system', t('public.company_intake.fields.work_system'))} value={workSystem} onChange={(event) => setWorkSystem(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.workplace', t('app.candidate_card.fields.address.city'))} value={workplace} onChange={(event) => setWorkplace(event.target.value)} />
      <Input label={rowLabel(group, 'zatrudnienie.compensation', t('app.hr.employee_detail.payroll_base_rate'))} value={amount} onChange={(event) => setAmount(event.target.value)} />
      <Input label={t('app.hr.employee_detail.payroll_currency')} value={currency} onChange={(event) => setCurrency(event.target.value)} />
      <Input label={t('app.hr.employee_detail.payroll_pay_type')} value={period} onChange={(event) => setPeriod(event.target.value)} />
      <CatalogSelect label={rowLabel(group, 'zatrudnienie.duration', t('app.candidate_card.employment.columns.end'))} value={duration} options={['indefinite', 'fixed']} onChange={setDuration} t={t} />
      {duration === 'fixed' ? (
        <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={fixedEnd} onChange={(event) => setFixedEnd(event.target.value)} />
      ) : null}
      <CatalogSelect label={rowLabel(group, 'zatrudnienie.probation', t('app.hr.employee_detail.workforce_journey.contract'))} value={probation} options={['none', 'dated']} onChange={setProbation} t={t} />
      {probation === 'dated' ? (
        <Input label={t('app.candidate_card.employment.columns.end')} type="date" value={probationEnd} onChange={(event) => setProbationEnd(event.target.value)} />
      ) : null}
      <Input label={rowLabel(group, 'zatrudnienie.planned_start', t('app.candidate_card.employment.columns.start'))} type="date" value={planned} onChange={(event) => setPlanned(event.target.value)} />
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        {saving ? t('common.saving') : t('common.actions.save')}
      </button>
    </form>
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
  t,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
  t: Translate
}) {
  return (
    <label className="block">
      <div className="label">{label}</div>
      <select className="input" value={value} onChange={(event) => onChange(event.target.value)}>
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
