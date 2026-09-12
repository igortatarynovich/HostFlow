export type ApplicationModule = 'sales' | 'recruitment'

export type ApplicationStatus = 'new' | 'in_progress' | 'waiting' | 'completed' | 'rejected' | 'questionnaire_submitted'

export type ApplicationTab = 'all' | 'new' | 'in_progress' | 'waiting' | 'completed'

export type ApplicationContact = {
  name: string
  phone?: string | null
  email?: string | null
}

/** Product-facing inbound object — UI Constitution v1. Never Lead. */
export type Application = {
  id: string
  module: ApplicationModule
  contact: ApplicationContact
  title: string
  subtitle?: string | null
  source?: string | null
  status: ApplicationStatus
  tab_bucket: ApplicationTab
  assignee_id?: string | null
  next_action?: string | null
  last_activity_at?: string | null
  created_at?: string | null
  priority?: string | null
  tags?: string[]
  extensions?: Record<string, unknown>
  outcome_entity_id?: string | null
  outcome_entity_type?: string | null
  /** Stage 3 slice 3 — SalesInquiry product id (same as id when SI-backed). */
  sales_inquiry_id?: string | null
  /** Transport Lead id for Lead-only sections (questionnaire, notes, timeline). */
  transport_lead_id?: string | null
  /** Vacancy Requirements × canonical facts — computed verdict (not persisted). */
  requirements_verdict?: RequirementsVerdict | null
}

export type RequirementsVerdictStatus = 'fit' | 'missing' | 'not_fit'

export type RequirementsVerdictNextAction = {
  code: 'fits' | 'collect_fact' | 'reject' | string
  message?: string
  fact_code?: string
  requirement?: string
  reason_code?: string
}

export type RequirementsVerdictExplanation = {
  kind?: string
  code?: string
  outcome?: RequirementsVerdictStatus | string
  message?: string
  requirement?: string
  qualified_code?: string
  document_type_code?: string
}

export type RequirementsVerdict = {
  ok?: boolean
  contract_id?: string
  status?: RequirementsVerdictStatus | string
  explanation?: RequirementsVerdictExplanation[]
  next_action?: RequirementsVerdictNextAction
}

export type ApplicationListResponse = {
  items: Application[]
  total: number
  counts?: Partial<Record<ApplicationTab, number>>
}
