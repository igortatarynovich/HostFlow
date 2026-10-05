import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import { SearchableSelect } from '../../components/candidate/shared/FormComponents'
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
  legal_eligibility?: {
    outcome?: string | null
    policy_id?: string | null
  } | null
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

  const unknownLabel = t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })
  const countryOptions = useMemo(
    () => [{ value: 'unknown', label: unknownLabel }, ...countries],
    [countries, unknownLabel],
  )
  const countrySelect = (value: string | null | undefined, onChange: (next: string) => void, testId: string) => (
    <div data-testid={testId}>
      <SearchableSelect
        options={countryOptions}
        value={value || 'unknown'}
        onChange={onChange}
        disabled={disabled}
        placeholder={t('app.candidate_card.select.empty')}
        searchPlaceholder={t('app.candidate_card.select.search')}
        noResultsLabel={t('app.candidate_card.select.no_results')}
      />
    </div>
  )
  const field = (label: string, control: ReactNode, testId?: string, hint?: ReactNode) => (
    <label className="block" data-testid={testId}>
      <div className="label">{label}</div>
      {control}
      {hint}
    </label>
  )
  const presenceSelect = (
    value: boolean | null | undefined,
    onChange: (next: true | false | 'unknown') => void,
    testId?: string,
  ) => (
    <select
      data-testid={testId}
      className="input"
      disabled={disabled}
      value={value === true ? 'yes' : value === false ? 'no' : 'unknown'}
      onChange={(event) => {
        const next = event.target.value
        onChange(next === 'yes' ? true : next === 'no' ? false : 'unknown')
      }}
    >
      <option value="unknown">{unknownLabel}</option>
      <option value="yes">{t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })}</option>
      <option value="no">{t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })}</option>
    </select>
  )

  const legalStatus =
    view.legal_eligibility?.outcome ||
    view.chain?.valid_for_this_employment ||
    (valid?.visible ? valid.stored : null) ||
    null

  const hint = (text: string, testId?: string) => (
    <p className="mt-1 text-xs text-slate-500" data-testid={testId}>
      {text}
    </p>
  )

  return (
    <div className="space-y-4" data-testid="operator-facts-form">
      <section className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4" data-testid="operator-facts-driver">
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_card.operator_facts.driver_block', {
            defaultValue: 'Dane i uprawnienia kierowcy',
          })}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
      {field(
        t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Citizenship' }),
        countrySelect(citizenship?.stored, (next) => onPatch({ citizenship: next }), 'operator-facts-citizenship-input'),
        'operator-facts-citizenship',
      )}

      {stay?.visible
        ? field(
            t('app.candidate_card.operator_facts.stay', { defaultValue: 'Stay basis' }),
            <select
              data-testid="operator-facts-stay-input"
              className="input"
              disabled={disabled}
              value={stay.stored || 'unknown'}
              onChange={(event) => onPatch({ stay_basis: event.target.value })}
            >
              <option value="unknown">{unknownLabel}</option>
              {['visa_d', 'visa_c', 'karta_pobytu', 'visa_free', 'waiting_for_trc', 'special_protection', 'other', 'none'].map((code) => (
                <option key={code} value={code}>
                  {t(`app.candidate_card.operator_facts.stay_${code}`, { defaultValue: code })}
                </option>
              ))}
            </select>,
            'operator-facts-stay',
          )
        : null}

      {parameters?.visible ? (
        <div className="contents" data-testid="operator-facts-stay-parameters">
          {field(
            t('app.candidate_card.operator_facts.visa_type', { defaultValue: 'Visa type' }),
            <input
              className="input"
              disabled={disabled}
              value={parameters.visa_type || ''}
              onChange={(event) => onPatch({ visa_type: event.target.value || 'unknown' })}
            />,
          )}
          {field(
            t('app.candidate_card.operator_facts.visa_purpose', { defaultValue: 'Visa purpose' }),
            <input
              className="input"
              disabled={disabled}
              value={parameters.visa_purpose || ''}
              onChange={(event) => onPatch({ visa_purpose: event.target.value || 'unknown' })}
            />,
          )}
        </div>
      ) : null}

      <div className="lg:col-span-2 grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="operator-facts-licence">
        {field(
          t('app.candidate_card.operator_facts.licence_country', { defaultValue: 'Driving licence issuing country' }),
          countrySelect(
            licence?.issuing_country,
            (next) => onPatch({ licence_issuing_country: next }),
            'operator-facts-licence-country',
          ),
        )}
        <div>
          <div className="label">
            {t('app.candidate_card.operator_facts.licence_categories', { defaultValue: 'Category' })}
          </div>
          <div className="flex flex-wrap gap-3">
            {LICENCE_CATEGORIES.map((code) => {
              const selected = (licence?.categories ?? []).includes(code)
              return (
                <label key={code} className="flex items-center gap-2">
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
                  <span>{code}</span>
                </label>
              )
            })}
          </div>
        </div>
      </div>

      {field(
        t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' }),
        presenceSelect(code95?.presence, (next) => onPatch({ code95_presence: next }), 'operator-facts-code95-presence'),
        'operator-facts-code95',
        <>
          {hint(
            shape === 'shared'
              ? t('app.candidate_card.operator_facts.shared', { defaultValue: 'Shared evidence: one licence for CE and Code 95' })
              : shape === 'separate'
                ? t('app.candidate_card.operator_facts.separate', { defaultValue: 'Separate evidence: licence and qualification card' })
                : t('app.candidate_card.operator_facts.no_file', { defaultValue: 'No file is requested' }),
            'operator-facts-evidence',
          )}
          {uploads.length > 0 ? (
            <p className="mt-1 text-xs text-slate-500" data-testid="operator-facts-uploads">
              {uploads.join(', ')}
            </p>
          ) : (
            <p className="sr-only" data-testid="operator-facts-uploads-empty">
              {t('app.candidate_card.operator_facts.no_file', { defaultValue: 'No file is requested' })}
            </p>
          )}
        </>,
      )}

      <div className="lg:col-span-2 grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="operator-facts-tachograph">
        {field(
          t('app.candidate_card.operator_facts.tachograph', { defaultValue: 'Tachograph card' }),
          presenceSelect(tacho?.presence, (next) => onPatch({ tachograph_presence: next })),
          undefined,
          hint(t('app.candidate_card.operator_facts.fact_only', { defaultValue: 'Recorded as a fact. No file is requested.' })),
        )}
        {field(
          t('app.candidate_card.operator_facts.tachograph_country', { defaultValue: 'Issuing country' }),
          countrySelect(
            tacho?.issuing_country,
            (next) => onPatch({ tachograph_issuing_country: next }),
            'operator-facts-tacho-country',
          ),
        )}
      </div>

      <div className="lg:col-span-2 grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="operator-facts-adr">
        {field(
          t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' }),
          presenceSelect(adr?.presence, (next) => onPatch({ adr_presence: next })),
          undefined,
          hint(t('app.candidate_card.operator_facts.fact_only', { defaultValue: 'Recorded as a fact. No file is requested.' })),
        )}
        {field(
          t('app.candidate_card.operator_facts.adr_country', { defaultValue: 'Issuing country' }),
          countrySelect(adr?.issuing_country, (next) => onPatch({ adr_issuing_country: next }), 'operator-facts-adr-country'),
        )}
      </div>
        </div>
      </section>

      <section className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4" data-testid="operator-facts-work-rights">
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_card.operator_facts.work_block', { defaultValue: 'Prawo do pracy' })}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {work?.visible
          ? field(
              t('app.candidate_card.operator_facts.work', { defaultValue: 'Podstawa pracy' }),
              <select
                data-testid="operator-facts-work-input"
                className="input"
                disabled={disabled}
                value={workLabel(work)}
                onChange={(event) => onPatch({ work_label: event.target.value })}
              >
                <option value="unknown">{unknownLabel}</option>
                <option value="work_permit">
                  {t('app.candidate_card.operator_facts.work_permit', { defaultValue: 'Work permit' })}
                </option>
                <option value="oswiadczenie">
                  {t('app.candidate_card.operator_facts.oswiadczenie', { defaultValue: 'Oświadczenie' })}
                </option>
                <option value="included_in_stay">
                  {t('app.candidate_card.operator_facts.included_in_stay', { defaultValue: 'Right to work is included in the stay' })}
                </option>
              </select>,
              'operator-facts-work',
              work.procedure_type
                ? hint(
                    `${t('app.candidate_card.operator_facts.procedure', { defaultValue: 'Typ procedury' })}: ${work.procedure_type}`,
                    'operator-facts-procedure',
                  )
                : null,
            )
          : null}
        {valid?.visible ? (
          <label className="flex items-center gap-2" data-testid="operator-facts-valid">
            <input
              type="checkbox"
              data-testid="operator-facts-valid-no"
              disabled={disabled}
              checked={valid.stored === 'no'}
              onChange={(event) =>
                onPatch({ valid_for_this_employment: event.target.checked ? 'no' : 'unknown' })
              }
            />
            <span>{t('app.candidate_card.operator_facts.valid_no', { defaultValue: 'Not valid for this employment' })}</span>
          </label>
        ) : null}
        <div data-testid="operator-facts-legal-status">
          <div className="label">
            {t('app.candidate_card.operator_facts.legal_status', { defaultValue: 'Status Legal Eligibility' })}
          </div>
          <p className="text-sm text-slate-800">
            {legalStatus || unknownLabel}
          </p>
        </div>
        </div>
      </section>
    </div>
  )
}

export default function OperatorFactsSurface({
  candidateId,
  onSaved,
}: {
  candidateId: string
  onSaved?: (view: OperatorFactsView) => void
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
        onSaved?.(response.data)
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
    <div className="space-y-4" data-testid="operator-facts-surface">
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      {view ? <OperatorFactsForm view={view} disabled={busy} onPatch={(patch) => void onPatch(patch)} /> : null}
    </div>
  )
}
