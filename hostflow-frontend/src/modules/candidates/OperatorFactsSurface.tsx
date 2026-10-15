import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import { CardAccordion, joinParts } from '../../components/candidate/card/CandidateCardChrome'
import { ReadFieldRows } from '../../components/ui/ReadFieldRows'
import { ChipFieldEditor } from '../../components/ui/ChipFieldEditor'
import { FieldGrid } from '../../components/ui/FieldGrid'
import { InlineFieldRow } from '../../components/ui/InlineFieldRow'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { LegalizationStatus } from '../../components/ui/documentRequirement/LegalizationStatus'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import { SearchableSelect } from '../../components/candidate/shared/FormComponents'
import DateInput from '../../components/controls/DateInput'
import { useI18n } from '../../i18n'
import { formatDateSafe } from './candidateUtils'
import { countryFlag } from '../candidate-card/utils'

type CountryOption = { value: string; label: string }

type Step = {
  key: string
  visible: boolean
  stored?: string | null
  card_kind?: string | null
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
  document_presence?: Record<string, boolean>
  ce_code95?: {
    progress?: string | null
    evidence_shape?: string | null
    evidence_variant?: string | null
    upload_codes?: string[]
    asks_file?: boolean
  }
  upload_codes?: string[]
  licence_category_codes?: string[]
  stay_choices?: string[]
  work_choices?: string[]
  legalization?: {
    recommendation: { stay_required: boolean | null; work_required: boolean | null; reason: string }
    selection: {
      stay_required: boolean | null
      work_required: boolean | null
      stay_manual: boolean
      work_manual: boolean
      stay_code: string | null
      stay_exemption: string | null
      work_exemption: string | null
      visa_type: string | null
    }
    resolved: {
      residence: string
      work: string
      missing_residence?: string[]
      missing_work?: string[]
      residence_detail?: string | null
      work_detail?: string | null
    }
    readiness?: { ready: boolean }
    applicable_stay: Array<{
      code: string
      kind: string
      stay_basis: string
      card_kind?: string | null
      documents: string[]
      dependent_documents: string[]
    }>
    applicable_work: Array<{ code: string; kind: string; documents?: string[] }>
    work_exemptions: string[]
    stay_exemptions: string[]
    selected_stay: {
      code: string
      kind: string
      documents: string[]
      dependent_documents: string[]
      evidence?: Array<{ label: string; codes: string[]; metadata?: string[] }>
    } | null
  }
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

export type OperatorFactsSlice = 'rights' | 'documents' | 'extra'

/** Presentation placement. The same operator-facts contract still owns the values. */
export type OperatorFactsRegion = 'person' | 'professional' | 'legalization'

/** Skill answers what the person can do. Record is the physical document. Same contract. */
export type OperatorFactsPresentation = 'skill' | 'record'

export function OperatorFactsForm({
  view,
  countries,
  disabled,
  onPatch,
  slice,
  plain = false,
  region,
  presentation,
}: {
  view: OperatorFactsView
  countries: CountryOption[]
  disabled?: boolean
  onPatch: (patch: Patch) => void
  slice?: OperatorFactsSlice
  plain?: boolean
  region?: OperatorFactsRegion
  presentation?: OperatorFactsPresentation
}) {
  const { t, locale } = useI18n()
  const [skillField, setSkillField] = useState<'categories' | 'adr' | 'code95' | null>(null)
  const [categoryDraft, setCategoryDraft] = useState<string[]>([])
  const [presenceDraft, setPresenceDraft] = useState<string | null>(null)
  const [dateDraft, setDateDraft] = useState('')
  const citizenship = stepOf(view, 'citizenship')
  const stay = stepOf(view, 'stay_basis')
  const work = stepOf(view, 'work')
  const licence = stepOf(view, 'driving_licence')
  const code95 = stepOf(view, 'code95')
  const tacho = stepOf(view, 'tachograph')
  const adr = stepOf(view, 'adr')
  const stayCode = stay?.stored || ''
  const visaOpen = stayCode === 'visa_d' || stayCode === 'visa_c'
  const cardOpen = stayCode === 'karta_pobytu'
  const selectedWork = work?.operator_label && work.operator_label !== 'unknown' ? work.operator_label : 'unknown'
  const procedureOpen = selectedWork === 'work_permit' || selectedWork === 'oswiadczenie'
  const determined = view.citizenship_class === 'pl' || view.citizenship_class === 'eu_eea_ch'
  const licenceCountry = licence?.issuing_country || ''

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
    options: readonly string[],
    onChange: (next: string) => void,
    testId: string,
    group: 'stay_option' | 'work_option',
  ) => (
    <select
      data-testid={testId}
      className="input"
      disabled={disabled}
      value={value || 'unknown'}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="unknown">{unknownLabel}</option>
      {options.map((code) => (
        <option key={code} value={code}>
          {t(`app.candidate_card.operator_facts.${group}.${code}`, { defaultValue: code })}
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
    <DateInput
      value={value}
      disabled={disabled}
      testId={testId}
      onValueChange={(next) => onChange(next || 'unknown')}
    />
  )

  const showRights = !slice || slice === 'rights'
  const showDocuments = !slice || slice === 'documents'
  const showExtra = !slice || slice === 'extra'
  const showCitizenship = region === 'person' || (region == null && showRights)
  const showStay = region === 'legalization' || (region == null && showRights)
  const showWork = region === 'legalization' || (region == null && showRights)
  const showQualifications = region === 'professional' || (region == null && showDocuments)
  const showIdentifiers = region === 'person' || (region == null && showExtra)
  const showAdditional = (region === 'professional' || (region == null && showExtra)) && presentation !== 'skill'
  const shell = plain ? 'space-y-3' : 'scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4'
  const nest = plain ? 'space-y-3' : 'space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3'

  return (
    <div className="space-y-4" data-testid="operator-facts-form">
      {showCitizenship || showStay ? (
      <section className={shell} data-testid="operator-facts-driver">
        {plain ? null : (
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_card.operator_facts.driver_block', {
            defaultValue: 'Dane i uprawnienia kierowcy',
          })}
        </div>
        )}
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {showCitizenship ? field(
            t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Obywatelstwo' }),
            countrySelect(citizenship?.stored, (next) => onPatch({ citizenship: next }), 'operator-facts-citizenship-input'),
            'operator-facts-citizenship',
          ) : null}

          {showStay && stay?.visible ? (
            <div className={nest} data-testid="operator-facts-stay">
              <div className="text-xs font-semibold text-slate-700">
                {t('app.candidate_card.operator_facts.stay_question', {
                  defaultValue: 'Na jakiej podstawie przebywa w Polsce?',
                })}
              </div>
              {choice(stayCode, view.stay_choices ?? [], (next) => onPatch({ stay_basis: next }), 'operator-facts-stay-input', 'stay_option')}
              {visaOpen ? (
                <div data-testid="operator-facts-stay-parameters">
                  {field(
                    t('app.candidate_card.operator_facts.valid_to', { defaultValue: 'Ważna do' }),
                    dateInput(stay?.valid_to, (next) => onPatch({ stay_valid_to: next }), 'operator-facts-stay-valid-to'),
                  )}
                </div>
              ) : null}
              {cardOpen ? (
                <div data-testid="operator-facts-card-parameters">
                  {field(
                    t('app.candidate_card.operator_facts.card_valid_to', { defaultValue: 'Karta ważna do' }),
                    dateInput(stay?.valid_to, (next) => onPatch({ stay_valid_to: next }), 'operator-facts-stay-valid-to'),
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
      ) : null}

      {showWork && (determined || work?.visible) ? (
        <section className={shell} data-testid="operator-facts-work-rights">
          {plain ? null : (
          <div className="text-sm font-semibold text-slate-900">
            {t('app.candidate_card.operator_facts.work_block', { defaultValue: 'Prawo do pracy' })}
          </div>
          )}
          <div className="mt-4 space-y-4">
            {determined ? (
              <p className="text-sm text-slate-800" data-testid="operator-facts-work-determined">
                {t('app.candidate_card.operator_facts.work_not_required', {
                  defaultValue: 'Pobyt i zezwolenie na pracę nie są wymagane.',
                })}
              </p>
            ) : null}
            {work?.visible ? (
              <div className={nest}>
                {field(
                  t('app.candidate_card.operator_facts.work_question', {
                    defaultValue: 'Na jakiej podstawie może pracować?',
                  }),
                  choice(selectedWork, view.work_choices ?? [], (next) => onPatch({ work_label: next }), 'operator-facts-work-input', 'work_option'),
                  'operator-facts-work',
                )}
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
            ) : null}
          </div>
        </section>
      ) : null}

      {showQualifications || showIdentifiers ? (
      <section className={shell} data-testid="operator-facts-qualifications">
        {plain ? null : (
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_card.operator_facts.qualifications', { defaultValue: 'Uprawnienia kierowcy' })}
        </div>
        )}
        {showQualifications && presentation === 'skill' ? (
          <FieldGrid dense testId="operator-facts-skill-rows">
            <InlineFieldRow
              testId="operator-facts-licence-details"
              label={t('app.candidate_card.operator_facts.licence_categories', { defaultValue: 'Categories' })}
              value={(licence?.categories ?? []).join(' · ')}
              editing={skillField === 'categories'}
              canEdit={!disabled}
              contentEditor
              onEdit={() => {
                setCategoryDraft([...(licence?.categories ?? [])])
                setSkillField('categories')
              }}
              onDone={() => {
                onPatch({ licence_categories: categoryDraft.length ? categoryDraft : 'unknown' })
                setSkillField(null)
              }}
              onCancel={() => setSkillField(null)}
            >
              <ChipFieldEditor
                options={(view.licence_category_codes ?? []).map((code) => ({ value: code, label: code }))}
                values={categoryDraft}
                onChange={setCategoryDraft}
                disabled={disabled}
                addLabel={t('common.actions.add')}
                dismissLabel={t('common.actions.dismiss')}
              />
            </InlineFieldRow>
            <InlineFieldRow
              label={t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' })}
              value={factValue(
                adr?.presence,
                t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' }),
                t('app.candidate_card.operator_facts.no', { defaultValue: 'No' }),
              )}
              editing={skillField === 'adr'}
              canEdit={!disabled}
              contentEditor
              onEdit={() => {
                setPresenceDraft(adr?.presence === true ? 'yes' : adr?.presence === false ? 'no' : null)
                setSkillField('adr')
              }}
              onDone={() => {
                onPatch({ adr_presence: presenceDraft === 'yes' ? true : presenceDraft === 'no' ? false : 'unknown' })
                setSkillField(null)
              }}
              onCancel={() => setSkillField(null)}
            >
              <SegmentedControl
                value={presenceDraft}
                options={[
                  { value: 'no', label: t('app.candidate_card.operator_facts.no', { defaultValue: 'No' }) },
                  { value: 'yes', label: t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' }), tone: 'brand' },
                ]}
                disabled={disabled}
                onChange={setPresenceDraft}
              />
            </InlineFieldRow>
            {code95?.visible ? (
              <InlineFieldRow
                testId="operator-facts-code95-skill"
                label={t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' })}
                value={factValue(
                  code95.presence,
                  t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' }),
                  t('app.candidate_card.operator_facts.no', { defaultValue: 'No' }),
                  code95.valid_to,
                  locale,
                )}
                editing={skillField === 'code95'}
                canEdit={!disabled}
                contentEditor
                onEdit={() => {
                  setPresenceDraft(code95.presence === true ? 'yes' : code95.presence === false ? 'no' : null)
                  setDateDraft(code95.valid_to || '')
                  setSkillField('code95')
                }}
                onDone={() => {
                  onPatch({
                    code95_presence: presenceDraft === 'yes' ? true : presenceDraft === 'no' ? false : 'unknown',
                    code95_valid_to: dateDraft || 'unknown',
                  })
                  setSkillField(null)
                }}
                onCancel={() => setSkillField(null)}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SegmentedControl
                    value={presenceDraft}
                    options={[
                      { value: 'no', label: t('app.candidate_card.operator_facts.no', { defaultValue: 'No' }) },
                      { value: 'yes', label: t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' }), tone: 'brand' },
                    ]}
                    disabled={disabled}
                    onChange={setPresenceDraft}
                  />
                  {presenceDraft === 'yes' ? (
                    <DateInput value={dateDraft} disabled={disabled} onValueChange={setDateDraft} />
                  ) : null}
                </div>
              </InlineFieldRow>
            ) : null}
          </FieldGrid>
        ) : null}
        {showQualifications && presentation !== 'skill' ? (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className={nest} data-testid="operator-facts-licence">
            {presentation === 'skill' ? (
              <div className="text-xs font-semibold text-slate-700">
                {t('app.candidate_card.operator_facts.licence_categories', { defaultValue: 'Kategorie' })}
              </div>
            ) : (
              <div className="text-xs font-semibold text-slate-700">
                {t('app.candidate_card.operator_facts.licence_title', { defaultValue: 'Prawo jazdy' })}
              </div>
            )}
            {presentation !== 'skill' ? field(
              t('app.candidate_card.operator_facts.licence_country', { defaultValue: 'Prawo jazdy — kraj wydania' }),
              countrySelect(
                licence?.issuing_country,
                (next) => onPatch({ licence_issuing_country: next }),
                'operator-facts-licence-country',
              ),
            ) : null}
            {(presentation === 'skill' || (presentation !== 'record' && Boolean(licenceCountry))) ? (
              <div data-testid="operator-facts-licence-details">
                {presentation === 'skill' ? null : (
                  <div className="label">
                    {t('app.candidate_card.operator_facts.licence_categories', { defaultValue: 'Kategorie' })}
                  </div>
                )}
                <div className="flex flex-wrap gap-3">
                  {(view.licence_category_codes ?? []).map((code) => {
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
            ) : null}
            {presentation !== 'skill' && licenceCountry ? (
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
            ) : null}
          </div>

          {presentation === 'skill' && code95?.visible ? (
            <div className={nest} data-testid="operator-facts-code95-skill">
              {field(
                t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' }),
                <div className="text-sm text-slate-800">
                  {factValue(
                    code95.presence,
                    t('app.candidate_card.operator_facts.yes', { defaultValue: 'Tak' }),
                    t('app.candidate_card.operator_facts.no', { defaultValue: 'Nie' }),
                    undefined,
                    locale,
                  )}
                </div>,
              )}
            </div>
          ) : null}

          {presentation !== 'skill' && code95?.visible ? (
            <div className={nest} data-testid="operator-facts-code95">
              {field(
                t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' }),
                presenceSelect(code95?.presence, (next) => onPatch({ code95_presence: next }), 'operator-facts-code95-presence'),
              )}
              {code95?.presence === true ? (
                <div className="space-y-4" data-testid="operator-facts-code95-details">
                  {field(
                    t('app.candidate_card.operator_facts.code95_valid_to', { defaultValue: 'Ważny do' }),
                    dateInput(code95?.valid_to, (next) => onPatch({ code95_valid_to: next }), 'operator-facts-code95-valid-to'),
                  )}
                </div>
              ) : null}
            </div>
          ) : null}

          {presentation !== 'skill' ? (
          <div className={nest} data-testid="operator-facts-tachograph">
            {field(
              t('app.candidate_card.operator_facts.tachograph', { defaultValue: 'Karta kierowcy' }),
              presenceSelect(tacho?.presence, (next) => onPatch({ tachograph_presence: next })),
            )}
            {tacho?.presence === true ? (
              <div className="space-y-3">
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
          ) : null}

          {presentation === 'record' && adr?.presence !== true ? null : (
          <div className={nest} data-testid="operator-facts-adr">
            {presentation !== 'record' ? field(
              t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' }),
              presenceSelect(adr?.presence, (next) => onPatch({ adr_presence: next })),
            ) : (
              <div className="text-xs font-semibold text-slate-700">
                {t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' })}
              </div>
            )}
            {presentation !== 'skill' && adr?.presence === true ? (
              <div className="space-y-3">
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
          )}

          {presentation !== 'skill' ? (
          <div className={nest} data-testid="operator-facts-medical">
            {field(
              t('app.candidate_card.operator_facts.medical', { defaultValue: 'Badania lekarskie' }),
              presenceSelect(stepOf(view, 'medical')?.presence, (next) => onPatch({ medical_presence: next })),
            )}
          </div>
          ) : null}
          {presentation !== 'skill' ? (
          <div className={nest} data-testid="operator-facts-psych">
            {field(
              t('app.candidate_card.operator_facts.psych', { defaultValue: 'Testy psychologiczne' }),
              presenceSelect(stepOf(view, 'psych')?.presence, (next) => onPatch({ psych_presence: next })),
            )}
          </div>
          ) : null}
        </div>
        ) : null}
        {showIdentifiers || showAdditional ? (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {showIdentifiers ? (
          <div className={nest} data-testid="operator-facts-pesel">
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
          ) : null}
          {showAdditional ? (
          <div className={nest} data-testid="operator-facts-additional">
            {field(
              t('app.candidate_card.operator_facts.additional', { defaultValue: 'Dodatkowy dokument' }),
              presenceSelect(stepOf(view, 'additional')?.presence, (next) => onPatch({ additional_presence: next })),
            )}
          </div>
          ) : null}
        </div>
        ) : null}
      </section>
      ) : null}
    </div>
  )
}

function countryName(code: string | null | undefined, countries: CountryOption[]): string {
  if (!code || code === 'unknown') return '—'
  const label = countries.find((item) => item.value === code)?.label || code
  const flag = countryFlag(code)
  return flag ? `${flag} ${label}` : label
}

function factValue(
  present: boolean | null | undefined,
  yes: string,
  no: string,
  until?: string | null,
  locale?: string,
): string {
  if (present === false) return no
  if (present !== true) return '—'
  const date = until ? formatDateSafe(until, locale) : ''
  return date && date !== '—' ? `${yes} · ${date}` : yes
}

export function readOperatorFacts(
  view: OperatorFactsView,
  countries: CountryOption[],
  t: (key: string, options?: { defaultValue?: string }) => string,
  locale: string,
) {
  const yes = t('app.candidate_card.operator_facts.yes', { defaultValue: 'Tak' })
  const no = t('app.candidate_card.operator_facts.no', { defaultValue: 'Nie' })
  const licence = stepOf(view, 'driving_licence')
  const code95 = stepOf(view, 'code95')
  const tacho = stepOf(view, 'tachograph')
  const adr = stepOf(view, 'adr')
  const medical = stepOf(view, 'medical')
  const psych = stepOf(view, 'psych')
  const stay = stepOf(view, 'stay_basis')
  const work = stepOf(view, 'work')
  const citizenship = stepOf(view, 'citizenship')
  const pesel = stepOf(view, 'pesel')
  const categories = (licence?.categories ?? []).filter(Boolean)
  const stayCode = stay?.stored && stay.stored !== 'unknown' ? stay.stored : ''
  const stayLabel = stayCode
    ? t(`app.candidate_card.operator_facts.stay_option.${stayCode}`, { defaultValue: stayCode })
    : '—'
  const workCode = work?.operator_label && work.operator_label !== 'unknown' ? work.operator_label : ''
  const workLabel = workCode
    ? t(`app.candidate_card.operator_facts.work_option.${workCode}`, { defaultValue: workCode })
    : '—'
  const rights = [
    {
      label: t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Obywatelstwo' }),
      value: countryName(citizenship?.stored, countries),
    },
    ...(stay?.visible
      ? [
          {
            label: t('app.candidate_card.operator_facts.stay_question', { defaultValue: 'Pobyt' }),
            value: joinParts([
              stayLabel,
              stay?.valid_to ? formatDateSafe(stay.valid_to, locale) : null,
            ]) || '—',
          },
        ]
      : []),
    ...(work?.visible
      ? [
          {
            label: t('app.candidate_card.operator_facts.work_question', { defaultValue: 'Praca' }),
            value: workLabel,
          },
        ]
      : []),
  ]
  const documents = [
    {
      label: t('app.candidate_card.operator_facts.licence_title', { defaultValue: 'Prawo jazdy' }),
      value: categories.length
        ? joinParts([
            categories.join('/'),
            countryName(licence?.issuing_country, countries),
            licence?.valid_to ? formatDateSafe(licence.valid_to, locale) : null,
          ])
        : '—',
    },
    ...(code95?.visible
      ? [
          {
            label: t('app.candidate_card.operator_facts.code95', { defaultValue: 'Code 95' }),
            value: factValue(code95.presence, yes, no, code95.valid_to, locale),
          },
        ]
      : []),
    {
      label: t('app.candidate_card.operator_facts.tachograph', { defaultValue: 'Karta kierowcy' }),
      value: factValue(tacho?.presence, yes, no, tacho?.valid_to, locale),
    },
    {
      label: t('app.candidate_card.operator_facts.adr', { defaultValue: 'ADR' }),
      value: factValue(adr?.presence, yes, no, adr?.valid_to, locale),
    },
    {
      label: t('app.candidate_card.operator_facts.medical', { defaultValue: 'Badania lekarskie' }),
      value: factValue(medical?.presence, yes, no),
    },
    {
      label: t('app.candidate_card.operator_facts.psych', { defaultValue: 'Testy psychologiczne' }),
      value: factValue(psych?.presence, yes, no),
    },
  ]
  const extra = [
    {
      label: t('app.candidate_card.operator_facts.pesel', { defaultValue: 'PESEL' }),
      value: pesel?.presence === true ? pesel.stored || yes : factValue(pesel?.presence, yes, no),
    },
  ]
  const documentsLine = joinParts(
    documents
      .filter((row) => row.value && row.value !== '—')
      .map((row) => `${row.label} ${row.value}`),
  )
  const rightsLine = joinParts(
    rights
      .filter((row) => row.value && row.value !== '—')
      .map((row) => `${row.label} ${row.value}`),
  )
  return { rights, documents, extra, documentsLine, rightsLine, categoryLine: categories.join('/') }
}

export function OperatorFactsWorkspace({
  view,
  countries,
  disabled,
  onPatch,
  requestedSlice,
  editToken = 0,
}: {
  view: OperatorFactsView
  countries: CountryOption[]
  disabled?: boolean
  onPatch: (patch: Patch) => void
  requestedSlice?: OperatorFactsSlice | null
  editToken?: number
}) {
  const { t, locale } = useI18n()
  const [editing, setEditing] = useState<OperatorFactsSlice | null>(null)
  useEffect(() => {
    if (requestedSlice) setEditing(requestedSlice)
  }, [editToken, requestedSlice])
  const read = readOperatorFacts(view, countries, t, locale)
  const block = (slice: OperatorFactsSlice, title: string, rows: Array<{ label: string; value: string }>, defaultOpen: boolean) => (
    <CardAccordion
      title={title}
      summary={joinParts(rows.filter((row) => row.value !== '—').map((row) => `${row.label} ${row.value}`))}
      defaultOpen={defaultOpen}
      editing={editing === slice}
      onEdit={() => setEditing(slice)}
      onDone={() => setEditing(null)}
    >
      {editing === slice ? (
        <OperatorFactsForm
          view={view}
          countries={countries}
          disabled={disabled}
          onPatch={onPatch}
          slice={slice}
          plain
        />
      ) : (
        <ReadFieldRows rows={rows} />
      )}
    </CardAccordion>
  )
  return (
    <div className="space-y-3" data-testid="operator-facts-workspace">
      {block('rights', t('app.candidate_card.ia.sections.rights'), read.rights, true)}
      {block('documents', t('app.candidate_card.ia.sections.documents'), read.documents, true)}
      {block('extra', t('app.candidate_card.ia.sections.extra_facts'), read.extra, false)}
    </div>
  )
}

function LegalizationFactsSheet({
  view,
  contextLabel,
  disabled,
  onPatch,
  stayDocuments,
  workDocuments,
}: {
  view: OperatorFactsView
  contextLabel?: string | null
  onOpenDocuments?: () => void
  disabled?: boolean
  onPatch?: (patch: Patch) => void
  stayDocuments?: ReactNode
  workDocuments?: ReactNode
}) {
  const { t, locale } = useI18n()
  const [openField, setOpenField] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const begin = (key: string, value: string) => {
    setDraft(value)
    setOpenField(key)
  }
  const close = () => setOpenField(null)
  const stay = stepOf(view, 'stay_basis')
  const work = stepOf(view, 'work')
  const determined = view.citizenship_class === 'pl' || view.citizenship_class === 'eu_eea_ch'
  const yes = t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })
  const no = t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })
  const unknownLabel = t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })
  const stayRequired = !(determined || !stay?.visible)
  const workRequired = !(determined || !work?.visible)
  const stayCode = stay?.stored && stay.stored !== 'unknown' ? stay.stored : ''
  const stayLabel = stayCode
    ? t(`app.candidate_card.operator_facts.stay_option.${stayCode}`, { defaultValue: stayCode })
    : ''
  const workCode = work?.operator_label && work.operator_label !== 'unknown' ? work.operator_label : ''
  const workLabel = workCode
    ? t(`app.candidate_card.operator_facts.work_option.${workCode}`, { defaultValue: workCode })
    : ''
  const stayUntil = stay?.valid_to ? formatDateSafe(stay.valid_to, locale) : ''
  const notRequired = t('app.candidate_card.operator_facts.work_not_required', {
    defaultValue: 'Stay and a work permit are not required.',
  })
  const choice = (
    value: string,
    options: readonly string[],
    group: 'stay_option' | 'work_option',
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
      {options.map((code) => (
        <option key={code} value={code}>
          {t(`app.candidate_card.operator_facts.${group}.${code}`, { defaultValue: code })}
        </option>
      ))}
    </select>
  )
  const composeDocuments = stayDocuments !== undefined || workDocuments !== undefined
  const legal = view.legalization
  const basisName = (code: string) => t(`app.candidate_card.ia.legalization.basis.${code}`, {
    defaultValue: t(`app.candidate_card.operator_facts.work_option.${code}`, {
      defaultValue: t(`app.candidate_card.operator_facts.stay_option.${code}`, { defaultValue: code }),
    }),
  })
  const manualNote = t('app.candidate_card.ia.legalization.manual', { defaultValue: 'Set manually' })
  const yesNoValue = (value: boolean | null) => (value === true ? yes : value === false ? no : '')
  const yesNoEditor = () => (
    <SegmentedControl
      value={draft || null}
      options={[
        { value: 'no', label: no },
        { value: 'yes', label: yes, tone: 'brand' },
      ]}
      disabled={disabled || !onPatch}
      onChange={setDraft}
    />
  )
  return (
    <div className={composeDocuments ? 'grid grid-cols-1 gap-3' : 'grid grid-cols-1 gap-3 lg:grid-cols-2'} data-testid="legalization-facts-sheet">
      <WorkspaceSection
        title={t('app.candidate_card.ia.legalization_stay', { defaultValue: 'Stay in the country' })}
        description={stayRequired ? t('app.candidate_card.ia.legalization_stay_hint', { defaultValue: 'Upload only the documents required for this type of stay.' }) : null}
      >
        {composeDocuments ? (
          legal ? (
            <div className="space-y-3">
              <FieldGrid dense>
                <InlineFieldRow
                  label={t('app.candidate_card.ia.legalization_stay_required_question', { defaultValue: 'Is a separate stay basis required?' })}
                  value={yesNoValue(legal.selection.stay_required)}
                  editing={openField === 'stay_required'}
                  canEdit={!disabled && Boolean(onPatch)}
                  contentEditor
                  onEdit={() => begin('stay_required', legal.selection.stay_required === true ? 'yes' : legal.selection.stay_required === false ? 'no' : '')}
                  onDone={() => {
                    if (draft === 'yes' || draft === 'no') onPatch?.({ stay_required: draft === 'yes' })
                    close()
                  }}
                  onCancel={close}
                >
                  {yesNoEditor()}
                </InlineFieldRow>
                {legal.selection.stay_required === true ? (
                  <InlineFieldRow
                    label={t('app.candidate_card.ia.legalization_stay_basis', { defaultValue: 'Stay basis' })}
                    value={legal.selection.stay_code ? basisName(legal.selection.stay_code) : ''}
                    editing={openField === 'stay_basis'}
                    canEdit={!disabled && Boolean(onPatch)}
                    onEdit={() => begin('stay_basis', legal.selection.stay_code || '')}
                    onDone={() => {
                      const item = legal.applicable_stay.find((basis) => basis.code === draft)
                      if (item) {
                        onPatch?.({
                          stay_basis: item.stay_basis,
                          stay_card_kind: item.card_kind || 'unknown',
                          visa_type: item.code === 'visa' ? 'D' : 'unknown',
                        })
                      }
                      close()
                    }}
                    onCancel={close}
                  >
                    <select
                      className="input"
                      data-testid="legalization-stay-basis"
                      disabled={disabled || !onPatch}
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                    >
                      <option value="">{unknownLabel}</option>
                      {legal.applicable_stay.map((item) => (
                        <option key={item.code} value={item.code}>{basisName(item.code)}</option>
                      ))}
                    </select>
                  </InlineFieldRow>
                ) : null}
                {legal.selection.stay_required === false && legal.selection.stay_manual ? (
                  <InlineFieldRow
                    label={t('app.candidate_card.ia.legalization_exemption', { defaultValue: 'Exemption basis' })}
                    value={basisName(legal.selection.stay_exemption || 'other')}
                    editing={openField === 'stay_exemption'}
                    canEdit={!disabled && Boolean(onPatch)}
                    onEdit={() => begin('stay_exemption', legal.selection.stay_exemption || 'other')}
                    onDone={() => {
                      if (draft) onPatch?.({ stay_exemption: draft })
                      close()
                    }}
                    onCancel={close}
                  >
                    <select className="input" disabled={disabled || !onPatch} value={draft} onChange={(event) => setDraft(event.target.value)}>
                      {legal.stay_exemptions.map((code) => (
                        <option key={code} value={code}>{basisName(code)}</option>
                      ))}
                    </select>
                  </InlineFieldRow>
                ) : null}
                {legal.selected_stay?.kind === 'regime' && legal.selected_stay.code === 'visa_free' ? (
                  <InlineFieldRow
                    label={t('app.candidate_card.ia.legalization_valid_to', { defaultValue: 'Valid to' })}
                    value={stayUntil}
                    editing={openField === 'stay_until'}
                    canEdit={!disabled && Boolean(onPatch)}
                    onEdit={() => begin('stay_until', stay?.valid_to || '')}
                    onDone={() => {
                      onPatch?.({ stay_valid_to: draft || 'unknown' })
                      close()
                    }}
                    onCancel={close}
                  >
                    <DateInput value={draft} disabled={disabled} onValueChange={setDraft} />
                  </InlineFieldRow>
                ) : null}
              </FieldGrid>
              {legal.selection.stay_manual ? <p className="text-xs text-slate-500">{manualNote}</p> : null}
              {legal.selection.stay_required === false && !legal.selection.stay_manual ? (
                <p className="text-sm text-slate-800">{basisName(legal.selection.stay_exemption || legal.recommendation.reason)}</p>
              ) : null}
              {legal.selected_stay?.kind === 'regime' && legal.selected_stay.code === 'visa_free' ? (
                <p className="text-sm text-slate-600">
                  {t('app.candidate_card.ia.legalization.visa_free_limit', { defaultValue: 'Short stay follows the 90/180 rule.' })}
                </p>
              ) : null}
              {legal.selected_stay?.kind === 'document' ? stayDocuments : null}
              <LegalizationStatus
                status={legal.resolved.residence}
                missing={legal.resolved.missing_residence}
                detail={legal.resolved.residence_detail}
                hideGap={legal.selected_stay?.kind === 'document'}
              />
            </div>
          ) : (
            stayRequired ? stayDocuments : <p className="text-sm text-slate-800">{stayLabel || notRequired}</p>
          )
        ) : (
          <>
            <InlineFieldRow
              label={t('app.candidate_card.ia.legalization_required', { defaultValue: 'Required' })}
              value={stayRequired ? yes : no}
              editing={false}
              canEdit={false}
              onEdit={() => undefined}
              onDone={() => undefined}
            >
              {null}
            </InlineFieldRow>
            {stayRequired ? (
              <>
                <InlineFieldRow
                  label={t('app.candidate_card.ia.legalization_basis', { defaultValue: 'Basis' })}
                  value={stayLabel}
                  editing={openField === 'stay'}
                  canEdit={!disabled && Boolean(onPatch)}
                  onEdit={() => begin('stay', stayCode)}
                  onDone={() => {
                    onPatch?.({ stay_basis: draft || 'unknown' })
                    close()
                  }}
                  onCancel={close}
                >
                  {choice(draft, view.stay_choices ?? [], 'stay_option', setDraft, 'operator-facts-stay-input')}
                </InlineFieldRow>
                <InlineFieldRow
                  label={t('app.candidate_card.ia.legalization_valid_to', { defaultValue: 'Valid to' })}
                  value={stayUntil}
                  editing={openField === 'stay_until'}
                  canEdit={!disabled && Boolean(onPatch)}
                  onEdit={() => begin('stay_until', stay?.valid_to || '')}
                  onDone={() => {
                    onPatch?.({ stay_valid_to: draft || 'unknown' })
                    close()
                  }}
                  onCancel={close}
                >
                  <DateInput
                    value={draft}
                    disabled={disabled}
                    testId="operator-facts-stay-valid-to"
                    onValueChange={setDraft}
                  />
                </InlineFieldRow>
              </>
            ) : null}
          </>
        )}
      </WorkspaceSection>
      <WorkspaceSection
        title={t('app.candidate_card.ia.legalization_work', { defaultValue: 'Right to work' })}
        description={workRequired
          ? t('app.candidate_card.ia.legalization_work_hint', { defaultValue: 'Documents and procedures that confirm the right to work.' })
          : null}
      >
        {composeDocuments ? (
          legal ? (
            <div className="space-y-3">
              <FieldGrid dense>
                <InlineFieldRow
                  label={t('app.candidate_card.ia.legalization_work_required_question', { defaultValue: 'Is a work permit required?' })}
                  value={yesNoValue(legal.selection.work_required)}
                  editing={openField === 'work_required'}
                  canEdit={!disabled && Boolean(onPatch)}
                  contentEditor
                  onEdit={() => begin('work_required', legal.selection.work_required === true ? 'yes' : legal.selection.work_required === false ? 'no' : '')}
                  onDone={() => {
                    if (draft === 'yes') onPatch?.({ work_required: true, work_label: 'work_permit' })
                    else if (draft === 'no') onPatch?.({ work_required: false, work_exemption: legal.work_exemptions[0] || 'other' })
                    close()
                  }}
                  onCancel={close}
                >
                  {yesNoEditor()}
                </InlineFieldRow>
                {legal.selection.work_required === true ? (
                  <InlineFieldRow
                    label={t('app.candidate_card.ia.legalization_procedure', { defaultValue: 'Procedure' })}
                    value={workCode ? basisName(workCode) : ''}
                    editing={openField === 'work_type'}
                    canEdit={!disabled && Boolean(onPatch)}
                    onEdit={() => begin('work_type', workCode)}
                    onDone={() => {
                      if (draft) onPatch?.({ work_label: draft })
                      close()
                    }}
                    onCancel={close}
                  >
                    <select
                      className="input"
                      data-testid="legalization-work-type"
                      disabled={disabled || !onPatch}
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                    >
                      <option value="">{unknownLabel}</option>
                      {legal.applicable_work.map((item) => (
                        <option key={item.code} value={item.code}>{basisName(item.code)}</option>
                      ))}
                    </select>
                  </InlineFieldRow>
                ) : null}
                {legal.selection.work_required === false && legal.selection.work_manual ? (
                  <InlineFieldRow
                    label={t('app.candidate_card.ia.legalization_exemption', { defaultValue: 'Exemption basis' })}
                    value={basisName(legal.selection.work_exemption || 'other')}
                    editing={openField === 'work_exemption'}
                    canEdit={!disabled && Boolean(onPatch)}
                    onEdit={() => begin('work_exemption', legal.selection.work_exemption || 'other')}
                    onDone={() => {
                      if (draft) {
                        onPatch?.({
                          work_exemption: draft,
                          ...(draft === 'not_required' || draft === 'included_in_stay' ? { work_label: draft } : { work_label: 'not_required' }),
                        })
                      }
                      close()
                    }}
                    onCancel={close}
                  >
                    <select className="input" disabled={disabled || !onPatch} value={draft} onChange={(event) => setDraft(event.target.value)}>
                      {legal.work_exemptions.map((code) => (
                        <option key={code} value={code}>{basisName(code)}</option>
                      ))}
                    </select>
                  </InlineFieldRow>
                ) : null}
              </FieldGrid>
              {legal.selection.work_manual ? <p className="text-xs text-slate-500">{manualNote}</p> : null}
              {legal.selection.work_required === false && !legal.selection.work_manual ? (
                <p className="text-sm text-slate-800">{basisName(legal.selection.work_exemption || legal.recommendation.reason)}</p>
              ) : null}
              {legal.applicable_work.some((item) => item.code === workCode && (item.documents?.length || item.code === 'work_permit' || item.code === 'oswiadczenie')) ? workDocuments : null}
              <LegalizationStatus
                status={legal.resolved.work}
                missing={legal.resolved.missing_work}
                detail={legal.resolved.work_detail}
                hideGap={legal.applicable_work.some((item) => item.code === workCode && (item.documents?.length || item.code === 'work_permit' || item.code === 'oswiadczenie'))}
              />
            </div>
          ) : workRequired ? (
            <div className="space-y-3">
              <InlineFieldRow
                label={t('app.candidate_card.ia.legalization_work_required_question', { defaultValue: 'Is a work permit required?' })}
                value={yesNoValue(workCode === 'work_permit' || workCode === 'oswiadczenie' ? true : workCode === 'not_required' || workCode === 'included_in_stay' ? false : null)}
                editing={openField === 'work_required_fallback'}
                canEdit={!disabled && Boolean(onPatch)}
                contentEditor
                onEdit={() => begin('work_required_fallback', workCode === 'work_permit' || workCode === 'oswiadczenie' ? 'yes' : workCode === 'not_required' || workCode === 'included_in_stay' ? 'no' : '')}
                onDone={() => {
                  if (draft === 'yes') onPatch?.({ work_label: 'work_permit' })
                  else if (draft === 'no') onPatch?.({ work_label: 'not_required' })
                  close()
                }}
                onCancel={close}
              >
                {yesNoEditor()}
              </InlineFieldRow>
              {workCode === 'work_permit' || workCode === 'oswiadczenie' ? workDocuments : (
                <p className="text-sm text-slate-800">{workLabel || notRequired}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-800">{workLabel || notRequired}</p>
          )
        ) : (
          <>
            <InlineFieldRow
              label={t('app.candidate_card.ia.legalization_required', { defaultValue: 'Required' })}
              value={workRequired ? yes : no}
              editing={false}
              canEdit={false}
              onEdit={() => undefined}
              onDone={() => undefined}
            >
              {null}
            </InlineFieldRow>
            {workRequired ? (
              <InlineFieldRow
                label={t('app.candidate_card.ia.legalization_basis', { defaultValue: 'Basis' })}
                value={workLabel}
                editing={openField === 'work'}
                canEdit={!disabled && Boolean(onPatch)}
                onEdit={() => begin('work', workCode)}
                onDone={() => {
                  onPatch?.({ work_label: draft || 'unknown' })
                  close()
                }}
                onCancel={close}
              >
                {choice(draft, view.work_choices ?? [], 'work_option', setDraft, 'operator-facts-work-input')}
              </InlineFieldRow>
            ) : null}
            {contextLabel?.trim() ? (
              <InlineFieldRow
                label={t('app.candidate_card.ia.legalization_employment', { defaultValue: 'Employment' })}
                value={contextLabel.trim()}
                editing={false}
                canEdit={false}
                onEdit={() => undefined}
                onDone={() => undefined}
              >
                {null}
              </InlineFieldRow>
            ) : null}
          </>
        )}
      </WorkspaceSection>
    </div>
  )
}

export function PersonIdentityFacts({
  view,
  countries,
  disabled,
  onPatch,
  flow = false,
}: {
  view: OperatorFactsView
  countries: CountryOption[]
  disabled?: boolean
  onPatch: (patch: Patch) => void
  flow?: boolean
}) {
  const { t } = useI18n()
  const [openField, setOpenField] = useState<'citizenship' | 'pesel' | null>(null)
  const [citizenshipDraft, setCitizenshipDraft] = useState('unknown')
  const [peselPresence, setPeselPresence] = useState<string | null>(null)
  const [peselDraft, setPeselDraft] = useState('')
  const citizenship = stepOf(view, 'citizenship')
  const pesel = stepOf(view, 'pesel')
  const yes = t('app.candidate_card.operator_facts.yes', { defaultValue: 'Yes' })
  const no = t('app.candidate_card.operator_facts.no', { defaultValue: 'No' })
  const unknownLabel = t('app.candidate_card.operator_facts.unknown', { defaultValue: 'Unknown' })
  const countryOptions = [{ value: 'unknown', label: unknownLabel }, ...countries]
  const peselValue = pesel?.presence === true
    ? [yes, pesel.stored].filter((part) => part && part !== 'unknown').join(' · ')
    : pesel?.presence === false
      ? no
      : ''

  return (
    <FieldGrid dense flow={flow} testId="operator-facts-person-rows">
      <InlineFieldRow
        testId="operator-facts-citizenship"
        label={t('app.candidate_card.operator_facts.citizenship', { defaultValue: 'Citizenship' })}
        value={countryName(citizenship?.stored, countries)}
        editing={openField === 'citizenship'}
        canEdit={!disabled}
        onEdit={() => {
          setCitizenshipDraft(citizenship?.stored || 'unknown')
          setOpenField('citizenship')
        }}
        onDone={() => {
          onPatch({ citizenship: citizenshipDraft })
          setOpenField(null)
        }}
        onCancel={() => setOpenField(null)}
      >
        <div data-testid="operator-facts-citizenship-input">
          <SearchableSelect
            options={countryOptions}
            value={citizenshipDraft}
            onChange={setCitizenshipDraft}
            disabled={disabled}
            placeholder={t('app.candidate_card.select.empty')}
            searchPlaceholder={t('app.candidate_card.select.search')}
            noResultsLabel={t('app.candidate_card.select.no_results')}
          />
        </div>
      </InlineFieldRow>
      <InlineFieldRow
        label={t('app.candidate_card.operator_facts.pesel', { defaultValue: 'PESEL' })}
        value={peselValue === '—' ? '' : peselValue}
        editing={openField === 'pesel'}
        canEdit={!disabled}
        contentEditor
        onEdit={() => {
          setPeselPresence(pesel?.presence === true ? 'yes' : pesel?.presence === false ? 'no' : null)
          setPeselDraft(pesel?.stored && pesel.stored !== 'unknown' ? pesel.stored : '')
          setOpenField('pesel')
        }}
        onDone={() => {
          onPatch({
            pesel_presence: peselPresence === 'yes' ? true : peselPresence === 'no' ? false : 'unknown',
            ...(peselPresence === 'yes' ? { pesel: peselDraft || 'unknown' } : {}),
          })
          setOpenField(null)
        }}
        onCancel={() => setOpenField(null)}
      >
        <div className="flex flex-wrap items-center gap-2" data-testid="operator-facts-pesel">
          <SegmentedControl
            value={peselPresence}
            options={[
              { value: 'no', label: no },
              { value: 'yes', label: yes, tone: 'brand' },
            ]}
            disabled={disabled}
            onChange={setPeselPresence}
          />
          {peselPresence === 'yes' ? (
            <input
              className="input w-40"
              aria-label={t('app.candidate_card.operator_facts.pesel_number', { defaultValue: 'PESEL number' })}
              disabled={disabled}
              value={peselDraft}
              onChange={(event) => setPeselDraft(event.target.value)}
            />
          ) : null}
        </div>
      </InlineFieldRow>
    </FieldGrid>
  )
}

export default function OperatorFactsSurface({
  candidateId,
  countries,
  onSaved,
  onLoaded,
  requestedSlice,
  editToken = 0,
  region,
  presentation,
  contextLabel,
  onOpenDocuments,
  flow = false,
  stayDocuments,
  workDocuments,
}: {
  candidateId: string
  countries: CountryOption[]
  onSaved?: (view: OperatorFactsView) => void
  onLoaded?: (view: OperatorFactsView) => void
  requestedSlice?: OperatorFactsSlice | null
  editToken?: number
  region?: OperatorFactsRegion
  presentation?: OperatorFactsPresentation
  contextLabel?: string | null
  onOpenDocuments?: () => void
  flow?: boolean
  stayDocuments?: ReactNode
  workDocuments?: ReactNode
}) {
  const { t } = useI18n()
  const [view, setView] = useState<OperatorFactsView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const onLoadedRef = useRef(onLoaded)
  onLoadedRef.current = onLoaded

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
        if (!cancelled) {
          setView(response.data)
          onLoadedRef.current?.(response.data)
        }
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
        onLoadedRef.current?.(response.data)
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
    <div className={flow && region === 'person' ? 'contents' : 'space-y-3'} data-testid="operator-facts-surface">
      {error ? <p className="text-xs text-slate-700">{error}</p> : null}
      {view && region === 'legalization' ? (
        <LegalizationFactsSheet
          view={view}
          contextLabel={contextLabel}
          disabled={busy}
          onPatch={(patch) => void onPatch(patch)}
          stayDocuments={stayDocuments}
          workDocuments={workDocuments}
        />
      ) : null}
      {view && region === 'person' ? (
        <PersonIdentityFacts
          view={view}
          countries={countries}
          disabled={busy}
          onPatch={(patch) => void onPatch(patch)}
          flow={flow}
        />
      ) : null}
      {view && region && region !== 'person' && region !== 'legalization' ? (
        <OperatorFactsForm
          view={view}
          countries={countries}
          disabled={busy}
          onPatch={(patch) => void onPatch(patch)}
          region={region}
          presentation={presentation}
          plain
        />
      ) : null}
      {view && !region ? (
        <OperatorFactsWorkspace
          view={view}
          countries={countries}
          disabled={busy}
          onPatch={(patch) => void onPatch(patch)}
          requestedSlice={requestedSlice}
          editToken={editToken}
        />
      ) : null}
    </div>
  )
}
