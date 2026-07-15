import type { EntityPassport } from '../../platform/entity-model'
import type { EntityWorkspaceHeaderExtension } from '../../platform/entity-workspace'
import { formatDateSafe } from './candidateUtils'
import type { AugmentedCandidate } from './types'

type BuildCandidateHeaderExtensionArgs = {
  candidate: AugmentedCandidate
  passport: EntityPassport
  backHref: string
  backLabel: string
  locale: string
}

export function buildCandidateEntityWorkspaceHeaderExtension(
  args: BuildCandidateHeaderExtensionArgs,
): EntityWorkspaceHeaderExtension {
  const { candidate, passport, backHref, backLabel, locale } = args
  const chips: EntityWorkspaceHeaderExtension['chips'] = []

  if (passport.sections.contacts.citizenship) {
    chips.push({ id: 'citizenship', label: passport.sections.contacts.citizenship })
  }
  if (candidate.city) {
    chips.push({ id: 'city', label: String(candidate.city) })
  }
  if (candidate.phone && !candidate.masked) {
    chips.push({ id: 'phone', label: String(candidate.phone) })
  }

  const footerMeta: EntityWorkspaceHeaderExtension['footerMeta'] = []
  if (candidate.created_at) {
    footerMeta.push({
      label: 'Создан',
      value: formatDateSafe(String(candidate.created_at), locale),
    })
  }
  if (candidate.updated_at) {
    footerMeta.push({
      label: 'Обновлён',
      value: formatDateSafe(String(candidate.updated_at), locale),
    })
  }
  if (passport.sections.ownership.managerLabel) {
    footerMeta.push({
      label: 'Ответственный',
      value: passport.sections.ownership.managerLabel,
    })
  }

  const shortId = passport.sections.identity.shortId
  const entityRefLabel = shortId ? `#${shortId}` : undefined

  return {
    backHref,
    backLabel,
    avatarFallback: passport.sections.identity.title,
    entityRefLabel,
    sourceLabel: candidate.source ? String(candidate.source) : undefined,
    chips,
    footerMeta,
  }
}
