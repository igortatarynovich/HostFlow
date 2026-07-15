import type { AcceptedEvidenceVariant, RequirementChecklistItem } from '../../../api/candidateRequirements'
import type { useI18n } from '../../../i18n'
import { variantDocumentTypeCodes } from '../requirementsChecklistPresentation'

export function requirementTitle(
  t: ReturnType<typeof useI18n>['t'],
  item: RequirementChecklistItem,
): string {
  const code = item.requirement_code
  const fromApi = String(item.public_name || '').trim()
  if (fromApi) return fromApi
  return t(`app.candidate_card.requirements_checklist.requirements.${code}`, {
    defaultValue: code.replace(/_/g, ' '),
  })
}

export function variantLabel(
  t: ReturnType<typeof useI18n>['t'],
  variant: AcceptedEvidenceVariant,
  labelForType: (code: string) => string,
): string {
  const code = variant.evidence_variant_code
  const fromKey = t(`app.candidate_card.requirements_checklist.variants.${code}`, { defaultValue: '' }).trim()
  if (fromKey) return fromKey
  const types = variantDocumentTypeCodes(variant)
  if (types.length === 1) return labelForType(types[0])
  if (variant.all_of?.length) {
    return types.map(labelForType).join(' + ')
  }
  return types.map(labelForType).join(' / ')
}
