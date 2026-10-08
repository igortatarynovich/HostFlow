import { useMemo } from 'react'
import type { CanonicalField } from '../../api/fieldRegistry'
import type {
  FieldRequirementLevel,
  RecruitmentProfileFieldBinding,
} from '../../api/recruitmentProfiles'
import { useI18n } from '../../i18n'

export type FieldConfig = RecruitmentProfileFieldBinding

interface ProfileFieldConstructorProps {
  catalog: CanonicalField[]
  value: RecruitmentProfileFieldBinding[]
  onChange: (fields: RecruitmentProfileFieldBinding[]) => void
  disabled?: boolean
}

const LEVELS: FieldRequirementLevel[] = ['hidden', 'optional', 'required']

export function completeFieldBindings(
  catalog: CanonicalField[],
  bindings: RecruitmentProfileFieldBinding[],
): RecruitmentProfileFieldBinding[] {
  const byId = new Map(bindings.map((binding) => [binding.canonical_field_id, binding]))
  return catalog.map((field, index) => {
    const existing = byId.get(field.id)
    return {
      canonical_field_id: field.id,
      qualified_code: field.qualified_code,
      requirement_level: existing?.requirement_level ?? 'hidden',
      sort_order: existing?.sort_order ?? (index + 1) * 10,
    }
  }).sort((a, b) => a.sort_order - b.sort_order)
}

export default function ProfileFieldConstructor({
  catalog,
  value,
  onChange,
  disabled = false,
}: ProfileFieldConstructorProps) {
  const { t } = useI18n()
  const rows = useMemo(() => completeFieldBindings(catalog, value), [catalog, value])

  const updateLevel = (canonicalFieldId: string, requirementLevel: FieldRequirementLevel) => {
    onChange(rows.map((row) =>
      row.canonical_field_id === canonicalFieldId
        ? { ...row, requirement_level: requirementLevel }
        : row,
    ))
  }

  if (catalog.length === 0) {
    return <p className="text-sm text-slate-500">{t('app.settings.candidate_profiles.field_constructor.empty')}</p>
  }

  return (
    <div className="space-y-2">
      {rows.map((binding) => {
        const field = catalog.find((item) => item.id === binding.canonical_field_id)
        if (!field) return null
        return (
          <div key={binding.canonical_field_id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
            <div className="min-w-0 flex-1">
              <div className="font-medium text-slate-900">{field.name}</div>
              <div className="truncate font-mono text-xs text-slate-500">
                {field.qualified_code} · {field.field_type}
              </div>
            </div>
            <select
              className="input min-w-36"
              value={binding.requirement_level}
              disabled={disabled}
              onChange={(event) => updateLevel(binding.canonical_field_id, event.target.value as FieldRequirementLevel)}
              aria-label={`${field.name} requirement level`}
            >
              {LEVELS.map((level) => <option key={level} value={level}>{level}</option>)}
            </select>
          </div>
        )
      })}
    </div>
  )
}
