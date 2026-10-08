import { useMemo } from 'react'
import type {
  CurrentDocumentTypeVersion,
  DocumentRequirementLevel,
  RecruitmentProfileDocumentBinding,
} from '../../api/recruitmentProfiles'
import { useI18n } from '../../i18n'

export type DocumentConfig = RecruitmentProfileDocumentBinding

interface ProfileDocumentConstructorProps {
  catalog: CurrentDocumentTypeVersion[]
  value: RecruitmentProfileDocumentBinding[]
  onChange: (configs: RecruitmentProfileDocumentBinding[]) => void
  disabled?: boolean
}

const LEVELS: DocumentRequirementLevel[] = ['hidden', 'preferred', 'required']

export function completeDocumentBindings(
  catalog: CurrentDocumentTypeVersion[],
  bindings: RecruitmentProfileDocumentBinding[],
): RecruitmentProfileDocumentBinding[] {
  const byVersionId = new Map(bindings.map((binding) => [binding.document_type_version_id, binding]))
  return catalog.map((documentType, index) => {
    const existing = byVersionId.get(documentType.document_type_version_id)
    return {
      document_type_version_id: documentType.document_type_version_id,
      requirement_level: existing?.requirement_level ?? 'hidden',
      sort_order: existing?.sort_order ?? (index + 1) * 10,
    }
  }).sort((a, b) => a.sort_order - b.sort_order)
}

export default function ProfileDocumentConstructor({
  catalog,
  value,
  onChange,
  disabled = false,
}: ProfileDocumentConstructorProps) {
  const { t } = useI18n()
  const rows = useMemo(() => completeDocumentBindings(catalog, value), [catalog, value])

  const updateLevel = (documentTypeVersionId: string, requirementLevel: DocumentRequirementLevel) => {
    onChange(rows.map((row) =>
      row.document_type_version_id === documentTypeVersionId
        ? { ...row, requirement_level: requirementLevel }
        : row,
    ))
  }

  if (catalog.length === 0) {
    return <p className="text-sm text-slate-500">{t('admin.candidate_profiles_page.docs.empty')}</p>
  }

  return (
    <div className="space-y-2">
      {rows.map((binding) => {
        const documentType = catalog.find((item) => item.document_type_version_id === binding.document_type_version_id)
        if (!documentType) return null
        return (
          <div key={binding.document_type_version_id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
            <div className="min-w-0 flex-1">
              <div className="font-medium text-slate-900">{documentType.public_name}</div>
              <div className="truncate font-mono text-xs text-slate-500">
                {documentType.document_type_code} · {documentType.version_code}
              </div>
            </div>
            <select
              className="input min-w-36"
              value={binding.requirement_level}
              disabled={disabled}
              onChange={(event) => updateLevel(binding.document_type_version_id, event.target.value as DocumentRequirementLevel)}
              aria-label={`${documentType.public_name} requirement level`}
            >
              {LEVELS.map((level) => <option key={level} value={level}>{level}</option>)}
            </select>
          </div>
        )
      })}
    </div>
  )
}
