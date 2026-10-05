import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import { SearchableSelect } from '../../components/candidate/shared/FormComponents'
import { buildCountryOptions } from '../../data/countries'
import { useI18n } from '../../i18n'

const LICENCE_CATEGORIES = ['B', 'C', 'CE', 'C1', 'C1E', 'D', 'DE'] as const

const STAY_CHOICES = [
  ['visa_d', 'Wiza D'],
  ['visa_c', 'Wiza C'],
  ['karta_pobytu', 'Karta pobytu'],
  ['visa_free', 'Ruch bezwizowy'],
  ['waiting_for_trc', 'Oczekuje na kartę pobytu'],
  ['special_protection', 'Ochrona'],
  ['other', 'Inna'],
  ['none', 'Brak'],
] as const

const WORK_CHOICES = [
  ['work_permit', 'Zezwolenie na pracę'],
  ['oswiadczenie', 'Oświadczenie'],
  ['included_in_stay', 'Prawo do pracy wynika z pobytu'],
  ['not_required', 'Nie wymaga zezwolenia'],
  ['no_right', 'Brak prawa do pracy'],
] as const

type Step = {
  key: string
  visible: boolean
  stored?: string | null
  operator_label?: string | null
  visa_type?: string | null
  visa_purpose?: string | null
  work_authorization_basis?: string | null
  procedure_type?: string | null
  issuing_country?: string | null
  categories?: string[]
  valid_from?: string | null
  valid_to?: string | null
  conditions?: string | null
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
  if (step.operator_label) return step.operator_label
  if (step.work_authorization_basis === 'not_required') return 'not_required'
  if (step.work_authorization_basis === 'included_in_stay') return 'included_in_stay'
  if (step.work_authorization_basis === 'separate_required' && step.procedure_type === 'work_permit_a') {
    return 'work_permit'
  }
  if (step.work_authorization_basis === 'separate_required' && step.procedure_type === 'employer_declaration') {
    return 'oswiadczenie'
  }
  if (step.stored === 'no' && !step.work_authorization_basis) return 'no_right'
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
  const licence = stepOf(view, 'driving_licence')
  const code95 = stepOf(view, 'code95')
  const tacho = stepOf(view, 'tachograph')
  const adr = stepOf(view, 'adr')
  const stayCode = stay?.stored || ''
  const visaOpen = stayCode === 'visa_d' || stayCode === 'visa_c'
  const cardOpen = stayCode === 'karta_pobytu'
  const selectedWork = workLabel(work)
  const procedureOpen = selectedWork === 'work_permit' || selectedWork === 'oswiadczenie'
  const determined = view.citizenship_class === 'pl' || view.citizenship_class === 'eu_eea_ch'
  const licenceCountry = licence?.issuing_country || ''
  const licenceCountryLabel = countries.find((option) => option.value === licenceCountry)?.label || licenceCountry

  const unknownLabel = t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Nie wiadomo' })
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
  const field = (label: string, control: ReactNode, testId?: string) => (
    <label className="block" data-testid={testId}>
      <div className="label">{label}</div>
      {control}
    </label>
  )
  const choice = (
    value: string,
    options: readonly (readonly [string, string])[],
    onChange: (next: string) => void,
    testId: string,
  ) => (
    <select
      data-testid={testId}
      className="input"
      disabled={disabled}
      value={value || 'unknown'}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="unknown">{unknownLabel}</option>
      {options.map(([code, label]) => (
        <option key={code} value={code}>
          {label}
        </option>
      ))}
    </select>
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
      <option value="yes">{t('app.candidate_card.operator_facts.yes', { defaultValue: 'Tak' })}</option>
      <option value="no">{t('app.candidate_card.operator_facts.no', { defaultValue: 'Nie' })}</option>
    </select>
  )
  const dateInput = (value: string | null | undefined, onChange: (next: string) => void, testId: string) => (
    <input
      data-testid={testId}
      type="date"
      className="input"
      disabled={disabled}
      value={value || ''}
      onChange={(event) => onChange(event.target.value || 'unknown')}
    />
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
            t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Obywatelstwo' }),
            countrySelect(citizenship?.stored, (next) => onPatch({ citizenship: next }), 'operator-facts-citizenship-input'),
            'operator-facts-citizenship',
          )}

          {stay?.visible
            ? field(
                t('app.candidate_card.operator_facts.stay_question', {
                  defaultValue: 'Na jakiej podstawie przebywa w Polsce?',
                }),
                choice(stayCode, STAY_CHOICES, (next) => onPatch({ stay_basis: next }), 'operator-facts-stay-input'),
                'operator-facts-stay',
              )
            : null}

          {visaOpen ? (
            <div className="space-y-4 lg:col-span-2 lg:grid lg:grid-cols-2 lg:gap-4" data-testid="operator-facts-stay-parameters">
              {field(
                t('app.candidate_card.operator_facts.visa_type', { defaultValue: 'Typ wizy' }),
                <input
                  className="input"
                  disabled={disabled}
                  value={parameters?.visa_type || ''}
                  onChange={(event) => onPatch({ visa_type: event.target.value || 'unknown' })}
                />,
              )}
              {field(
                t('app.candidate_card.operator_facts.visa_purpose', { defaultValue: 'Cel wizy' }),
                <input
                  className="input"
                  disabled={disabled}
                  value={parameters?.visa_purpose || ''}
                  onChange={(event) => onPatch({ visa_purpose: event.target.value || 'unknown' })}
                />,
              )}
              {field(
                t('app.candidate_card.operator_facts.valid_to', { defaultValue: 'Ważna do' }),
                dateInput(stay?.valid_to, (next) => onPatch({ stay_valid_to: next }), 'operator-facts-stay-valid-to'),
              )}
            </div>
          ) : null}

          {cardOpen ? (
            <div className="space-y-4" data-testid="operator-facts-card-parameters">
              {field(
                t('app.candidate_card.operator_facts.card_valid_to', { defaultValue: 'Karta ważna do' }),
                dateInput(stay?.valid_to, (next) => onPatch({ stay_valid_to: next }), 'operator-facts-stay-valid-to'),
              )}
            </div>
          ) : null}
        </div>
      </section>

      {determined || work?.visible ? (
        <section className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4" data-testid="operator-facts-work-rights">
          <div className="text-sm font-semibold text-slate-900">
            {t('app.candidate_card.operator_facts.work_block', { defaultValue: 'Prawo do pracy' })}
          </div>
          <div className="mt-4 space-y-4">
            {determined ? (
              <p className="text-sm text-slate-800" data-testid="operator-facts-work-determined">
                {t('app.candidate_card.operator_facts.work_not_required', {
                  defaultValue: 'Pobyt i zezwolenie na pracę nie są wymagane.',
                })}
              </p>
            ) : null}
            {work?.visible
              ? field(
                  t('app.candidate_card.operator_facts.work_question', {
                    defaultValue: 'Na jakiej podstawie może pracować?',
                  }),
                  choice(selectedWork, WORK_CHOICES, (next) => onPatch({ work_label: next }), 'operator-facts-work-input'),
                  'operator-facts-work',
                )
              : null}
            {procedureOpen ? (
              <div className="space-y-4" data-testid="operator-facts-work-parameters">
                {field(
                  t('app.candidate_card.operator_facts.authorization_from', { defaultValue: 'Ważne od' }),
                  dateInput(
                    work?.valid_from,
                    (next) => onPatch({ authorization_valid_from: next }),
                    'operator-facts-authorization-from',
                  ),
                )}
                {field(
                  t('app.candidate_card.operator_facts.authorization_to', { defaultValue: 'Ważne do' }),
                  dateInput(
                    work?.valid_to,
                    (next) => onPatch({ authorization_valid_to: next }),
                    'operator-facts-authorization-to',
                  ),
                )}
                {field(
                  t('app.candidate_card.operator_facts.authorization_conditions', { defaultValue: 'Warunki' }),
                  <input
                    className="input"
                    disabled={disabled}
                    value={work?.conditions || ''}
                    onChange={(event) => onPatch({ authorization_conditions: event.target.value || 'unknown' })}
                  />,
                )}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4" data-testid="operator-facts-qualifications">
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_card.operator_facts.qualifications', { defaultValue: 'Uprawnienia kierowcy' })}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="space-y-4" data-testid="operator-facts-licence">
            {field(
              t('app.candidate_card.operator_facts.licence_country', { defaultValue: 'Prawo jazdy — kraj wydania' }),
              countrySelect(
                licence?.issuing_country,
                (next) => onPatch({ licence_issuing_country: next }),
                'operator-facts-licence-country',
              ),
            )}
            {licenceCountry ? (
              <div data-testid="operator-facts-licence-details">
                <div className="label">
                  {t('app.candidate_card.operator_facts.licence_categories', { defaultValue: 'Kategorie' })}
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
                <div className="mt-4">
                  {field(
                    t('app.candidate_card.operator_facts.licence_valid_to', { defaultValue: 'Ważne do' }),
                    dateInput(
                      licence?.valid_to,
                      (next) => onPatch({ licence_valid_to: next }),
                      'operator-facts-licence-valid-to',
                    ),
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <div className="space-y-4" data-testid="operator-facts-code95">
            {field(
              t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' }),
              presenceSelect(code95?.presence, (next) => onPatch({ code95_presence: next }), 'operator-facts-code95-presence'),
            )}
            {code95?.presence === true ? (
              <div className="space-y-4" data-testid="operator-facts-code95-details">
                <div>
                  <div className="label">
                    {t('app.candidate_card.operator_facts.code95_where', { defaultValue: 'Gdzie potwierdzony' })}
                  </div>
                  <p className="text-sm text-slate-800">{licenceCountryLabel || unknownLabel}</p>
                </div>
                {field(
                  t('app.candidate_card.operator_facts.code95_valid_to', { defaultValue: 'Ważny do' }),
                  dateInput(code95?.valid_to, (next) => onPatch({ code95_valid_to: next }), 'operator-facts-code95-valid-to'),
                )}
              </div>
            ) : null}
          </div>

          <div className="space-y-4" data-testid="operator-facts-tachograph">
            {field(
              t('app.candidate_card.operator_facts.tachograph', { defaultValue: 'Karta kierowcy' }),
              presenceSelect(tacho?.presence, (next) => onPatch({ tachograph_presence: next })),
            )}
            {tacho?.presence === true ? (
              <div className="space-y-4">
                {field(
                  t('app.candidate_card.operator_facts.tachograph_country', { defaultValue: 'Kraj' }),
                  countrySelect(
                    tacho?.issuing_country,
                    (next) => onPatch({ tachograph_issuing_country: next }),
                    'operator-facts-tacho-country',
                  ),
                )}
                {field(
                  t('app.candidate_card.operator_facts.tachograph_valid_to', { defaultValue: 'Ważna do' }),
                  dateInput(tacho?.valid_to, (next) => onPatch({ tachograph_valid_to: next }), 'operator-facts-tacho-valid-to'),
                )}
              </div>
            ) : null}
          </div>

          <div className="space-y-4" data-testid="operator-facts-adr">
            {field(
              t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' }),
              presenceSelect(adr?.presence, (next) => onPatch({ adr_presence: next })),
            )}
            {adr?.presence === true ? (
              <div className="space-y-4">
                {field(
                  t('app.candidate_card.operator_facts.adr_country', { defaultValue: 'Kraj' }),
                  countrySelect(adr?.issuing_country, (next) => onPatch({ adr_issuing_country: next }), 'operator-facts-adr-country'),
                )}
                {field(
                  t('app.candidate_card.operator_facts.adr_valid_to', { defaultValue: 'Ważne do' }),
                  dateInput(adr?.valid_to, (next) => onPatch({ adr_valid_to: next }), 'operator-facts-adr-valid-to'),
                )}
              </div>
            ) : null}
          </div>

          <div className="space-y-4" data-testid="operator-facts-medical">
            {field(
              t('app.candidate_card.operator_facts.medical', { defaultValue: 'Badania lekarskie' }),
              presenceSelect(stepOf(view, 'medical')?.presence, (next) => onPatch({ medical_presence: next })),
            )}
          </div>
          <div className="space-y-4" data-testid="operator-facts-psych">
            {field(
              t('app.candidate_card.operator_facts.psych', { defaultValue: 'Testy psychologiczne' }),
              presenceSelect(stepOf(view, 'psych')?.presence, (next) => onPatch({ psych_presence: next })),
            )}
          </div>
          <div className="space-y-4" data-testid="operator-facts-pesel">
            {field(
              t('app.candidate_card.operator_facts.pesel', { defaultValue: 'PESEL' }),
              presenceSelect(stepOf(view, 'pesel')?.presence, (next) => onPatch({ pesel_presence: next })),
            )}
            {stepOf(view, 'pesel')?.presence === true ? (
              field(
                t('app.candidate_card.operator_facts.pesel_number', { defaultValue: 'Numer PESEL' }),
                <input
                  className="input"
                  disabled={disabled}
                  value={stepOf(view, 'pesel')?.stored || ''}
                  onChange={(event) => onPatch({ pesel: event.target.value || 'unknown' })}
                />,
              )
            ) : null}
          </div>
          <div className="space-y-4" data-testid="operator-facts-additional">
            {field(
              t('app.candidate_card.operator_facts.additional', { defaultValue: 'Dodatkowy dokument' }),
              presenceSelect(stepOf(view, 'additional')?.presence, (next) => onPatch({ additional_presence: next })),
            )}
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
