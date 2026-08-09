import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { ACTIVATION_PATHS, type ActivationBusinessType } from '../app/activationRoutes'

export type SuccessPathItemId =
  | 'company'
  | 'invite'
  | 'meta'
  | 'client'
  | 'vacancy'
  | 'lead'
  | 'contact'

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
  next_action_created?: boolean
}

const NEXT_ORDER_BY_TYPE: Record<ActivationBusinessType, SuccessPathItemId[]> = {
  employer: ['company', 'vacancy', 'meta', 'lead', 'contact', 'invite'],
  agency: ['company', 'client', 'vacancy', 'meta', 'lead', 'contact', 'invite'],
  services: ['company', 'client', 'meta', 'lead', 'contact', 'invite'],
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
      href: CRM_APP_PATHS.settingsIntegrationsMeta,
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
      {
        id: 'contact',
        done: Boolean(steps?.next_action_created),
        optional: false,
        deferred: false,
        href: ACTIVATION_PATHS.leads,
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
      {
        id: 'contact',
        done: Boolean(steps?.next_action_created),
        optional: false,
        deferred: false,
        href: ACTIVATION_PATHS.leads,
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
    {
      id: 'contact',
      done: Boolean(steps?.next_action_created),
      optional: false,
      deferred: false,
      href: ACTIVATION_PATHS.leads,
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
    if (item.id === 'invite') {
      const blockers = items.filter((i) => !i.optional && !i.done && i.id !== 'invite')
      if (blockers.length > 0) continue
    }
    return { id: item.id, href: item.href }
  }
  return null
}

export function isSuccessPathComplete(items: SuccessPathItem[]): boolean {
  return items.filter((i) => !i.optional).every((i) => i.done)
}
