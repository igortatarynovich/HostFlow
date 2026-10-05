import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import { buildCountryOptions } from '../../data/countries'
import { useI18n } from '../../i18n'

const LICENCE_CATEGORIES = ['B', 'C', 'CE', 'C1', 'C1E', 'D', 'DE'] as const

type Step = {
  key: string
  visible: boolean
  stored?: string | null
  visa_type?: string | null
  visa_purpose?: string | null
  work_authorization_basis?: string | null
  procedure_type?: string | null
  issuing_country?: string | null
  categories?: string[]
  valid_to?: string | null
  presence?: boolean | null
  evidence_shape?: string | null
  asks_file?: boolean
}

export type OperatorFactsView = {
  citizenship_class?: string | null
  chain?: Record<string, string | null>
  steps: Step[]
  ce_code95?: {
    progress?: string | null
    evidence_shape?: string | null
    evidence_variant?: string | null
    upload_codes?: string[]
    asks_file?: boolean
  }
  upload_codes?: string[]
  asks_file?: boolean
}

type Patch = Record<string, unknown>

function stepOf(view: OperatorFactsView, key: string): Step | undefined {
  return view.steps.find((step) => step.key === key)
}

function workLabel(step: Step | undefined): string {
  if (!step) return 'unknown'
  if (step.work_authorization_basis === 'included_in_stay') return 'included_in_stay'
  if (step.work_authorization_basis === 'separate_required' && step.procedure_type === 'work_permit_a') {
    return 'work_permit'
  }
  if (step.work_authorization_basis === 'separate_required' && step.procedure_type === 'employer_declaration') {
    return 'oswiadczenie'
  }
  return 'unknown'
}

export function OperatorFactsForm({
  view,
  disabled,
  onPatch,
}: {
  view: OperatorFactsView
  disabled?: boolean
  onPatch: (patch: Patch) => void
}) {
  const { t, locale } = useI18n()
  const countries = useMemo(() => buildCountryOptions(locale), [locale])
  const citizenship = stepOf(view, 'citizenship')
  const stay = stepOf(view, 'stay_basis')
  const parameters = stepOf(view, 'stay_parameters')
  const work = stepOf(view, 'work')
  const valid = stepOf(view, 'valid_for_this_employment')
  const licence = stepOf(view, 'driving_licence')
  const code95 = stepOf(view, 'code95')
  const tacho = stepOf(view, 'tachograph')
  const adr = stepOf(view, 'adr')
  const uploads = view.upload_codes ?? view.ce_code95?.upload_codes ?? []
  const shape = view.ce_code95?.evidence_shape ?? code95?.evidence_shape ?? null

  const countrySelect = (value: string | null | undefined, onChange: (next: string) => void, testId: string) => (
    <select
      data-testid={testId}
      className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
      disabled={disabled}
      value={value || 'unknown'}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
      {countries.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )

  return (
    <div className="space-y-4" data-testid="operator-facts-form">
      <section data-testid="operator-facts-citizenship">
        <label className="block text-xs font-medium text-slate-700">
          {t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Citizenship' })}
        </label>
        {countrySelect(citizenship?.stored, (next) => onPatch({ citizenship: next }), 'operator-facts-citizenship-input')}
      </section>

      {stay?.visible ? (
        <section data-testid="operator-facts-stay">
          <label className="block text-xs font-medium text-slate-700">
            {t('app.candidate_card.operator_facts.stay', { defaultValue: 'Stay basis' })}
          </label>
          <select
            data-testid="operator-facts-stay-input"
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            disabled={disabled}
            value={stay.stored || 'unknown'}
            onChange={(event) => onPatch({ stay_basis: event.target.value })}
          >
            <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
            {['visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none'].map((code) => (
              <option key={code} value={code}>
                {t(`app.candidate_card.operator_facts.stay_${code}`, { defaultValue: code })}
              </option>
            ))}
          </select>
        </section>
      ) : null}

      {parameters?.visible ? (
        <section data-testid="operator-facts-stay-parameters" className="grid gap-2 sm:grid-cols-2">
          <label className="block text-xs font-medium text-slate-700">
            {t('app.candidate_card.operator_facts.visa_type', { defaultValue: 'Visa type' })}
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              disabled={disabled}
              value={parameters.visa_type || ''}
              onChange={(event) => onPatch({ visa_type: event.target.value || 'unknown' })}
            />
          </label>
          <label className="block text-xs font-medium text-slate-700">
            {t('app.candidate_card.operator_facts.visa_purpose', { defaultValue: 'Visa purpose' })}
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              disabled={disabled}
              value={parameters.visa_purpose || ''}
              onChange={(event) => onPatch({ visa_purpose: event.target.value || 'unknown' })}
            />
          </label>
        </section>
      ) : null}

      {work?.visible ? (
        <section data-testid="operator-facts-work">
          <label className="block text-xs font-medium text-slate-700">
            {t('app.candidate_card.operator_facts.work', { defaultValue: 'Work authorization' })}
          </label>
          <select
            data-testid="operator-facts-work-input"
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            disabled={disabled}
            value={workLabel(work)}
            onChange={(event) => onPatch({ work_label: event.target.value })}
          >
            <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
            <option value="work_permit">
              {t('app.candidate_card.operator_facts.work_permit', { defaultValue: 'Work permit' })}
            </option>
            <option value="oswiadczenie">
              {t('app.candidate_card.operator_facts.oswiadczenie', { defaultValue: 'Oświadczenie' })}
            </option>
            <option value="included_in_stay">
              {t('app.candidate_card.operator_facts.included_in_stay', { defaultValue: 'Right to work is included in the stay' })}
            </option>
          </select>
        </section>
      ) : null}

      {valid?.visible ? (
        <section data-testid="operator-facts-valid">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              data-testid="operator-facts-valid-no"
              disabled={disabled}
              checked={valid.stored === 'no'}
              onChange={(event) =>
                onPatch({ valid_for_this_employment: event.target.checked ? 'no' : 'unknown' })
              }
            />
            {t('app.candidate_card.operator_facts.valid_no', { defaultValue: 'Not valid for this employment' })}
          </label>
        </section>
      ) : null}

      <section data-testid="operator-facts-licence">
        <label className="block text-xs font-medium text-slate-700">
          {t('app.candidate_card.operator_facts.licence_country', { defaultValue: 'Driving licence issuing country' })}
        </label>
        {countrySelect(
          licence?.issuing_country,
          (next) => onPatch({ licence_issuing_country: next }),
          'operator-facts-licence-country',
        )}
        <div className="mt-2 flex flex-wrap gap-2">
          {LICENCE_CATEGORIES.map((code) => {
            const selected = (licence?.categories ?? []).includes(code)
            return (
              <label key={code} className="flex items-center gap-1 text-xs text-slate-700">
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={selected}
                  onChange={() => {
                    const current = new Set(licence?.categories ?? [])
                    if (selected) current.delete(code)
                    else current.add(code)
                    onPatch({ licence_categories: current.size ? Array.from(current) : 'unknown' })
                  }}
                />
                {code}
              </label>
            )
          })}
        </div>
      </section>

      <section data-testid="operator-facts-code95">
        <label className="block text-xs font-medium text-slate-700">
          {t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' })}
        </label>
        <select
          data-testid="operator-facts-code95-presence"
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          disabled={disabled}
          value={code95?.presence === true ? 'yes' : code95?.presence === false ? 'no' : 'unknown'}
          onChange={(event) => {
            const next = event.target.value
            onPatch({ code95_presence: next === 'yes' ? true : next === 'no' ? false : 'unknown' })
          }}
        >
          <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
          <option value="yes">{t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })}</option>
          <option value="no">{t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })}</option>
        </select>
        <p className="mt-1 text-xs text-slate-500" data-testid="operator-facts-evidence">
          {shape === 'shared'
            ? t('app.candidate_card.operator_facts.shared', { defaultValue: 'Shared evidence: one licence for CE and Code 95' })
            : shape === 'separate'
              ? t('app.candidate_card.operator_facts.separate', { defaultValue: 'Separate evidence: licence and qualification card' })
              : t('app.candidate_card.operator_facts.no_file', { defaultValue: 'No file is requested' })}
        </p>
        {uploads.length > 0 ? (
          <p className="text-xs text-slate-600" data-testid="operator-facts-uploads">
            {uploads.join(', ')}
          </p>
        ) : (
          <p className="sr-only" data-testid="operator-facts-uploads-empty">
            {t('app.candidate_card.operator_facts.no_file', { defaultValue: 'No file is requested' })}
          </p>
        )}
      </section>

      <section data-testid="operator-facts-tachograph">
        <label className="block text-xs font-medium text-slate-700">
          {t('app.candidate_card.operator_facts.tachograph', { defaultValue: 'Tachograph card' })}
        </label>
        <select
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          disabled={disabled}
          value={tacho?.presence === true ? 'yes' : tacho?.presence === false ? 'no' : 'unknown'}
          onChange={(event) => {
            const next = event.target.value
            onPatch({ tachograph_presence: next === 'yes' ? true : next === 'no' ? false : 'unknown' })
          }}
        >
          <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
          <option value="yes">{t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })}</option>
          <option value="no">{t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })}</option>
        </select>
        {countrySelect(
          tacho?.issuing_country,
          (next) => onPatch({ tachograph_issuing_country: next }),
          'operator-facts-tacho-country',
        )}
        <p className="mt-1 text-xs text-slate-500">
          {t('app.candidate_card.operator_facts.fact_only', { defaultValue: 'Recorded as a fact. No file is requested.' })}
        </p>
      </section>

      <section data-testid="operator-facts-adr">
        <label className="block text-xs font-medium text-slate-700">
          {t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' })}
        </label>
        <select
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          disabled={disabled}
          value={adr?.presence === true ? 'yes' : adr?.presence === false ? 'no' : 'unknown'}
          onChange={(event) => {
            const next = event.target.value
            onPatch({ adr_presence: next === 'yes' ? true : next === 'no' ? false : 'unknown' })
          }}
        >
          <option value="unknown">{t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })}</option>
          <option value="yes">{t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })}</option>
          <option value="no">{t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })}</option>
        </select>
        {countrySelect(adr?.issuing_country, (next) => onPatch({ adr_issuing_country: next }), 'operator-facts-adr-country')}
        <p className="mt-1 text-xs text-slate-500">
          {t('app.candidate_card.operator_facts.fact_only', { defaultValue: 'Recorded as a fact. No file is requested.' })}
        </p>
      </section>
    </div>
  )
}

export default function OperatorFactsSurface({
  candidateId,
  onSaved,
}: {
  candidateId: string
  onSaved?: () => void
}) {
  const { t } = useI18n()
  const [view, setView] = useState<OperatorFactsView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const response = await api.get<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`)
    setView(response.data)
  }, [candidateId])

  useEffect(() => {
    let cancelled = false
    setError(null)
    void api
      .get<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`)
      .then((response) => {
        if (!cancelled) setView(response.data)
      })
      .catch(() => {
        if (!cancelled) {
          setError(t('app.candidate_card.operator_facts.load_failed', { defaultValue: 'Could not load facts' }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [candidateId, t])

  const onPatch = useCallback(
    async (patch: Patch) => {
      setBusy(true)
      setError(null)
      try {
        const response = await api.put<OperatorFactsView>(`/candidates/${candidateId}/operator-facts`, patch)
        setView(response.data)
        onSaved?.()
      } catch {
        setError(t('app.candidate_card.operator_facts.save_failed', { defaultValue: 'Could not save facts' }))
        await load()
      } finally {
        setBusy(false)
      }
    },
    [candidateId, load, onSaved, t],
  )

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="operator-facts-surface">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">
        {t('app.candidate_card.operator_facts.title', { defaultValue: 'Candidate facts' })}
      </h2>
      {error ? <p className="mb-2 text-xs text-red-600">{error}</p> : null}
      {view ? <OperatorFactsForm view={view} disabled={busy} onPatch={(patch) => void onPatch(patch)} /> : null}
    </section>
  )
}
