import type { EntitySectionId } from '../entity-model/types'
import type { EntityModel, EntityPassport } from '../entity-model'
import type { EntityContextRailModel, EntityWorkspaceHeaderModel, EntityWorkspaceSectionId, EntityWorkspaceSummaryModel, EntityContextRailContactAction } from './types'
import { ENTITY_WORKSPACE_SECTION_ORDER } from './types'

const NAV_ENTITY_SECTIONS: Record<EntityWorkspaceSectionId, readonly EntitySectionId[]> = {
  overview: ['identity', 'state', 'ownership'],
  contacts: ['contacts'],
  documents: ['documents'],
  timeline: ['timeline'],
  relations: ['relations'],
  tasks: ['tasks'],
  outcome: ['outcome'],
  finance: [],
  comments: [],
  activity: ['timeline'],
}

export function resolveEnabledWorkspaceSections(model: EntityModel, passport: EntityPassport): EntityWorkspaceSectionId[] {
  return ENTITY_WORKSPACE_SECTION_ORDER.filter((navId) => {
    const entitySections = NAV_ENTITY_SECTIONS[navId]
    if (!entitySections.length) return false
    if (!entitySections.some((s) => model.sections.includes(s))) return false
    if (navId === 'outcome') return passport.sections.outcome != null
    return true
  })
}

export function projectEntityWorkspaceHeader(args: {
  passport: EntityPassport
  resourceTypeLabel: string
}): EntityWorkspaceHeaderModel {
  const { passport, resourceTypeLabel } = args
  const { identity, state, outcome } = passport.sections
  const subtitleParts = [resourceTypeLabel, identity.shortId ? `#${identity.shortId}` : null].filter(Boolean)

  return {
    title: identity.title,
    subtitle: subtitleParts.join(' · '),
    resourceTypeLabel,
    statusLabel: state.processLabel,
    statusSemantic: state.processPhase === 'terminal' ? 'status' : 'process_stage',
    stageLabel: state.stageLabel,
    stageSemantic: 'process_stage',
    outcomeLabel: outcome?.title,
    outcomeSemantic: outcome?.variant === 'success' ? 'status' : outcome ? 'status' : undefined,
  }
}

export function projectEntityWorkspaceSummary(passport: EntityPassport): EntityWorkspaceSummaryModel {
  const { state, ownership, documents, actions, relations } = passport.sections
  const cards: EntityWorkspaceSummaryModel['cards'] = []

  cards.push({
    id: 'stage',
    label: 'Текущий этап',
    value: state.stageLabel || state.processLabel,
    subValue: state.stageLabel && state.processLabel !== state.stageLabel ? state.processLabel : undefined,
    tone: state.processPhase === 'terminal' ? 'muted' : 'default',
  })

  if (actions.decisionTitle && actions.workAllowed) {
    cards.push({
      id: 'next',
      label: 'Следующее действие',
      value: actions.decisionTitle,
      tone: 'brand',
    })
  } else if (passport.sections.outcome?.title) {
    cards.push({
      id: 'outcome',
      label: 'Итог',
      value: passport.sections.outcome.title,
      subValue: passport.sections.outcome.body,
      tone: 'success',
    })
  }

  const why = state.why || documents.blockersSummary
  if (why) {
    cards.push({
      id: 'why',
      label: 'Почему сейчас',
      value: why,
      tone: 'warning',
    })
  }

  const primaryRelation = relations.items[0]
  if (primaryRelation) {
    cards.push({
      id: 'relation',
      label: primaryRelation.kind === 'vacancy' ? 'Подбор / Вакансия' : 'Связь',
      value: primaryRelation.label,
      href: primaryRelation.href,
    })
  }

  if (ownership.managerLabel) {
    cards.push({
      id: 'owner',
      label: 'Ответственный',
      value: ownership.managerLabel,
      tone: 'muted',
    })
  }

  return {
    cards,
    blockerHint: documents.blockersSummary,
  }
}

function mapChannelIcon(kind: string): EntityContextRailContactAction['icon'] | null {
  if (kind === 'phone') return 'phone'
  if (kind === 'whatsapp') return 'whatsapp'
  if (kind === 'email') return 'email'
  return null
}

export function projectEntityContextRail(passport: EntityPassport): EntityContextRailModel {
  const { actions, tasks, timeline, contacts } = passport.sections

  const quickContacts: EntityContextRailContactAction[] = contacts.channels
    .map((ch) => {
      const icon = mapChannelIcon(ch.kind)
      if (!icon || !ch.href) return null
      return {
        id: ch.kind,
        label: ch.display || ch.value,
        href: ch.href,
        icon,
      }
    })
    .filter((item): item is EntityContextRailContactAction => item != null)

  return {
    decisionTitle: actions.decisionTitle,
    decisionWhy: actions.decisionWhy,
    afterActionHint: actions.afterActionHint,
    actions: actions.workAllowed
      ? {
          primary: actions.primaryCapabilityId
            ? {
                id: actions.primaryCapabilityId,
                label: actions.decisionTitle || actions.primaryCapabilityId,
              }
            : null,
        }
      : undefined,
    tasks: tasks.items.map((t) => ({
      id: t.id,
      title: t.title,
      dueAt: t.dueAt,
      overdue: t.overdue,
      done: t.status === 'completed' || t.status === 'done',
    })),
    recentEvents: timeline.items.slice(0, 5).map((e) => ({
      id: e.id,
      at: e.at,
      title: e.title,
      description: e.description,
    })),
    quickContacts: quickContacts.length ? quickContacts : undefined,
  }
}
