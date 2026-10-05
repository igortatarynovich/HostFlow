import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  confirmHrDriverLegal,
  confirmHrDriverTerms,
  getHrDriverOperatorSurface,
  recordHrDriverReady,
  startHrDriverEmployment,
  type HrDriverActionResult,
  type HrDriverLegalIn,
  type HrDriverOperatorSurface,
  type HrDriverTermsIn,
} from '../../api/workforce'
import { useI18n } from '../../i18n'

type GroupId = 'identity' | 'legal_stay' | 'work_eligibility' | 'professional' | 'terms' | 'next' | 'ready'

const CITIZENSHIP = ['pl', 'eu_eea_ch', 'third_country'] as const
const STAY = [
  'not_required',
  'visa_d',
  'visa_c',
  'karta_pobytu',
  'visa_free',
  'waiting_for_trc',
  'special_protection',
  'other',
  'none',
] as const
const WORK = ['not_required', 'included_in_stay', 'separate_required'] as const
const VALID = ['yes', 'no', 'operator_verification'] as const

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

function defaultGroup(surface: HrDriverOperatorSurface): GroupId {
  const focus = surface.next_action?.focus
  if (focus === 'professional') return 'professional'
  if (focus === 'terms') return 'terms'
  if (focus === 'work_eligibility') return 'work_eligibility'
  if (focus === 'ready' || surface.ready_to_start.can_start) return 'ready'
  if (focus === 'next') return 'next'
  return 'identity'
}

function Row({
  label,
  value,
  open,
  onOpen,
}: {
  label: string
  value: string
  open: boolean
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`flex w-full items-baseline justify-between gap-4 border-b border-slate-100 px-4 py-3 text-left ${
        open ? 'bg-slate-50' : 'bg-white hover:bg-slate-50'
      }`}
    >
      <span className="text-xs font-semibold tracking-wide text-slate-500">{label}</span>
      <span className="text-sm text-slate-900">{value}</span>
    </button>
  )
}

export default function HrDriverOperatorSurface({
  employeeId,
  manage,
}: {
  employeeId: string
  manage: boolean
}) {
  const { t } = useI18n()
  const [surface, setSurface] = useState<HrDriverOperatorSurface | null>(null)
  const [open, setOpen] = useState<GroupId | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    const next = await getHrDriverOperatorSurface(employeeId)
    setSurface(next)
    setOpen((current) => current ?? defaultGroup(next))
  }, [employeeId])

  useEffect(() => {
    let cancelled = false
    setSurface(null)
    setOpen(null)
    setError(null)
    getHrDriverOperatorSurface(employeeId)
      .then((next) => {
        if (cancelled) return
        setSurface(next)
        setOpen(defaultGroup(next))
      })
      .catch(() => {
        if (!cancelled) setError(t('app.hr.driver_surface.load_error', { defaultValue: 'Could not load this employment.' }))
      })
    return () => {
      cancelled = true
    }
  }, [employeeId, t])

  const run = async (fn: () => Promise<HrDriverActionResult>) => {
    setSaving(true)
    setError(null)
    try {
      const result = await fn()
      const legalNotPass = Boolean(result.outcome && result.outcome !== 'pass')
      if (result.accepted === false || result.activated === false || legalNotPass) {
        setError(result.reason || t('app.hr.driver_surface.save_error', { defaultValue: 'Could not save.' }))
      }
      await load()
    } catch {
      setError(t('app.hr.driver_surface.save_error', { defaultValue: 'Could not save.' }))
    } finally {
      setSaving(false)
    }
  }

  if (error && !surface) {
    return <p className="text-sm text-rose-800">{error}</p>
  }
  if (!surface) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  const headerBits = [surface.header.name, surface.header.position, surface.header.employer].filter(Boolean)
  const professionalValue = surface.professional.defined
    ? `${surface.professional.satisfied}/${surface.professional.applicable}`
    : t('app.hr.driver_surface.not_materialized', { defaultValue: 'Not materialized' })
  const readyValue =
    surface.ready_to_start.status === 'pass'
      ? t('app.hr.driver_surface.ready', { defaultValue: 'Ready' })
      : surface.ready_to_start.status === 'active'
        ? t('app.hr.driver_surface.active', { defaultValue: 'Active' })
        : t('app.hr.driver_surface.blocked', { defaultValue: 'Blocked' })

  return (
    <section id="hr-verification" className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-4 py-4">
        <h2 className="text-lg font-semibold text-slate-950">{headerBits.join(' · ') || surface.header.name}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.hr.driver_surface.employment', { defaultValue: 'Employment' })}: {stateLabel(surface.state)}
          {' · '}
          {t('app.hr.driver_surface.planned_start', { defaultValue: 'Planned start' })}: {formatDay(surface.header.planned_start)}
        </p>
      </header>

      <Row
        label={t('app.hr.driver_surface.identity', { defaultValue: 'Identity' })}
        value={
          surface.identity.complete
            ? t('app.hr.driver_surface.complete', { defaultValue: 'Complete' })
            : t('app.hr.driver_surface.incomplete', { defaultValue: 'Incomplete' })
        }
        open={open === 'identity'}
        onOpen={() => setOpen('identity')}
      />
      {open === 'identity' ? <IdentityPanel surface={surface} /> : null}

      <Row
        label={t('app.hr.driver_surface.legal_stay', { defaultValue: 'Legal stay' })}
        value={
          surface.legal_stay.status === 'valid'
            ? t('app.hr.driver_surface.valid', { defaultValue: 'Valid' })
            : t('app.hr.driver_surface.unknown', { defaultValue: 'Unknown' })
        }
        open={open === 'legal_stay'}
        onOpen={() => setOpen('legal_stay')}
      />
      {open === 'legal_stay' ? (
        <Panel>
          <Fact label={t('app.hr.driver_surface.basis', { defaultValue: 'Basis' })} value={surface.legal_stay.basis} />
        </Panel>
      ) : null}

      <Row
        label={t('app.hr.driver_surface.work_eligibility', { defaultValue: 'Work eligibility' })}
        value={
          surface.work_eligibility.status === 'eligible'
            ? t('app.hr.driver_surface.eligible', { defaultValue: 'Eligible' })
            : t('app.hr.driver_surface.permit_pending', { defaultValue: 'Permit pending' })
        }
        open={open === 'work_eligibility'}
        onOpen={() => setOpen('work_eligibility')}
      />
      {open === 'work_eligibility' ? (
        <WorkPanel surface={surface} manage={manage} saving={saving} onSave={(body) => void run(() => confirmHrDriverLegal(employeeId, body))} />
      ) : null}

      <Row
        label={t('app.hr.driver_surface.professional', { defaultValue: 'Professional readiness' })}
        value={professionalValue}
        open={open === 'professional'}
        onOpen={() => setOpen('professional')}
      />
      {open === 'professional' ? <ProfessionalPanel surface={surface} /> : null}

      <Row
        label={t('app.hr.driver_surface.terms', { defaultValue: 'Employment terms' })}
        value={
          surface.terms?.complete
            ? t('app.hr.driver_surface.confirmed', { defaultValue: 'Confirmed' })
            : t('app.hr.driver_surface.open', { defaultValue: 'Open' })
        }
        open={open === 'terms'}
        onOpen={() => setOpen('terms')}
      />
      {open === 'terms' ? (
        <TermsPanel surface={surface} manage={manage} saving={saving} onSave={(body) => void run(() => confirmHrDriverTerms(employeeId, body))} />
      ) : null}

      <div className="border-t border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-xs font-semibold tracking-wide text-slate-500">
          {t('app.hr.driver_surface.next_action', { defaultValue: 'Next action' })}
        </p>
        {surface.next_action ? (
          <>
            <p className="mt-1 text-base font-semibold text-slate-950">{surface.next_action.title}</p>
            <p className="mt-1 text-sm text-slate-600">{surface.next_action.reason}</p>
            {surface.next_action.code === 'register_zus' ? (
              <Link className="mt-3 inline-flex rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white" to={CRM_APP_PATHS.hrZusWorkspace}>
                {t('app.hr.driver_surface.register_zus', { defaultValue: 'Register / complete ZUS' })}
              </Link>
            ) : null}
            {surface.next_action.code === 'record_ready' && manage ? (
              <button
                type="button"
                disabled={saving}
                className="mt-3 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                onClick={() => void run(() => recordHrDriverReady(employeeId))}
              >
                {t('app.hr.driver_surface.record_ready', { defaultValue: 'Record Ready to Start' })}
              </button>
            ) : null}
            {surface.next_action.code !== 'register_zus' &&
            surface.next_action.code !== 'start_employment' &&
            surface.next_action.code !== 'record_ready' ? (
              <button
                type="button"
                className="mt-3 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900"
                onClick={() => setOpen(defaultGroup({ ...surface, ready_to_start: { ...surface.ready_to_start, can_start: false } }))}
              >
                {surface.next_action.title}
              </button>
            ) : null}
          </>
        ) : (
          <p className="mt-1 text-sm text-slate-600">
            {surface.state === 'active'
              ? t('app.hr.driver_surface.already_active', { defaultValue: 'This employment is active.' })
              : t('app.hr.driver_surface.no_action', { defaultValue: 'No single next action for this case.' })}
          </p>
        )}
      </div>

      <Row
        label={t('app.hr.driver_surface.ready_to_start', { defaultValue: 'Ready to start' })}
        value={readyValue}
        open={open === 'ready'}
        onOpen={() => setOpen('ready')}
      />
      {surface.ready_to_start.reasons.length > 0 ? (
        <p className="border-b border-slate-100 px-4 py-2 text-sm text-slate-600">{surface.ready_to_start.reasons.join(' · ')}</p>
      ) : null}
      {open === 'ready' && surface.ready_to_start.can_start && manage ? (
        <Panel>
          <button
            type="button"
            disabled={saving}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            onClick={() => void run(() => startHrDriverEmployment(employeeId))}
          >
            {t('app.hr.driver_surface.start_employment', { defaultValue: 'Start employment' })}
          </button>
        </Panel>
      ) : null}
      {error ? <p className="px-4 py-3 text-sm text-rose-800">{error}</p> : null}
    </section>
  )
}

function Panel({ children }: { children: ReactNode }) {
  return <div className="space-y-3 border-b border-slate-100 bg-white px-4 py-4">{children}</div>
}

function Fact({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <p className="text-sm text-slate-800">
      <span className="text-slate-500">{label}</span>
      <span className="mx-2 text-slate-300">·</span>
      {value || '—'}
    </p>
  )
}

function IdentityPanel({ surface }: { surface: HrDriverOperatorSurface }) {
  return (
    <Panel>
      <Fact label="Name" value={[surface.identity.first_name, surface.identity.last_name].filter(Boolean).join(' ')} />
      <Fact label="Birth date" value={formatDay(surface.identity.birth_date)} />
      <Fact label="Citizenship" value={surface.identity.citizenship} />
    </Panel>
  )
}

function ProfessionalPanel({ surface }: { surface: HrDriverOperatorSurface }) {
  if (!surface.professional.defined) {
    return (
      <Panel>
        <p className="text-sm text-slate-600">The requirement set for this employment is not materialized.</p>
      </Panel>
    )
  }
  return (
    <Panel>
      <ul className="space-y-2">
        {surface.professional.facts.map((fact) => (
          <li key={fact.key} className="flex items-baseline justify-between gap-4 text-sm">
            <span className="text-slate-900">{fact.label}</span>
            <span className="text-slate-600">
              {fact.not_applicable
                ? 'Not required'
                : fact.resolution === 'satisfied'
                  ? fact.evidence_linked
                    ? 'Confirmed · evidence linked'
                    : 'Confirmed'
                  : fact.resolution === 'waived'
                    ? 'Waived'
                    : fact.resolution === 'blocking'
                      ? fact.blocking_reason || 'Blocking'
                      : 'Open'}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function WorkPanel({
  surface,
  manage,
  saving,
  onSave,
}: {
  surface: HrDriverOperatorSurface
  manage: boolean
  saving: boolean
  onSave: (body: HrDriverLegalIn) => void
}) {
  const work = surface.work_eligibility
  const [citizenship, setCitizenship] = useState(work.citizenship_class || 'third_country')
  const [stay, setStay] = useState(surface.legal_stay.basis && surface.legal_stay.basis !== 'none' ? surface.legal_stay.basis : 'none')
  const [basis, setBasis] = useState(work.basis || 'separate_required')
  const [valid, setValid] = useState(work.valid_for_this_employment || 'operator_verification')
  return (
    <Panel>
      <Fact label="Basis" value={work.basis} />
      <Fact label="Valid for this employment" value={work.valid_for_this_employment} />
      {!work.checkpoint_context_complete ? (
        <p className="text-sm text-amber-900">
          The checkpoint context is incomplete. This employment needs a client, a vacancy, and a planned start on the terms. The planned start is not written as the actual start.
        </p>
      ) : null}
      {manage && surface.state === 'preparing' ? (
        <form
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            onSave({
              citizenship_class: citizenship,
              stay_basis: stay,
              work_authorization_basis: basis,
              valid_for_this_employment: valid,
            })
          }}
        >
          <Select label="Citizenship class" value={citizenship} options={CITIZENSHIP} onChange={setCitizenship} />
          <Select label="Stay basis" value={stay} options={STAY} onChange={setStay} />
          <Select label="Work authorization" value={basis} options={WORK} onChange={setBasis} />
          <Select label="Valid for this employment" value={valid} options={VALID} onChange={setValid} />
          <button type="submit" disabled={saving} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2">
            Confirm legal eligibility
          </button>
        </form>
      ) : null}
    </Panel>
  )
}

function TermsPanel({
  surface,
  manage,
  saving,
  onSave,
}: {
  surface: HrDriverOperatorSurface
  manage: boolean
  saving: boolean
  onSave: (body: HrDriverTermsIn) => void
}) {
  const terms = surface.terms
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
    <Panel>
      <Fact label="Position" value={terms?.position} />
      <Fact label="Contract" value={terms?.contract_basis} />
      <Fact label="Work time" value={terms ? `${terms.work_time_value || '—'} ${terms.work_time_unit || ''}` : null} />
      <Fact label="Work system" value={terms?.work_system} />
      <Fact label="Place" value={terms?.workplace} />
      <Fact
        label="Rate"
        value={terms ? `${terms.compensation_amount || '—'} ${terms.compensation_currency || ''} / ${terms.compensation_unit || ''}` : null}
      />
      <Fact label="Term" value={terms?.duration === 'fixed' ? `Fixed until ${formatDay(terms.fixed_term_end)}` : terms?.duration} />
      <Fact label="Probation" value={terms?.probation_status === 'dated' ? formatDay(terms.probation_end) : terms?.probation_status} />
      <Fact label="Planned start" value={formatDay(terms?.intended_start_date)} />
      {manage && surface.state === 'preparing' ? (
        <form
          className="grid gap-3 sm:grid-cols-2"
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
          <Field label="Position" value={position} onChange={setPosition} />
          <Field label="Contract" value={contractBasis} onChange={setContractBasis} />
          <Field label="Work time" value={workTime} onChange={setWorkTime} />
          <Field label="Work time unit" value={workTimeUnit} onChange={setWorkTimeUnit} />
          <Field label="Work system" value={workSystem} onChange={setWorkSystem} />
          <Field label="Place" value={workplace} onChange={setWorkplace} />
          <Field label="Rate" value={amount} onChange={setAmount} />
          <Field label="Currency" value={currency} onChange={setCurrency} />
          <Field label="Period" value={period} onChange={setPeriod} />
          <Select label="Term" value={duration} options={['indefinite', 'fixed']} onChange={setDuration} />
          {duration === 'fixed' ? <Field label="Fixed term end" value={fixedEnd} onChange={setFixedEnd} type="date" /> : null}
          <Select label="Probation" value={probation} options={['none', 'dated']} onChange={setProbation} />
          {probation === 'dated' ? <Field label="Probation end" value={probationEnd} onChange={setProbationEnd} type="date" /> : null}
          <Field label="Planned start" value={planned} onChange={setPlanned} type="date" />
          <button type="submit" disabled={saving} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2">
            Confirm employment terms
          </button>
        </form>
      ) : null}
    </Panel>
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
    <label className="block text-sm text-slate-700">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
      />
    </label>
  )
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: readonly string[]
  onChange: (value: string) => void
}) {
  return (
    <label className="block text-sm text-slate-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}
