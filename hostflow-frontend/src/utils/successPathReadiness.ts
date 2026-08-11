import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { ACTIVATION_PATHS, type ActivationBusinessType } from '../app/activationRoutes'

export type SuccessPathItemId =
  | 'company'
  | 'invite'
  | 'meta'
  | 'client'
  | 'vacancy'
  | 'lead'

export type SuccessPathItem = {
  id: SuccessPathItemId
  done: boolean
  optional: boolean
  deferred: boolean
  href: string
}

export type SuccessPathNextAction = {
  id: SuccessPathItemId
  href: string
}

export type SuccessPathStepsLike = {
  company_created?: boolean
  first_lead_created?: boolean
  first_vacancy_created?: boolean
  first_client_created?: boolean
}

const NEXT_ORDER_BY_TYPE: Record<ActivationBusinessType, SuccessPathItemId[]> = {
  // Optional source/integrations step comes after core path (not before first lead).
  employer: ['company', 'vacancy', 'lead', 'meta', 'invite'],
  agency: ['company', 'client', 'vacancy', 'lead', 'meta', 'invite'],
  services: ['company', 'client', 'lead', 'meta', 'invite'],
}

export function normalizeSuccessPathBusinessType(
  value: string | null | undefined,
): ActivationBusinessType {
  if (value === 'employer' || value === 'services' || value === 'agency') return value
  return 'agency'
}

export function buildSuccessPathItems(params: {
  businessType: ActivationBusinessType
  steps: SuccessPathStepsLike | null | undefined
  metaConnectedOrDeferred: boolean
  metaDeferredOnly: boolean
  teammatesInvited: boolean
}): SuccessPathItem[] {
  const { businessType, steps, metaConnectedOrDeferred, metaDeferredOnly, teammatesInvited } =
    params
  const firstLead = Boolean(steps?.first_lead_created)
  const firstClient = Boolean(steps?.first_client_created)
  const firstVacancy = Boolean(steps?.first_vacancy_created)

  const items: SuccessPathItem[] = [
    {
      id: 'company',
      done: Boolean(steps?.company_created),
      optional: false,
      deferred: false,
      href: CRM_APP_PATHS.platformSetup,
    },
    {
      id: 'invite',
      done: teammatesInvited,
      optional: true,
      deferred: false,
      href: CRM_APP_PATHS.settingsUsers,
    },
    {
      id: 'meta',
      done: metaConnectedOrDeferred,
      optional: true,
      deferred: metaDeferredOnly,
      // Hub of intake sources (Meta is one of many) — not a Meta-only deep link.
      href: CRM_APP_PATHS.settingsIntegrations,
    },
  ]

  if (businessType === 'employer') {
    items.push(
      {
        id: 'vacancy',
        done: firstVacancy,
        optional: false,
        deferred: false,
        href: CRM_APP_PATHS.setupVacancy,
      },
      {
        id: 'lead',
        done: firstLead,
        optional: false,
        deferred: false,
        href: firstLead ? ACTIVATION_PATHS.leads : CRM_APP_PATHS.setupIntake,
      },
    )
    return items
  }

  if (businessType === 'services') {
    items.push(
      {
        id: 'client',
        // Lead from ads can be first value for services (potential client).
        done: firstClient || firstLead,
        optional: false,
        deferred: false,
        href: CRM_APP_PATHS.setupClient,
      },
      {
        id: 'lead',
        done: firstLead,
        optional: false,
        deferred: false,
        href: firstLead ? ACTIVATION_PATHS.leads : CRM_APP_PATHS.setupIntake,
      },
    )
    return items
  }

  // agency
  items.push(
    {
      id: 'client',
      done: firstClient,
      optional: false,
      deferred: false,
      href: CRM_APP_PATHS.setupClient,
    },
    {
      id: 'vacancy',
      done: firstVacancy,
      optional: false,
      deferred: false,
      href: CRM_APP_PATHS.setupVacancy,
    },
    {
      id: 'lead',
      done: firstLead,
      optional: false,
      deferred: false,
      href: firstLead ? ACTIVATION_PATHS.leads : CRM_APP_PATHS.setupIntake,
    },
  )
  return items
}

export function pickSuccessPathNext(
  items: SuccessPathItem[],
  businessType: ActivationBusinessType,
): SuccessPathNextAction | null {
  const order = NEXT_ORDER_BY_TYPE[businessType]
  const byId = new Map(items.map((item) => [item.id, item]))
  for (const id of order) {
    const item = byId.get(id)
    if (!item || item.done) continue
    if (item.optional) {
      // Optional steps (sources, invite) never block the primary path.
      const blockers = items.filter((i) => !i.optional && !i.done)
      if (blockers.length > 0) continue
    }
    return { id: item.id, href: item.href }
  }
  return null
}

export function isSuccessPathComplete(items: SuccessPathItem[]): boolean {
  return items.filter((i) => !i.optional).every((i) => i.done)
}
