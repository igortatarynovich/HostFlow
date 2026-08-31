import { useEffect, useMemo, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { IconGripVertical, IconDots } from '@tabler/icons-react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { CustomFieldDefinition } from '../../api/custom_fields'
import { listCustomFieldDefinitions } from '../../api/custom_fields'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import type { EntityPassport } from '../../platform/entity-model'
import { getFieldConfigs, getFieldLabel, isFieldVisible } from '../../utils/profileUtils'
import { getLanguageDisplayName, getRegionDisplayName } from '../../utils/catalogLocale'
import { formatDateSafe } from './candidateUtils'
import type { AugmentedCandidate } from './types'
import { useI18n } from '../../i18n'

type ReadOnlyFieldProps = {
  label: string
  value?: ReactNode
  fullWidth?: boolean
}

function ReadOnlyField({ label, value, fullWidth }: ReadOnlyFieldProps) {
  if (value == null || value === '') return null
  return (
    <div className={clsx('space-y-1', fullWidth && 'md:col-span-2')}>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="text-sm font-medium text-slate-900">{value}</dd>
    </div>
  )
}

function MockupWorkspaceSection({
  index,
  title,
  subtitle,
  defaultOpen = true,
  children,
}: {
  index: number
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-slate-50/80"
      >
        <IconGripVertical size={16} className="mt-0.5 shrink-0 text-slate-300" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-900">
            {index}. {title}
          </p>
          {subtitle ? <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        <span className="shrink-0 text-xs font-medium text-slate-400">{open ? '−' : '+'}</span>
        <IconDots size={16} className="mt-0.5 shrink-0 text-slate-300" aria-hidden />
      </button>
      {open ? (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3">
          <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</dl>
        </div>
      ) : null}
    </section>
  )
}

function formatBool(value: boolean | null | undefined, yes: string, no: string): string | undefined {
  if (value == null) return undefined
  return value ? yes : no
}

function formatCustomFieldValue(
  definition: CustomFieldDefinition,
  raw: unknown,
  locale: string,
  yes: string,
  no: string,
): ReactNode {
  if (raw == null || raw === '') return '—'
  switch (definition.field_type) {
    case 'CHECKBOX':
      return formatBool(Boolean(raw), yes, no)
    case 'MULTISELECT':
      return Array.isArray(raw) && raw.length ? raw.join(', ') : '—'
    case 'DATE':
      return formatDateSafe(String(raw), locale)
    default:
      return String(raw)
  }
}

function CandidateCustomFieldsReadOnlyBlock({
  candidate,
  candidateProfile,
  effectiveLayout,
  locale,
}: {
  candidate: AugmentedCandidate
  candidateProfile: CandidateProfile | null
  effectiveLayout?: EffectiveCardLayout | null
  locale: string
}) {
  const { t } = useI18n()
  const extra = candidate.__extra as Record<string, unknown>
  const rawExtra = (candidate as { extra?: Record<string, unknown> }).extra ?? {}

  const profileCustomFields = useMemo(() => {
    if (!candidateProfile) return []
    return getFieldConfigs(candidateProfile).filter(
      (c) => c.field_key.startsWith('custom_') && c.custom_field_id,
    )
  }, [candidateProfile])

  const [definitions, setDefinitions] = useState<CustomFieldDefinition[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (profileCustomFields.length === 0) {
      setDefinitions([])
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)

    void listCustomFieldDefinitions({ scope: 'CANDIDATE', is_active: true })
      .then((all) => {
        if (cancelled) return
        const ids = new Set(profileCustomFields.map((f) => f.custom_field_id).filter(Boolean))
        setDefinitions(all.filter((def) => ids.has(def.id)))
      })
      .catch(() => {
        if (!cancelled) setDefinitions([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [profileCustomFields])

  const visibleFields = profileCustomFields.filter((fieldConfig) =>
    isFieldVisible(candidateProfile, fieldConfig.field_key, effectiveLayout),
  )

  if (!candidateProfile || visibleFields.length === 0) return null

  const definitionMap = new Map<string, CustomFieldDefinition>()
  visibleFields.forEach((fieldConfig) => {
    if (!fieldConfig.custom_field_id) return
    const def = definitions.find((d) => d.id === fieldConfig.custom_field_id)
    if (def) definitionMap.set(fieldConfig.field_key, def)
  })

  return (
    <MockupWorkspaceSection
      index={3}
      title={t('app.candidates.workspace.custom_fields')}
      subtitle={t('app.candidates.workspace.custom_fields_hint')}
      defaultOpen
    >
      {loading ? (
        <div className="md:col-span-2 text-sm text-slate-500">{t('common.loading')}</div>
      ) : (
        visibleFields.map((fieldConfig) => {
          const definition = definitionMap.get(fieldConfig.field_key)
          if (!definition) return null
          const label = getFieldLabel(candidateProfile, fieldConfig.field_key, definition.label, effectiveLayout)
          const value =
            (rawExtra as Record<string, unknown>)[fieldConfig.field_key] ??
            extra[fieldConfig.field_key]
          return (
            <ReadOnlyField
              key={fieldConfig.field_key}
              label={label}
              value={formatCustomFieldValue(definition, value, locale, t('common.yes'), t('common.no'))}
            />
          )
        })
      )}
    </MockupWorkspaceSection>
  )
}

export type CandidateOverviewContentProps = {
  passport: EntityPassport
  candidate: AugmentedCandidate
  locale: string
  candidateProfile: CandidateProfile | null
  effectiveLayout?: EffectiveCardLayout | null
}

export function CandidateOverviewContent({
  passport,
  candidate,
  locale,
  candidateProfile,
  effectiveLayout,
}: CandidateOverviewContentProps) {
  const { t } = useI18n()
  const extra = candidate.__extra
  const rawExtra = (candidate as { extra?: Record<string, unknown> }).extra ?? {}
  const birthDate = (rawExtra.birth_date as string | undefined) ?? undefined
  const languages = candidate.languages?.length
    ? candidate.languages.map((code) => getLanguageDisplayName(code, locale)).join(', ')
    : undefined
  const citizenship =
    passport.sections.contacts.citizenship ??
    (extra.citizenship ? getRegionDisplayName(String(extra.citizenship), locale) : undefined)
  const experienceYears =
    (rawExtra.experience_years as number | undefined) ??
    (rawExtra.experience_ce_total as number | undefined) ??
    undefined
  const licenseCategories = Array.isArray(rawExtra.license_categories)
    ? (rawExtra.license_categories as string[]).join(', ')
    : undefined

  return (
    <div className="space-y-3">
      <MockupWorkspaceSection
        index={1}
        title={t('app.candidates.workspace.overview')}
        subtitle={t('app.candidates.workspace.overview_hint')}
        defaultOpen
      >
        <ReadOnlyField label={t('app.candidates.workspace.full_name')} value={passport.sections.identity.title} />
        <ReadOnlyField
          label={t('app.candidates.workspace.birth_date')}
          value={birthDate ? formatDateSafe(birthDate, locale) : undefined}
        />
        <ReadOnlyField label={t('app.candidates.workspace.citizenship')} value={citizenship} />
        <ReadOnlyField label={t('app.candidates.workspace.languages')} value={languages} />
        <ReadOnlyField
          label={t('app.candidates.workspace.phone')}
          value={candidate.masked ? t('app.candidates.workspace.hidden') : candidate.phone ?? undefined}
        />
        <ReadOnlyField
          label="Email"
          value={candidate.masked ? t('app.candidates.workspace.hidden') : candidate.email ?? undefined}
        />
        <ReadOnlyField label={t('app.candidates.workspace.city')} value={candidate.city ? String(candidate.city) : undefined} />
        <ReadOnlyField
          label={t('app.candidates.workspace.stage')}
          value={passport.sections.state.stageLabel || passport.sections.state.processLabel}
        />
      </MockupWorkspaceSection>

      <MockupWorkspaceSection
        index={2}
        title={t('app.candidates.workspace.extra')}
        subtitle={t('app.candidates.workspace.extra_hint')}
        defaultOpen
      >
        <ReadOnlyField
          label={t('app.candidates.workspace.experience')}
          value={
            experienceYears != null
              ? t('app.candidates.workspace.years', { values: { count: experienceYears } })
              : undefined
          }
        />
        <ReadOnlyField
          label={t('app.candidates.workspace.experience_eu')}
          value={
            rawExtra.experience_eu_years != null
              ? t('app.candidates.workspace.years', { values: { count: String(rawExtra.experience_eu_years) } })
              : undefined
          }
        />
        <ReadOnlyField label={t('app.candidates.workspace.licence')} value={licenseCategories} />
        <ReadOnlyField
          label="ADR"
          value={formatBool(rawExtra.has_adr as boolean | null, t('common.yes'), t('common.no'))}
        />
        <ReadOnlyField
          label={t('app.candidates.workspace.in_poland')}
          value={formatBool(rawExtra.in_poland as boolean | null, t('common.yes'), t('common.no'))}
        />
        <ReadOnlyField
          label={t('app.candidates.workspace.stay_basis')}
          value={rawExtra.poland_stay_basis ? String(rawExtra.poland_stay_basis) : undefined}
        />
        <ReadOnlyField
          label={t('app.candidates.workspace.preferred_channel')}
          value={extra.preferredContact ?? undefined}
        />
        <ReadOnlyField
          label={t('app.candidates.workspace.source')}
          value={candidate.source ? String(candidate.source) : undefined}
        />
      </MockupWorkspaceSection>

      <CandidateCustomFieldsReadOnlyBlock
        candidate={candidate}
        candidateProfile={candidateProfile}
        effectiveLayout={effectiveLayout}
        locale={locale}
      />

      {passport.sections.identity.masked ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          {t('app.candidates.workspace.masked_policy')}
        </p>
      ) : null}
    </div>
  )
}

export function CandidateContactsContent({ passport, candidate }: { passport: EntityPassport; candidate: AugmentedCandidate }) {
  const { t } = useI18n()
  const channels = passport.sections.contacts.channels

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">{passport.sections.contacts.displayName}</h3>
        {passport.sections.contacts.citizenship ? (
          <p className="mt-1 text-sm text-slate-600">
            {t('app.platform.entity_workspace.citizenship', {
              values: { value: passport.sections.contacts.citizenship },
            })}
          </p>
        ) : null}
        {passport.sections.contacts.preferredChannel ? (
          <p className="mt-1 text-sm text-slate-600">
            {t('app.candidates.workspace.preferred_channel_value', {
              values: { value: passport.sections.contacts.preferredChannel },
            })}
          </p>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {channels.map((ch) => (
          <div key={`${ch.kind}-${ch.value}`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{ch.kind}</p>
            {ch.href && !candidate.masked ? (
              <a href={ch.href} className="mt-2 block text-base font-semibold text-brand-700 hover:underline">
                {ch.display || ch.value}
              </a>
            ) : (
              <p className="mt-2 text-base font-semibold text-slate-900">{candidate.masked ? t('app.candidates.workspace.hidden') : ch.display || ch.value}</p>
            )}
          </div>
        ))}
      </div>

      {!channels.length ? <p className="text-sm text-slate-500">{t('app.candidates.workspace.no_contacts')}</p> : null}
    </div>
  )
}

export function CandidateTimelineContent({ passport }: { passport: EntityPassport }) {
  const { t } = useI18n()
  const items = passport.sections.timeline.items

  if (!items.length) {
    return <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">{t('app.candidates.workspace.no_events')}</p>
  }

  return (
    <ul className="space-y-2">
      {items.map((ev) => (
        <li key={ev.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">{ev.title}</p>
          {ev.description ? <p className="mt-1 text-sm text-slate-600">{ev.description}</p> : null}
          {ev.at ? <p className="mt-2 text-xs text-slate-400">{ev.at}</p> : null}
        </li>
      ))}
    </ul>
  )
}

export function CandidateRelationsContent({ passport }: { passport: EntityPassport }) {
  const { t } = useI18n()
  const items = passport.sections.relations.items

  if (!items.length) {
    return <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">{t('app.candidates.workspace.no_relations')}</p>
  }

  return (
    <ul className="space-y-2">
      {items.map((rel) => (
        <li key={rel.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {rel.kind === 'vacancy'
                ? t('app.candidates.workspace.rel_vacancy')
                : rel.kind === 'hr'
                  ? 'Handoff'
                  : t('app.candidates.workspace.rel_relation')}
            </p>
            {rel.href ? (
              <a href={rel.href} className="mt-1 block text-sm font-semibold text-brand-700 hover:underline">
                {rel.label}
              </a>
            ) : (
              <p className="mt-1 text-sm font-semibold text-slate-900">{rel.label}</p>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function CandidateTasksContent({ passport }: { passport: EntityPassport }) {
  const { t } = useI18n()
  const items = passport.sections.tasks.items

  if (!items.length) {
    return <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">{t('app.candidates.workspace.no_tasks')}</p>
  }

  return (
    <ul className="space-y-2">
      {items.map((task) => (
        <li
          key={task.id}
          className={clsx(
            'flex items-start gap-3 rounded-xl border px-4 py-3 shadow-sm',
            task.overdue ? 'border-rose-200 bg-rose-50/40' : 'border-slate-200 bg-white',
          )}
        >
          <span
            className={clsx(
              'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border',
              task.status === 'completed' || task.status === 'done'
                ? 'border-brand-600 bg-brand-600 text-white'
                : 'border-slate-300 bg-white',
            )}
            aria-hidden
          >
            {task.status === 'completed' || task.status === 'done' ? '✓' : null}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900">{task.title}</p>
            {task.dueAt ? <p className="text-xs text-slate-500">{task.dueAt}</p> : null}
          </div>
        </li>
      ))}
    </ul>
  )
}
