import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
import CandidateDocsRailPanel from '../candidate/CandidateDocsRailPanel'
import { useI18n } from '../../i18n'
import { NotesCapability } from '../../platform/capabilities/notes/NotesCapability'
import { getRegionDisplayName } from '../../utils/catalogLocale'

const HIDDEN_STATUS = new Set(['recorded', 'missing', 'canonical', 'process'])
const VALUE_LABELS: Record<string, string> = {
  karta_pobytu: 'Residence card',
  visa_d: 'Visa D',
  visa_c: 'Visa C',
  visa_free: 'Visa-free',
  waiting_for_trc: 'Waiting for a residence card',
  special_protection: 'Special protection',
  none: '—',
  pass: 'Pass',
  separate_required: 'Separate authorization',
  included_in_stay: 'Included in the stay',
  not_required: 'Not required',
  operator_verification: 'Needs verification',
  yes: 'Yes',
  no: '—',
}

function formatDay(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [year, month, day] = iso.slice(0, 10).split('-')
  if (!year || !month || !day) return iso
  return `${day}.${month}.${year}`
}

function stateLabel(state: string | null): string {
  if (state === 'preparing') return 'Preparing'
  if (state === 'active') return 'Active'
  if (state === 'ended') return 'Ended'
  return 'No employment'
}

function looksTechnical(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return true
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(trimmed)
}

function displayValue(value: string | null, label: string, locale: 'en' | 'ru' | 'pl'): string {
  if (!value) return '—'
  if (looksTechnical(value)) return '—'
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return formatDay(value)
  const mapped = VALUE_LABELS[value]
  if (mapped) return mapped
  if (label === 'Obywatelstwo' && value.trim().length === 2) return getRegionDisplayName(value, locale)
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
                  <h3>{group.label}</h3>
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
                {group.id === 'legalizacja' ? (
                  <Link to={CRM_APP_PATHS.documents} className="btn-secondary btn-sm">
                    Dodaj dokument
                  </Link>
                ) : null}
              </section>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {compactGroups.map((group) => (
              <section key={group.id} id={`record-group-${group.id}`} className="app-surface p-4">
                <h3>{group.label}</h3>
                <CompactGroup group={group} locale={locale} />
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
              <CandidateDocsRailPanel candidateId={surface.candidate_id} pollingEnabled={false} />
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

function GroupBody({ group, locale }: { group: HrEmployeeRecordGroup; locale: 'en' | 'ru' | 'pl' }) {
  if (group.rows.length === 0) {
    return <p>{EMPTY_GROUP[group.id] || 'Nieuzupełnione'}</p>
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
  const [firstName, setFirstName] = useState(person?.first_name || '')
  const [lastName, setLastName] = useState(person?.last_name || '')
  const [birth, setBirth] = useState(person?.birth_date || '')
  const [citizenship, setCitizenship] = useState(person?.citizenship || '')
  const [phone, setPhone] = useState(person?.phone || '')
  const [email, setEmail] = useState(person?.email || '')
  const [address, setAddress] = useState(person?.address || '')
  const [pesel, setPesel] = useState(person?.pesel || '')
  const [languages, setLanguages] = useState(person?.languages || '')
  return (
    <form
      className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
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
      <Field label="Imię" value={firstName} onChange={setFirstName} />
      <Field label="Nazwisko" value={lastName} onChange={setLastName} />
      <Field label="Data urodzenia" value={birth} onChange={setBirth} type="date" />
      <Field label="Obywatelstwo" value={citizenship} onChange={setCitizenship} />
      <Field label="Telefon" value={phone} onChange={setPhone} />
      <Field label="Email" value={email} onChange={setEmail} />
      <Field label="Adres" value={address} onChange={setAddress} />
      <Field label="PESEL" value={pesel} onChange={setPesel} />
      <Field label="Języki" value={languages} onChange={setLanguages} />
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        Save
      </button>
    </form>
  )
}

function LegalForm({
  legal,
  saving,
  onSave,
}: {
  legal: HrEmployeeRecordSurface['legal']
  saving: boolean
  onSave: (body: HrDriverLegalIn) => void
}) {
  const [citizenshipClass, setCitizenshipClass] = useState(legal?.citizenship_class || 'third_country')
  const [stay, setStay] = useState(legal?.stay_basis && legal.stay_basis !== 'none' ? legal.stay_basis : 'none')
  const [basis, setBasis] = useState(legal?.work_authorization_basis || 'separate_required')
  const [valid, setValid] = useState(legal?.valid_for_this_employment || 'operator_verification')
  return (
    <form
      className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
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
      <SelectField label="Citizenship class" value={citizenshipClass} options={['pl', 'eu_eea_ch', 'third_country']} onChange={setCitizenshipClass} />
      <SelectField
        label="Podstawa pobytu"
        value={stay}
        options={['not_required', 'visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none']}
        onChange={setStay}
      />
      <SelectField label="Prawo do pracy" value={basis} options={['not_required', 'included_in_stay', 'separate_required']} onChange={setBasis} />
      <SelectField label="To Employment" value={valid} options={['yes', 'no', 'operator_verification']} onChange={setValid} />
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        Zweryfikuj
      </button>
    </form>
  )
}

function TermsForm({
  terms,
  saving,
  onSave,
}: {
  terms: HrEmployeeRecordSurface['terms']
  saving: boolean
  onSave: (body: HrDriverTermsIn) => void
}) {
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
      className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
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
      <Field label="Stanowisko" value={position} onChange={setPosition} />
      <Field label="Umowa" value={contractBasis} onChange={setContractBasis} />
      <Field label="Czas pracy" value={workTime} onChange={setWorkTime} />
      <Field label="Jednostka" value={workTimeUnit} onChange={setWorkTimeUnit} />
      <Field label="System pracy" value={workSystem} onChange={setWorkSystem} />
      <Field label="Miejsce pracy" value={workplace} onChange={setWorkplace} />
      <Field label="Stawka" value={amount} onChange={setAmount} />
      <Field label="Waluta" value={currency} onChange={setCurrency} />
      <Field label="Okres stawki" value={period} onChange={setPeriod} />
      <SelectField label="Okres" value={duration} options={['indefinite', 'fixed']} onChange={setDuration} />
      {duration === 'fixed' ? <Field label="Do" value={fixedEnd} onChange={setFixedEnd} type="date" /> : null}
      <SelectField label="Probation" value={probation} options={['none', 'dated']} onChange={setProbation} />
      {probation === 'dated' ? <Field label="Probation do" value={probationEnd} onChange={setProbationEnd} type="date" /> : null}
      <Field label="Planned start" value={planned} onChange={setPlanned} type="date" />
      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
        Save
      </button>
    </form>
  )
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
}) {
  return (
    <label>
      <div className="label">{label}</div>
      <input className="input" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
}) {
  return (
    <label>
      <div className="label">{label}</div>
      <select className="input" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {VALUE_LABELS[option] || option}
          </option>
        ))}
      </select>
    </label>
  )
}

function CompactGroup({ group, locale }: { group: HrEmployeeRecordGroup; locale: 'en' | 'ru' | 'pl' }) {
  const filled = group.rows.filter((row) => displayValue(row.value, row.label, locale) !== '—')
  if (group.id === 'dokumenty') {
    return (
      <Link to={CRM_APP_PATHS.documents} className="btn-secondary btn-sm">
        Open documents
      </Link>
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
