import clsx from 'clsx'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import { useI18n, type TranslateFn } from '../../i18n'
import DateInput from '../../components/controls/DateInput'
import { FieldGrid } from '../../components/ui/FieldGrid'
import { InlineFieldRow } from '../../components/ui/InlineFieldRow'
import { Chip } from '../../components/ui/Chip'
import { CardAccordion } from '../../components/candidate/card/CandidateCardChrome'
import {
  presentCompensation,
  presentCountry,
  presentJobCount,
  presentMonthSpan,
  presentProfessionalCode,
} from '../professional-profile/presentation'
import {
  durationLines,
  durationReading,
  durationText,
  employmentPeriodError,
  professionalSummary,
  splitConstraints,
  trailerLines,
  type DurationLine,
  type ProfessionalProfileProjection,
  type ProfileCopy,
} from './professionalProfileView'

export function useProfileCopy(): ProfileCopy {
  const { t } = useI18n()
  return {
    history: (years) => t('app.candidate_card.ia.profile_history', { defaultValue: '{years} лет по истории', values: { years } }),
    declared: (years) => t('app.candidate_card.ia.profile_declared', { defaultValue: 'заявлено {years}', values: { years } }),
    both: (calculated, declared) => t('app.candidate_card.ia.profile_both', {
      defaultValue: '{calculated} лет по истории / заявлено {declared}',
      values: { calculated, declared },
    }),
    presence: t('app.candidate_card.ia.profile_presence_short', { defaultValue: 'есть опыт' }),
    insufficient: t('app.candidate_card.ia.profile_insufficient', { defaultValue: 'недостаточно истории' }),
    periodError: t('app.candidate_card.ia.profile_check_history', { defaultValue: 'проверьте историю' }),
    rowPeriodError: t('app.candidate_card.ia.profile_row_period_error', { defaultValue: 'Ошибка периода работы' }),
    hasExperience: t('app.candidate_card.ia.profile_has_experience', { defaultValue: 'есть опыт' }),
    unmapped: (code) => t('app.candidate_card.ia.profile_unmapped', { defaultValue: '{code} · не сопоставлено', values: { code } }),
    openEnded: t('app.candidate_card.ia.profile_open_ended', { defaultValue: 'по настоящее время' }),
    noEmployment: t('app.candidate_card.ia.profile_no_employment', { defaultValue: 'Нет истории работы' }),
    noPreferences: t('app.candidate_card.ia.profile_no_preferences', { defaultValue: 'Нет предпочтений' }),
    availableFrom: (date) => date,
    present: t('app.candidate_card.profile_projection.present', { defaultValue: 'есть' }),
    absent: t('app.candidate_card.profile_projection.absent', { defaultValue: 'нет' }),
    unknown: t('app.candidate_card.profile_projection.unknown', { defaultValue: 'нет данных' }),
    expired: t('app.candidate_card.profile_projection.expired', { defaultValue: 'Истекло' }),
    scheduled: t('app.candidate_card.profile_projection.scheduled', { defaultValue: 'ещё не действует' }),
    validityUnknown: t('app.candidate_card.profile_projection.validity_unknown', { defaultValue: 'срок не определён' }),
  }
}

export function useProfessionalProfile(candidateId: string | null | undefined, revision: number) {
  const [profile, setProfile] = useState<ProfessionalProfileProjection | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    if (!candidateId) {
      setProfile(null)
      return
    }
    let cancelled = false
    setError(false)
    void api.get<ProfessionalProfileProjection>(`/candidates/${candidateId}/professional-profile`)
      .then((response) => {
        if (!cancelled) setProfile(response.data)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => {
      cancelled = true
    }
  }, [candidateId, revision])
  return { profile, error }
}

function readOnlyRow(label: string, value: string, testId?: string, muted = false) {
  return (
    <InlineFieldRow
      key={testId || `${label}:${value}`}
      label={label}
      value={value}
      editing={false}
      canEdit={false}
      onEdit={() => undefined}
      onDone={() => undefined}
      testId={testId}
      muted={muted}
    >
      {null}
    </InlineFieldRow>
  )
}

function presenceText(value: boolean | null, copy: ProfileCopy): string | null {
  if (value === true) return copy.present
  if (value === false) return copy.absent
  return null
}

function durationLabel(line: DurationLine, locale: string, t: TranslateFn): string {
  if (line.id === 'total') return t('app.candidate_card.ia.profile_total', { defaultValue: 'Общий опыт' })
  if (line.id === 'non_eu_declared') return t('app.candidate_card.ia.profile_non_eu', { defaultValue: 'Заявлено вне ЕС' })
  return presentProfessionalCode(
    line.id.startsWith('movement:') ? 'movement_pattern' : line.id.startsWith('crew:') ? 'crew_mode' : 'operation_scope',
    line.label,
    locale,
  ) || line.label
}

function metricText(
  aggregate: ProfessionalProfileProjection['experience']['aggregates']['ce'],
  declared: string | null,
  copy: ProfileCopy,
  locale: string,
): string | null {
  const reading = durationReading(aggregate, declared)
  const text = durationText(reading, copy, locale)
  if (reading.kind === 'hidden' || !text) return null
  return text
}

function buildTenureRows(
  profile: ProfessionalProfileProjection,
  lines: DurationLine[],
  copy: ProfileCopy,
  locale: string,
  t: TranslateFn,
): Array<{ id: string; label: string; text: string }> {
  const rows: Array<{ id: string; label: string; text: string }> = []
  const total = lines.find((line) => line.id === 'total')
  if (total) rows.push({ id: 'total', label: durationLabel(total, locale, t), text: total.text })
  const ce = metricText(profile.experience.aggregates.ce, profile.experience.declared.ce.years, copy, locale)
  if (ce) rows.push({ id: 'ce', label: 'CE', text: ce })
  const internationalLabel = presentProfessionalCode('operation_scope', 'international', locale) || 'International'
  const international = metricText(profile.experience.aggregates.international, null, copy, locale)
  if (international) rows.push({ id: 'international', label: internationalLabel, text: international })
  else if (profile.experience.declared.intake?.international === true) {
    rows.push({ id: 'international', label: internationalLabel, text: copy.presence })
  }
  const euLabel = presentProfessionalCode('work_area_region', 'eu', locale) || 'EU'
  const eu = metricText(profile.experience.aggregates.eu, null, copy, locale)
  if (eu) rows.push({ id: 'eu', label: euLabel, text: eu })
  for (const line of lines) {
    if (line.id === 'total') continue
    rows.push({ id: line.id, label: durationLabel(line, locale, t), text: line.text })
  }
  return rows
}

function qualificationDetail(
  presence: boolean | null,
  validTo: string | null,
  country: string | null,
  copy: ProfileCopy,
): string | null {
  const state = presenceText(presence, copy)
  if (!state) return null
  const extra = [country, validTo].filter(Boolean)
  if (presence === true && !extra.length) return null
  return [state, ...extra].join(' · ')
}

export function CandidateProfessionalProfile({
  profile,
  qualificationEditor,
  employmentEditor,
  candidateId,
  canEditAvailability = false,
  onAvailabilitySaved,
}: {
  profile: ProfessionalProfileProjection | null
  qualificationEditor?: ReactNode
  employmentEditor?: ReactNode
  candidateId?: string | null
  canEditAvailability?: boolean
  onAvailabilitySaved?: () => void
}) {
  const { t, locale } = useI18n()
  const copy = useProfileCopy()
  const summary = profile ? professionalSummary(profile, copy, locale) : []
  const lines = profile ? durationLines(profile, copy, locale) : []
  const [historyEditing, setHistoryEditing] = useState(false)
  const [availabilityEditing, setAvailabilityEditing] = useState(false)
  const [availableFrom, setAvailableFrom] = useState('')
  const availableFromRef = useRef('')
  const [availabilityError, setAvailabilityError] = useState(false)
  const storedAvailableFrom = profile?.preferences_and_availability.availability.available_from ?? ''
  const rememberAvailableFrom = (iso: string) => {
    availableFromRef.current = iso
    setAvailableFrom(iso)
  }
  useEffect(() => {
    rememberAvailableFrom(storedAvailableFrom)
    setAvailabilityEditing(false)
    setAvailabilityError(false)
  }, [storedAvailableFrom])
  const trailers = profile ? trailerLines(profile, copy, locale) : []
  const areas = profile?.experience.geography.work_areas ?? []
  const covers = (label: string | null) => Boolean(
    label && summary.some((part) => part === label || part.startsWith(`${label} `) || part.startsWith(`${label} ·`)),
  )
  const internationalLabel = presentProfessionalCode('operation_scope', 'international', locale)
  const euLabel = presentProfessionalCode('work_area_region', 'eu', locale)
  const visibleAreas = areas.filter((area) => !(area.kind === 'region' && area.code === 'eu' && covers(euLabel)))
  const measured = new Set(lines.map((line) => line.id))
  const character = profile ? [
    ...profile.experience.work_character.operation_scopes.map((item) => ({ ...item, vocabulary: 'operation_scope' })),
    ...profile.experience.work_character.movement_patterns.map((item) => ({ ...item, vocabulary: 'movement_pattern' })),
    ...profile.experience.work_character.crew_modes.map((item) => ({ ...item, vocabulary: 'crew_mode' })),
  ].filter((item) => {
    if (item.code === 'international' && covers(internationalLabel)) return false
    if (item.vocabulary === 'movement_pattern' && measured.has(`movement:${item.code}`)) return false
    if (item.vocabulary === 'crew_mode' && measured.has(`crew:${item.code}`)) return false
    return true
  }) : []
  const constraints = profile ? splitConstraints(profile) : { current: [], history: [] }
  const preferences = profile?.preferences_and_availability
  const preferencesEmpty = Boolean(
    preferences && !preferences.choices.length && !preferences.compensation && !preferences.availability.available_from,
  )
  const orderedLines = [...lines].sort((left, right) => {
    if (left.id === 'total') return -1
    if (right.id === 'total') return 1
    const weight = { history: 0, both: 0, declared: 1, presence: 2, insufficient: 3, period_error: 3, hidden: 9 }
    return weight[left.kind] - weight[right.kind]
  })
  const tenureRows = profile ? buildTenureRows(profile, orderedLines, copy, locale, t) : []
  const showCharacter = character.length > 0 || trailers.length > 0 || visibleAreas.length > 0
  const jobCount = profile?.experience.employments.length
    ? presentJobCount(profile.experience.employments.length, locale)
    : null
  const licence = profile?.capabilities.licence.categories.join(' · ') ?? ''
  const unmappedLicence = profile?.capabilities.licence.raw_unmapped ?? []
  const capabilityRows = profile ? [
    licence ? readOnlyRow(t('app.candidate_card.profile_projection.licence', { defaultValue: 'Категории прав' }), licence, 'profile-licence') : null,
    ...unmappedLicence.map((code) => readOnlyRow(
      t('app.candidate_card.profile_projection.licence', { defaultValue: 'Категории прав' }),
      copy.unmapped(code),
      `profile-licence-${code}`,
    )),
    qualificationDetail(profile.capabilities.code95.presence, profile.capabilities.code95.valid_to, null, copy)
      ? readOnlyRow('Code 95', qualificationDetail(profile.capabilities.code95.presence, profile.capabilities.code95.valid_to, null, copy) || '', 'profile-code95')
      : null,
    qualificationDetail(profile.capabilities.tachograph.presence, profile.capabilities.tachograph.valid_to, profile.capabilities.tachograph.issuing_country, copy)
      ? readOnlyRow(t('app.candidate_card.profile_projection.tachograph', { defaultValue: 'Тахограф' }), qualificationDetail(profile.capabilities.tachograph.presence, profile.capabilities.tachograph.valid_to, profile.capabilities.tachograph.issuing_country, copy) || '', 'profile-tachograph')
      : null,
    qualificationDetail(profile.capabilities.adr.presence, profile.capabilities.adr.valid_to, profile.capabilities.adr.issuing_country, copy)
      ? readOnlyRow('ADR', qualificationDetail(profile.capabilities.adr.presence, profile.capabilities.adr.valid_to, profile.capabilities.adr.issuing_country, copy) || '', 'profile-adr')
      : null,
  ].filter(Boolean) : []

  const saveAvailability = async () => {
    if (!candidateId) return
    setAvailabilityError(false)
    try {
      await api.patch(`/candidates/${candidateId}/professional-profile/availability`, {
        available_from: availableFromRef.current || null,
      })
      setAvailabilityEditing(false)
      onAvailabilitySaved?.()
    } catch {
      setAvailabilityError(true)
    }
  }

  return (
    <div className="space-y-3" data-testid="candidate-professional-profile">
      {summary.length ? (
        <div className="flex flex-wrap gap-1.5" data-testid="professional-summary">
          {summary.map((part) => (
            <Chip key={part} behavior="static" label={part} />
          ))}
        </div>
      ) : null}
      {profile && (capabilityRows.length || qualificationEditor) ? (
      <CardAccordion
        title={t('app.candidate_card.ia.sections.qualification', { defaultValue: 'Qualification' })}
        description={capabilityRows.length ? t('app.candidate_card.ia.qualification_hint', { defaultValue: 'Categories and professional qualifications' }) : null}
        defaultOpen={capabilityRows.length > 0}
      >
        {capabilityRows.length ? <FieldGrid dense>{capabilityRows}</FieldGrid> : null}
        {qualificationEditor}
      </CardAccordion>
      ) : null}
      {profile ? (
      <CardAccordion
        title={t('app.candidate_card.sections.experience.title')}
        description={t('app.candidate_card.ia.driving_experience_hint', { defaultValue: 'Total experience, work pattern and crew' })}
        defaultOpen
        editing={historyEditing}
        onEdit={profile.experience.employments.length || employmentEditor ? () => setHistoryEditing(true) : undefined}
        onDone={() => setHistoryEditing(false)}
        summary={profile.experience.employments.length
          ? presentJobCount(profile.experience.employments.length, locale)
          : null}
      >
        <div className="space-y-4">
        {tenureRows.length ? (
          <div className="space-y-2" data-testid="profile-tenure">
            <div className="text-sm font-medium text-slate-900">
              {t('app.candidate_card.ia.profile_calculated_tenure', { defaultValue: 'Рассчитанный стаж' })}
            </div>
            <FieldGrid dense>
              {tenureRows.map((line) => readOnlyRow(line.label, line.text, `profile-duration-${line.id}`))}
            </FieldGrid>
          </div>
        ) : null}
        {showCharacter ? (
          <div className={clsx('space-y-3', tenureRows.length ? 'border-t border-slate-200 pt-4' : undefined)} data-testid="profile-experience-character">
            <div className="text-sm font-medium text-slate-900">
              {t('app.candidate_card.ia.profile_experience_character', { defaultValue: 'Характер опыта' })}
            </div>
            {character.length ? (
              <div className="flex flex-wrap gap-1.5">
                {character.map((item) => {
                  const label = item.resolution === 'unmapped'
                    ? copy.unmapped(item.code)
                    : presentProfessionalCode(item.vocabulary, item.code, locale) || copy.unmapped(item.code)
                  return (
                    <span key={`${item.vocabulary}-${item.code}`} data-testid={`profile-character-${item.code}`}>
                      <Chip behavior="static" label={label} />
                    </span>
                  )
                })}
              </div>
            ) : null}
            {trailers.length ? (
              <div className="space-y-2">
                <div className="text-xs font-medium text-slate-500">
                  {t('app.candidate_card.profile_projection.practical', { defaultValue: 'Практический опыт' })}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {trailers.map((item) => (
                    <span key={item.code} data-testid={`profile-trailer-${item.code}`}>
                      <Chip behavior="static" label={item.text} />
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            {visibleAreas.length ? (
              <div className="space-y-2">
                <div className="text-xs font-medium text-slate-500">
                  {t('app.candidate_card.profile_projection.geography', { defaultValue: 'География' })}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {visibleAreas.map((area) => {
                    const label = area.resolution === 'unmapped'
                      ? copy.unmapped(area.code)
                      : area.kind === 'country'
                        ? presentCountry(area.code, locale)
                        : presentProfessionalCode('work_area_region', area.code, locale) || copy.unmapped(area.code)
                    return (
                      <span key={`${area.kind}-${area.code}`} data-testid={`profile-area-${area.kind}-${area.code}`}>
                        <Chip behavior="static" label={label} />
                      </span>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
        <div className={clsx('space-y-3', tenureRows.length || showCharacter ? 'border-t border-slate-200 pt-4' : undefined)}>
          <div className="flex items-baseline justify-between gap-3">
            <div className="text-sm font-medium text-slate-900">
              {t('app.candidate_card.ia.sections.recent_work', { defaultValue: 'История работы' })}
            </div>
            {jobCount ? <div className="text-xs text-slate-500">{jobCount}</div> : null}
          </div>
        {historyEditing ? employmentEditor : profile.experience.employments.length ? (
          <div className="space-y-3">
            {profile.experience.employments.map((job) => {
              const broken = employmentPeriodError(job.start_date, job.end_date)
              const period = broken ? null : presentMonthSpan(job.start_date, job.end_date, copy.openEnded)
              const place = job.country ? presentCountry(job.country, locale) : null
              const chips = [
                ...job.driving_categories,
                ...job.operation_scopes.map((code) => presentProfessionalCode('operation_scope', code, locale) || copy.unmapped(code)),
                ...job.movement_patterns.map((code) => presentProfessionalCode('movement_pattern', code, locale) || copy.unmapped(code)),
                ...job.crew_modes.map((code) => presentProfessionalCode('crew_mode', code, locale) || copy.unmapped(code)),
                ...job.work_areas.map((area) => {
                  const known = areas.find((item) => item.kind === area.kind && item.code === area.code)
                  if (known?.resolution === 'unmapped') return copy.unmapped(area.code)
                  if (area.kind === 'country') return presentCountry(area.code, locale)
                  return presentProfessionalCode('work_area_region', area.code, locale) || copy.unmapped(area.code)
                }),
                ...job.trailer_types.map((code) => {
                  const known = trailers.find((item) => item.code === code)
                  return known?.unmapped === false ? known.text.replace(` · ${copy.hasExperience}`, '') : copy.unmapped(code)
                }),
              ]
              return (
                <div key={job.id} data-testid={`profile-employment-${job.id}`} className="space-y-1">
                  <div className="text-sm font-medium text-slate-900">
                    {[job.employer_name || job.id, job.position].filter(Boolean).join(' · ')}
                  </div>
                  {broken ? (
                    <div className="text-sm text-rose-700">{copy.rowPeriodError}</div>
                  ) : (
                    <div className="text-sm text-slate-600">{[period, place].filter(Boolean).join(' · ')}</div>
                  )}
                  {chips.length ? (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {chips.map((label, index) => (
                        <Chip key={`${label}-${index}`} behavior="static" label={label} />
                      ))}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-500" data-testid="profile-no-employment">{copy.noEmployment}</p>
        )}
        </div>
        </div>
      </CardAccordion>
      ) : employmentEditor}
      {profile ? <CardAccordion
        title={t('app.candidate_card.profile_projection.preferences', { defaultValue: 'Предпочтения и доступность' })}
        description={t('app.candidate_card.profile_projection.available_from_hint', { defaultValue: 'Готовность выйти на работу' })}
        summary={preferences?.availability.available_from || (preferencesEmpty ? copy.noPreferences : null)}
        defaultOpen={!preferencesEmpty}
      >
        <FieldGrid dense>
          <InlineFieldRow
            label={t('app.candidate_card.profile_projection.available_from', { defaultValue: 'Готов выйти' })}
            value={preferences?.availability.available_from || ''}
            editing={availabilityEditing}
            canEdit={Boolean(candidateId && canEditAvailability)}
            onEdit={() => {
              rememberAvailableFrom(storedAvailableFrom)
              setAvailabilityError(false)
              setAvailabilityEditing(true)
            }}
            onDone={() => { void saveAvailability() }}
            onCancel={() => {
              rememberAvailableFrom(storedAvailableFrom)
              setAvailabilityError(false)
              setAvailabilityEditing(false)
            }}
            testId="profile-available-from"
            muted={!preferences?.availability.available_from}
          >
            <div className="space-y-1" data-testid="profile-available-from-editor">
              <DateInput value={availableFrom} onValueChange={rememberAvailableFrom} testId="profile-available-from-input" />
              {availabilityError ? (
                <p className="text-sm text-rose-700">{t('common.errors.save_failed', { defaultValue: 'Не удалось сохранить' })}</p>
              ) : null}
            </div>
          </InlineFieldRow>
          {preferences?.choices.map((choice) => readOnlyRow(
            t('app.candidate_card.profile_projection.preference', { defaultValue: 'Предпочтение' }),
            [
              presentProfessionalCode('work_system', choice.code, locale) || presentProfessionalCode(choice.subject, choice.code, locale) || copy.unmapped(choice.code),
            ].join(''),
            `profile-preference-${choice.id}`,
          ))}
          {preferences?.compensation ? readOnlyRow(
            t('app.candidate_card.profile_projection.compensation', { defaultValue: 'Ожидаемая оплата' }),
            presentCompensation(
              preferences.compensation.amount,
              preferences.compensation.currency,
              preferences.compensation.period,
              locale,
            ),
            'profile-compensation',
          ) : null}
        </FieldGrid>
      </CardAccordion> : null}
      {constraints.current.length ? (
        <CardAccordion
          title={t('app.candidate_card.profile_projection.constraints', { defaultValue: 'Ограничения' })}
          defaultOpen
        >
          <FieldGrid dense>
            {constraints.current.map((row) => readOnlyRow(
              t('app.candidate_card.profile_projection.constraint', { defaultValue: 'Ограничение' }),
              [row.subject, row.code, row.effect, row.valid_to].filter(Boolean).join(' · '),
              `profile-constraint-${row.id}`,
            ))}
          </FieldGrid>
        </CardAccordion>
      ) : null}
      {constraints.history.length ? (
        <CardAccordion
          title={`${t('app.candidate_card.profile_projection.constraint_history', { defaultValue: 'История ограничений' })} (${constraints.history.length})`}
          defaultOpen={false}
        >
          <FieldGrid dense>
            {constraints.history.map((row) => readOnlyRow(
              t('app.candidate_card.profile_projection.constraint_history', { defaultValue: 'История ограничений' }),
              `${[row.subject, row.code, row.effect].join(' · ')} · ${
                row.activity === 'expired' ? copy.expired : row.activity === 'scheduled' ? copy.scheduled : copy.validityUnknown
              }${row.valid_to ? ` · ${row.valid_to}` : ''}`,
              `profile-constraint-history-${row.id}`,
              true,
            ))}
          </FieldGrid>
        </CardAccordion>
      ) : null}
    </div>
  )
}
