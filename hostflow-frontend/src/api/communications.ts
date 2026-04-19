import api from './client'

export type CommunicationChannelKey =
  | 'whatsapp'
  | 'telegram'
  | 'viber'
  | 'messenger'
  | 'instagram'
  | 'sms'
  | 'email'

export type ChannelRoutingMode = 'manual' | 'round_robin' | 'candidate_manager'
export type QueueStrategy = 'manual' | 'round_robin' | 'weighted_round_robin' | 'least_busy'
export type AvailabilityState = 'available' | 'busy' | 'offline' | 'break' | 'meeting'

export type CommunicationChannelConfig = {
  key: CommunicationChannelKey
  enabled: boolean
  inboundEnabled: boolean
  outboundEnabled: boolean
  routingMode: ChannelRoutingMode
  responseSlaMinutes: number
}

export type CommunicationsChannelsSettings = {
  businessHoursStart: string
  businessHoursEnd: string
  timezone: string
  channels: CommunicationChannelConfig[]
  candidateReplyTemplate: string
  clientReplyTemplate: string
  consentRequired: boolean
}

export type CommunicationsEmailSettings = {
  incomingEnabled: boolean
  incomingAlias: string
  autoThreading: boolean
  syncIntervalMinutes: number
  defaultMailbox: 'candidates' | 'clients' | 'operations'
  signatureCandidates: string
  signatureClients: string
}

export type PlannerSettings = {
  view: 'agenda' | 'week'
  workStart: string
  workEnd: string
  showWeekends: boolean
  slotMinutes: 15 | 30 | 60
}

export type ManagerScheduleSlot = {
  day: 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'
  start: string
  end: string
  enabled: boolean
}

export type ManagerAvailability = {
  state: AvailabilityState
  note: string
  busyUntil: string | null
  currentLoad: number
  maxConcurrentChats: number
  maxConcurrentCalls: number
}

export type ManagerQueueItem = {
  managerId: string
  enabled: boolean
  priorityWeight: number
  queueOrder: number
  skills: string[]
  channels: CommunicationChannelKey[]
  languageCodes: string[]
  candidateTypes: string[]
  schedule: ManagerScheduleSlot[]
  availability: ManagerAvailability
}

export type ManagerQueueSettings = {
  enabled: boolean
  strategy: QueueStrategy
  fallbackToManual: boolean
  rebalanceOnStatusChange: boolean
  respectSchedules: boolean
  respectAvailability: boolean
  items: ManagerQueueItem[]
}

export type CommunicationsComplianceSettings = {
  requireConsentForOutboundCandidateMessaging: boolean
  allowClientMessagingWithoutConsent: boolean
  auditRetentionDays: number
  maskCandidateDataInClientThreads: boolean
}

export type CommunicationsSlaRecipientMode = 'assignee_or_owner' | 'assignee_only' | 'owner_only'

export type CommunicationsSlaSettings = {
  enabled: boolean
  createNotifications: boolean
  createReminders: boolean
  recipientMode: CommunicationsSlaRecipientMode
  mutedChannels: CommunicationChannelKey[]
  escalationTargets: string[]
}

export type CommunicationsEntitlement = {
  enabled: boolean
  planRequired: 'starter' | 'pro' | 'enterprise' | null
  seatScoped: boolean
}

export type CommunicationsEntitlementsSettings = {
  modules: Record<string, CommunicationsEntitlement>
}

export type CommunicationsRoleAccessSettings = {
  messages: string[]
  email: string[]
  calendar: string[]
  planner: string[]
  teamAvailability: string[]
  myAvailability: string[]
  timeOffRequests: string[]
  communicationsAdmin: string[]
}

export type CommunicationsAccessSettings = {
  roles: CommunicationsRoleAccessSettings
  usersOverrides: Record<string, Record<string, boolean>>
}

export type CommunicationCommandActionType =
  | 'mark_read'
  | 'archive'
  | 'unarchive'
  | 'delete'
  | 'restore'
  | 'priority_high'
  | 'priority_normal'
  | 'tag_add'
  | 'tag_remove'
  | 'move_folder'

export type CommunicationCommandAction = {
  type: CommunicationCommandActionType
  value?: string | null
}

export type CommunicationCommandTemplate = {
  id: string
  label: string
  target: 'email' | 'messages' | 'both'
  enabled: boolean
  actions: CommunicationCommandAction[]
}

export type CommunicationsCommandsSettings = {
  items: CommunicationCommandTemplate[]
}

export type CommunicationMessageTemplate = {
  id: string
  label: string
  body: string
  visibility: 'private' | 'company'
  target: 'messages' | 'email' | 'both'
  ownerUserId?: string | null
  enabled: boolean
}

export type CommunicationsMessageTemplatesSettings = {
  items: CommunicationMessageTemplate[]
}

export type CommunicationsWorkspaceSettings = {
  channels: CommunicationsChannelsSettings
  email: CommunicationsEmailSettings
  planner: PlannerSettings
  managerQueue: ManagerQueueSettings
  sla: CommunicationsSlaSettings
  compliance: CommunicationsComplianceSettings
  entitlements: CommunicationsEntitlementsSettings
  access: CommunicationsAccessSettings
  commands: CommunicationsCommandsSettings
  messageTemplates: CommunicationsMessageTemplatesSettings
}

export type CommunicationsSettingsPatch = Partial<CommunicationsWorkspaceSettings>

export type CommunicationThread = {
  id: string
  channel: string
  channel_account_id?: string | null
  channel_thread_ref?: string | null
  subject?: string | null
  status: string
  direction_hint?: string | null
  entity_type?: string | null
  entity_id?: string | null
  linked_company_id?: string | null
  linked_candidate_id?: string | null
  owner_id?: string | null
  assignee_id?: string | null
  queue_assigned_by?: string | null
  priority: string
  sla_due_at?: string | null
  participants_json: Record<string, any>
  tags_json: any[]
  thread_meta: Record<string, any>
  last_message_at?: string | null
  last_inbound_at?: string | null
  last_outbound_at?: string | null
  last_message_preview?: string | null
  unread_count: number
  is_archived: boolean
  created_at: string
  updated_at: string
}

export type CommunicationMessage = {
  id: string
  thread_id: string
  channel: string
  message_type: string
  direction: 'inbound' | 'outbound' | 'system'
  sender_type?: string | null
  sender_id?: string | null
  sender_label?: string | null
  sender_address?: string | null
  recipient_type?: string | null
  recipient_id?: string | null
  recipient_label?: string | null
  recipient_address?: string | null
  subject?: string | null
  body_text?: string | null
  body_html?: string | null
  attachments_json: any[]
  payload: Record<string, any>
  external_message_ref?: string | null
  delivery_status: string
  error_message?: string | null
  sent_at?: string | null
  delivered_at?: string | null
  read_at?: string | null
  is_internal_note: boolean
  created_at: string
  updated_at: string
}

export type CommunicationThreadListResponse = {
  items: CommunicationThread[]
  total: number
}

export type CommunicationMessageListResponse = {
  items: CommunicationMessage[]
  total: number
}

export type CommunicationThreadDetailResponse = {
  thread: CommunicationThread
  messages: CommunicationMessage[]
}

export type CommunicationChannelAccount = {
  id: string
  channel: string
  account_label: string
  external_account_ref?: string | null
  inbox_address?: string | null
  is_active: boolean
  settings_json: Record<string, any>
  created_at: string
  updated_at: string
}

export type CommunicationAccountOAuthStartResponse = {
  ok: boolean
  action: string
  provider: string
  state: string
  auth_url: string
  account: CommunicationChannelAccount
}

export type CommunicationAccountOAuthCompleteResponse = {
  ok: boolean
  action: string
  provider: string
  detail?: string | null
  account: CommunicationChannelAccount
}

export type CommunicationAccountSyncCursor = {
  account_id: string
  cursor_key: string
  cursor_value?: string | null
  meta: Record<string, any>
  updated_at?: string | null
}

export type CommunicationDispatchResponse = {
  dispatched: boolean
  reason?: string | null
  message: CommunicationMessage
  thread: CommunicationThread
}

export type CommunicationTimeOffRequest = {
  id: string
  tenant_id: string
  requester_user_id: string
  requester_label?: string | null
  approver_user_id?: string | null
  approver_label?: string | null
  request_type: string
  status: string
  start_date: string
  end_date: string
  partial_day?: string | null
  reason?: string | null
  decision_note?: string | null
  requested_at?: string | null
  decided_at?: string | null
  payload: Record<string, any>
  created_at: string
  updated_at: string
}

export type WorkingHoursWindow = { from: string; to: string }
export type WorkingHoursDay = { weekday: number; enabled: boolean; windows: WorkingHoursWindow[] }
export type WorkingHoursSchedule = { tz?: string | null; days: WorkingHoursDay[] }

export type CommunicationAllocationAudit = {
  id: string
  mode: string
  channel: string
  thread_id?: string | null
  actor_user_id?: string | null
  strategy?: string | null
  assigned: boolean
  assignee_id?: string | null
  reason?: string | null
  evaluated_at?: string | null
  candidates_json: Array<Record<string, any>>
  payload: Record<string, any>
  created_at: string
  updated_at: string
}

export type CommunicationCommandAudit = {
  id: string
  thread_id: string
  channel: string
  command_id: string
  command_label?: string | null
  actor_user_id?: string | null
  action_count: number
  actions_json: Array<Record<string, any>>
  payload: Record<string, any>
  executed_at?: string | null
  created_at: string
  updated_at: string
}

export type CommunicationSchedulerStatus = {
  enabled: boolean
  active: boolean
  started_at?: string | null
  stopped_at?: string | null
  tick_seconds: number
  last_tick_started_at?: string | null
  last_tick_finished_at?: string | null
  last_tick_duration_ms?: number | null
  last_tick_error?: string | null
  last_tick_summary: Record<string, any>
  tenants: Record<string, any>
}

export type CommunicationPlannerEvent = {
  id: string
  tenant_id: string
  title: string
  description?: string | null
  kind: string
  status: string
  priority: string
  start_at: string
  end_at?: string | null
  all_day: boolean
  owner_id?: string | null
  assignee_id?: string | null
  entity_type?: string | null
  entity_id?: string | null
  linked_candidate_id?: string | null
  linked_company_id?: string | null
  source: string
  payload: Record<string, any>
  created_at: string
  updated_at: string
}

const DEFAULT_CHANNELS: CommunicationChannelConfig[] = [
  { key: 'whatsapp', enabled: false, inboundEnabled: true, outboundEnabled: true, routingMode: 'candidate_manager', responseSlaMinutes: 30 },
  { key: 'telegram', enabled: false, inboundEnabled: true, outboundEnabled: true, routingMode: 'manual', responseSlaMinutes: 30 },
  { key: 'viber', enabled: false, inboundEnabled: true, outboundEnabled: true, routingMode: 'manual', responseSlaMinutes: 60 },
  { key: 'messenger', enabled: false, inboundEnabled: true, outboundEnabled: false, routingMode: 'round_robin', responseSlaMinutes: 30 },
  { key: 'instagram', enabled: false, inboundEnabled: true, outboundEnabled: false, routingMode: 'round_robin', responseSlaMinutes: 30 },
  { key: 'sms', enabled: true, inboundEnabled: false, outboundEnabled: true, routingMode: 'manual', responseSlaMinutes: 15 },
  { key: 'email', enabled: true, inboundEnabled: true, outboundEnabled: true, routingMode: 'candidate_manager', responseSlaMinutes: 120 },
]

const DEFAULT_WEEK_SCHEDULE: ManagerScheduleSlot[] = [
  { day: 'mon', start: '09:00', end: '17:00', enabled: true },
  { day: 'tue', start: '09:00', end: '17:00', enabled: true },
  { day: 'wed', start: '09:00', end: '17:00', enabled: true },
  { day: 'thu', start: '09:00', end: '17:00', enabled: true },
  { day: 'fri', start: '09:00', end: '17:00', enabled: true },
  { day: 'sat', start: '09:00', end: '13:00', enabled: false },
  { day: 'sun', start: '09:00', end: '13:00', enabled: false },
]

export const DEFAULT_COMMUNICATIONS_SETTINGS: CommunicationsWorkspaceSettings = {
  channels: {
    businessHoursStart: '08:00',
    businessHoursEnd: '18:00',
    timezone: 'Europe/Warsaw',
    channels: DEFAULT_CHANNELS,
    candidateReplyTemplate: 'Здравствуйте! Получили ваше сообщение. Ответим в ближайшее время.',
    clientReplyTemplate: 'Dzień dobry, wiadomość została przyjęta do obsługi. Wrócimy z odpowiedzią możliwie szybko.',
    consentRequired: true,
  },
  email: {
    incomingEnabled: false,
    incomingAlias: '',
    autoThreading: true,
    syncIntervalMinutes: 5,
    defaultMailbox: 'candidates',
    signatureCandidates: 'Zespół rekrutacji',
    signatureClients: 'Zespół HostFlow',
  },
  planner: {
    view: 'agenda',
    workStart: '08:00',
    workEnd: '18:00',
    showWeekends: false,
    slotMinutes: 30,
  },
  managerQueue: {
    enabled: true,
    strategy: 'round_robin',
    fallbackToManual: true,
    rebalanceOnStatusChange: true,
    respectSchedules: true,
    respectAvailability: true,
    items: [],
  },
  sla: {
    enabled: true,
    createNotifications: true,
    createReminders: true,
    recipientMode: 'assignee_or_owner',
    mutedChannels: [],
    escalationTargets: ['priority', 'manual_review', 'supervisor_desk'],
  },
  compliance: {
    requireConsentForOutboundCandidateMessaging: true,
    allowClientMessagingWithoutConsent: true,
    auditRetentionDays: 365,
    maskCandidateDataInClientThreads: true,
  },
  entitlements: {
    modules: {
      messages: { enabled: true, planRequired: null, seatScoped: false },
      email: { enabled: true, planRequired: 'pro', seatScoped: false },
      calendar: { enabled: true, planRequired: null, seatScoped: false },
      planner: { enabled: true, planRequired: null, seatScoped: false },
      availability: { enabled: true, planRequired: null, seatScoped: true },
      timeOff: { enabled: true, planRequired: 'pro', seatScoped: true },
      communicationsAdmin: { enabled: true, planRequired: null, seatScoped: false },
    },
  },
  access: {
    roles: {
      messages: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor'],
      email: ['administrator', 'supervisor', 'recruiter', 'client_manager'],
      calendar: ['administrator', 'supervisor', 'recruiter', 'client_manager'],
      planner: ['administrator', 'supervisor', 'recruiter', 'client_manager'],
      teamAvailability: ['administrator', 'supervisor'],
      myAvailability: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor'],
      timeOffRequests: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor'],
      communicationsAdmin: ['administrator', 'supervisor'],
    },
    usersOverrides: {},
  },
  commands: {
    items: [
      {
        id: 'cmd_archive_done',
        label: 'Archive completed',
        target: 'both',
        enabled: true,
        actions: [{ type: 'mark_read' }, { type: 'archive' }],
      },
      {
        id: 'cmd_escalate_high',
        label: 'Escalate priority',
        target: 'both',
        enabled: true,
        actions: [{ type: 'priority_high' }, { type: 'tag_add', value: 'escalation' }],
      },
      {
        id: 'cmd_handoff_ready',
        label: 'Ready for handoff',
        target: 'both',
        enabled: true,
        actions: [{ type: 'tag_add', value: 'handoff_ready' }, { type: 'mark_read' }],
      },
      {
        id: 'cmd_no_response_followup',
        label: 'No response follow-up',
        target: 'both',
        enabled: true,
        actions: [{ type: 'tag_add', value: 'followup_needed' }, { type: 'priority_high' }],
      },
      {
        id: 'cmd_move_to_hr',
        label: 'Move to HR folder',
        target: 'email',
        enabled: true,
        actions: [{ type: 'move_folder', value: 'HR' }],
      },
    ],
  },
  messageTemplates: {
    items: [
      {
        id: 'msg_tpl_acknowledge',
        label: 'Acknowledge received',
        body: 'Thank you, we received your message and will reply shortly.',
        visibility: 'company',
        target: 'messages',
        ownerUserId: null,
        enabled: true,
      },
      {
        id: 'msg_tpl_docs_request',
        label: 'Request documents',
        body: 'Please send the requested documents at your earliest convenience.',
        visibility: 'company',
        target: 'both',
        ownerUserId: null,
        enabled: true,
      },
    ],
  },
}

export function defaultQueueItemForManager(managerId: string): ManagerQueueItem {
  return {
    managerId,
    enabled: true,
    priorityWeight: 100,
    queueOrder: 0,
    skills: [],
    channels: ['whatsapp', 'telegram', 'instagram', 'sms', 'email'],
    languageCodes: [],
    candidateTypes: [],
    schedule: DEFAULT_WEEK_SCHEDULE.map((s) => ({ ...s })),
    availability: {
      state: 'available',
      note: '',
      busyUntil: null,
      currentLoad: 0,
      maxConcurrentChats: 10,
      maxConcurrentCalls: 3,
    },
  }
}

function normalizeChannelList(source: unknown): CommunicationChannelConfig[] {
  const rawList = Array.isArray(source) ? source : []
  const byKey = new Map<string, CommunicationChannelConfig>()
  rawList.forEach((raw) => {
    if (!raw || typeof raw !== 'object') return
    const item = raw as Partial<CommunicationChannelConfig>
    const key = String(item.key || '') as CommunicationChannelKey
    if (!key) return
    byKey.set(key, {
      key,
      enabled: Boolean(item.enabled),
      inboundEnabled: item.inboundEnabled !== false,
      outboundEnabled: item.outboundEnabled !== false,
      routingMode:
        item.routingMode === 'manual' || item.routingMode === 'round_robin' || item.routingMode === 'candidate_manager'
          ? item.routingMode
          : 'manual',
      responseSlaMinutes: Math.max(5, Number(item.responseSlaMinutes) || 30),
    })
  })
  return DEFAULT_CHANNELS.map((d) => byKey.get(d.key) ?? { ...d })
}

function normalizeQueueItems(items: unknown): ManagerQueueItem[] {
  if (!Array.isArray(items)) return []
  return items
    .filter((x) => x && typeof x === 'object')
    .map((x, idx) => {
      const raw = x as Partial<ManagerQueueItem>
      const base = defaultQueueItemForManager(String(raw.managerId || ''))
      return {
        ...base,
        ...raw,
        managerId: String(raw.managerId || '').trim(),
        queueOrder: Number.isFinite(Number(raw.queueOrder)) ? Number(raw.queueOrder) : idx,
        priorityWeight: Number.isFinite(Number(raw.priorityWeight)) ? Math.max(1, Number(raw.priorityWeight)) : 100,
        channels: Array.isArray(raw.channels) ? raw.channels.filter(Boolean) as CommunicationChannelKey[] : base.channels,
        skills: Array.isArray(raw.skills) ? raw.skills.map(String) : [],
        languageCodes: Array.isArray(raw.languageCodes) ? raw.languageCodes.map(String) : [],
        candidateTypes: Array.isArray(raw.candidateTypes) ? raw.candidateTypes.map(String) : [],
        schedule: Array.isArray(raw.schedule)
          ? raw.schedule
              .filter((s) => s && typeof s === 'object')
              .map((s) => ({
                ...DEFAULT_WEEK_SCHEDULE.find((d) => d.day === (s as any).day)!,
                ...(s as any),
              }))
          : base.schedule,
        availability: {
          ...base.availability,
          ...(raw.availability && typeof raw.availability === 'object' ? raw.availability : {}),
        },
      }
    })
    .filter((x) => Boolean(x.managerId))
}

function normalizeCommands(items: unknown): CommunicationCommandTemplate[] {
  if (!Array.isArray(items)) return []
  return items
    .filter((x) => x && typeof x === 'object')
    .map((x, idx) => {
      const raw = x as Partial<CommunicationCommandTemplate>
      const actions = Array.isArray(raw.actions)
        ? raw.actions
            .filter((a) => a && typeof a === 'object' && typeof (a as any).type === 'string')
            .map((a) => ({ type: (a as any).type as CommunicationCommandActionType, value: (a as any).value ?? null }))
        : []
      return {
        id: String(raw.id || `cmd_${idx + 1}`),
        label: String(raw.label || `Command ${idx + 1}`),
        target: raw.target === 'email' || raw.target === 'messages' ? raw.target : 'both',
        enabled: raw.enabled !== false,
        actions,
      }
    })
}

function normalizeMessageTemplates(items: unknown): CommunicationMessageTemplate[] {
  if (!Array.isArray(items)) return []
  return items
    .filter((x) => x && typeof x === 'object')
    .map((x, idx) => {
      const raw = x as Partial<CommunicationMessageTemplate>
      return {
        id: String(raw.id || `msg_tpl_${idx + 1}`),
        label: String(raw.label || `Template ${idx + 1}`),
        body: String(raw.body || ''),
        visibility: raw.visibility === 'company' ? 'company' : 'private',
        target: raw.target === 'email' || raw.target === 'both' ? raw.target : 'messages',
        ownerUserId: raw.ownerUserId || null,
        enabled: raw.enabled !== false,
      }
    })
}

export function normalizeCommunicationsSettings(input: Partial<CommunicationsWorkspaceSettings> | null | undefined): CommunicationsWorkspaceSettings {
  const source = input || {}
  return {
    channels: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.channels,
      ...(source.channels || {}),
      channels: normalizeChannelList(source.channels?.channels),
    },
    email: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.email,
      ...(source.email || {}),
      defaultMailbox:
        source.email?.defaultMailbox === 'clients' || source.email?.defaultMailbox === 'operations'
          ? source.email.defaultMailbox
          : 'candidates',
    },
    planner: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.planner,
      ...(source.planner || {}),
      slotMinutes:
        source.planner?.slotMinutes === 15 || source.planner?.slotMinutes === 60 ? source.planner.slotMinutes : 30,
    },
    managerQueue: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.managerQueue,
      ...(source.managerQueue || {}),
      items: normalizeQueueItems(source.managerQueue?.items),
    },
    sla: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.sla,
      ...(source.sla || {}),
      recipientMode:
        source.sla?.recipientMode === 'assignee_only' || source.sla?.recipientMode === 'owner_only'
          ? source.sla.recipientMode
          : 'assignee_or_owner',
      mutedChannels: Array.isArray(source.sla?.mutedChannels)
        ? source.sla!.mutedChannels
            .map((x) => String(x || '').trim().toLowerCase())
            .filter((x): x is CommunicationChannelKey => ['whatsapp', 'telegram', 'viber', 'messenger', 'instagram', 'sms', 'email'].includes(x))
        : [],
      escalationTargets: Array.isArray(source.sla?.escalationTargets)
        ? source.sla!.escalationTargets.map((x) => String(x || '').trim()).filter(Boolean)
        : DEFAULT_COMMUNICATIONS_SETTINGS.sla.escalationTargets,
    },
    compliance: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.compliance,
      ...(source.compliance || {}),
    },
    entitlements: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.entitlements,
      ...(source.entitlements || {}),
      modules: {
        ...DEFAULT_COMMUNICATIONS_SETTINGS.entitlements.modules,
        ...(source.entitlements?.modules || {}),
      },
    },
    access: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.access,
      ...(source.access || {}),
      roles: {
        ...DEFAULT_COMMUNICATIONS_SETTINGS.access.roles,
        ...(source.access?.roles || {}),
      },
      usersOverrides:
        source.access?.usersOverrides && typeof source.access.usersOverrides === 'object'
          ? source.access.usersOverrides
          : {},
    },
    commands: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.commands,
      ...(source.commands || {}),
      items: normalizeCommands(source.commands?.items),
    },
    messageTemplates: {
      ...DEFAULT_COMMUNICATIONS_SETTINGS.messageTemplates,
      ...(source.messageTemplates || {}),
      items: normalizeMessageTemplates(source.messageTemplates?.items),
    },
  }
}

export async function getCommunicationsSettings(): Promise<CommunicationsWorkspaceSettings> {
  const { data } = await api.get('/settings/communications')
  return normalizeCommunicationsSettings(data as Partial<CommunicationsWorkspaceSettings>)
}

export async function patchCommunicationsSettings(
  payload: CommunicationsSettingsPatch
): Promise<CommunicationsWorkspaceSettings> {
  const { data } = await api.patch('/settings/communications', payload)
  return normalizeCommunicationsSettings(data as Partial<CommunicationsWorkspaceSettings>)
}

export async function listCommunicationMessageTemplates(
  opts?: { target?: 'messages' | 'email' }
): Promise<{ items: CommunicationMessageTemplate[]; total: number }> {
  const params: Record<string, any> = {}
  if (opts?.target) params.target = opts.target
  const { data } = await api.get('/communications/message-templates', { params })
  const rawItems = Array.isArray((data as any)?.items) ? (data as any).items : []
  const items = normalizeMessageTemplates(rawItems)
  return { items, total: Number((data as any)?.total || items.length) }
}

export async function listCommunicationThreads(opts?: {
  limit?: number
  offset?: number
  channel?: string
  status?: string[]
  assigneeId?: string
  entityType?: string
  entityId?: string
  includeArchived?: boolean
  q?: string
  signal?: AbortSignal
}): Promise<CommunicationThreadListResponse> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.channel) params.channel = opts.channel
  if (opts?.status && opts.status.length) params.status_filter = opts.status
  if (opts?.assigneeId) params.assignee_id = opts.assigneeId
  if (opts?.entityType) params.entity_type = opts.entityType
  if (opts?.entityId) params.entity_id = opts.entityId
  if (opts?.includeArchived) params.include_archived = true
  if (opts?.q) params.q = opts.q
  const { data } = await api.get('/communications/threads', { params, signal: opts?.signal })
  return data as CommunicationThreadListResponse
}

export async function getCommunicationThread(
  threadId: string,
  opts?: { messagesLimit?: number }
): Promise<CommunicationThreadDetailResponse> {
  const params: Record<string, any> = {}
  if (opts?.messagesLimit != null) params.messages_limit = opts.messagesLimit
  const { data } = await api.get(`/communications/threads/${threadId}`, { params })
  return data as CommunicationThreadDetailResponse
}

export async function createCommunicationThread(payload: Record<string, any>): Promise<CommunicationThread> {
  const { data } = await api.post('/communications/threads', payload)
  return data as CommunicationThread
}

export async function patchCommunicationThread(threadId: string, payload: Record<string, any>): Promise<CommunicationThread> {
  const { data } = await api.patch(`/communications/threads/${threadId}`, payload)
  return data as CommunicationThread
}

export async function listCommunicationMessages(
  threadId: string,
  opts?: { limit?: number; offset?: number }
): Promise<CommunicationMessageListResponse> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  const { data } = await api.get(`/communications/threads/${threadId}/messages`, { params })
  return data as CommunicationMessageListResponse
}

export async function createCommunicationMessage(
  threadId: string,
  payload: Record<string, any>
): Promise<CommunicationMessage> {
  const { data } = await api.post(`/communications/threads/${threadId}/messages`, payload)
  return data as CommunicationMessage
}

export type CommunicationMessageAttachmentUpload = {
  kind: string
  filename: string
  mime?: string | null
  size: number
  storage_path: string
}

export async function uploadCommunicationThreadMessageAttachment(
  threadId: string,
  file: File
): Promise<CommunicationMessageAttachmentUpload> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post(`/communications/threads/${threadId}/message-attachments/upload`, fd)
  return data as CommunicationMessageAttachmentUpload
}

export async function markCommunicationThreadRead(
  threadId: string,
  payload?: { message_ids?: string[]; mark_thread?: boolean }
): Promise<CommunicationThread> {
  const { data } = await api.post(`/communications/threads/${threadId}/read`, payload || { mark_thread: true })
  return data as CommunicationThread
}

export async function reconcileCommunicationThreadUnread(payload?: {
  channel?: string
  includeArchived?: boolean
  limit?: number
}): Promise<{ processed: number; updated: number; total_unread: number }> {
  const body: Record<string, any> = {}
  if (payload?.channel) body.channel = payload.channel
  if (payload?.includeArchived) body.include_archived = true
  if (payload?.limit != null) body.limit = payload.limit
  const { data } = await api.post('/communications/threads/reconcile-unread', body)
  return data as { processed: number; updated: number; total_unread: number }
}

export async function autoAssignCommunicationThread(
  threadId: string
): Promise<{ assigned: boolean; thread: CommunicationThread; reason?: string | null; strategy?: string | null; assignee_id?: string | null; candidates?: Array<Record<string, any>> }> {
  const { data } = await api.post(`/communications/threads/${threadId}/assign-auto`)
  return data as { assigned: boolean; thread: CommunicationThread; reason?: string | null; strategy?: string | null; assignee_id?: string | null; candidates?: Array<Record<string, any>> }
}

export async function listCommunicationAccounts(opts?: { channel?: string }): Promise<{ items: CommunicationChannelAccount[] }> {
  const params: Record<string, any> = {}
  if (opts?.channel) params.channel = opts.channel
  const { data } = await api.get('/communications/accounts', { params })
  return data as { items: CommunicationChannelAccount[] }
}

export async function createCommunicationAccount(payload: Record<string, any>): Promise<CommunicationChannelAccount> {
  const { data } = await api.post('/communications/accounts', payload)
  return data as CommunicationChannelAccount
}

export async function patchCommunicationAccount(
  accountId: string,
  payload: Partial<{
    account_label: string
    external_account_ref: string | null
    inbox_address: string | null
    is_active: boolean
    settings_json: Record<string, any>
    oauth_client_secret: string
  }>
): Promise<CommunicationChannelAccount> {
  const { data } = await api.patch(`/communications/accounts/${accountId}`, payload)
  return data as CommunicationChannelAccount
}

export async function deleteCommunicationAccount(accountId: string): Promise<void> {
  await api.delete(`/communications/accounts/${accountId}`)
}

export async function testCommunicationAccountConnection(accountId: string): Promise<{
  ok: boolean
  action: string
  status: string
  detail?: string | null
  account: CommunicationChannelAccount
}> {
  const { data } = await api.post(`/communications/accounts/${accountId}/test-connection`)
  return data as {
    ok: boolean
    action: string
    status: string
    detail?: string | null
    account: CommunicationChannelAccount
  }
}

export async function syncCommunicationAccountNow(accountId: string): Promise<{
  ok: boolean
  action: string
  status: string
  detail?: string | null
  account: CommunicationChannelAccount
}> {
  const { data } = await api.post(`/communications/accounts/${accountId}/sync-now`)
  return data as {
    ok: boolean
    action: string
    status: string
    detail?: string | null
    account: CommunicationChannelAccount
  }
}

export async function setTelegramAccountWebhook(accountId: string): Promise<{
  ok: boolean
  action: string
  status: string
  detail?: string | null
  account: CommunicationChannelAccount
}> {
  const { data } = await api.post(`/communications/accounts/${accountId}/telegram/webhook/set`)
  return data as {
    ok: boolean
    action: string
    status: string
    detail?: string | null
    account: CommunicationChannelAccount
  }
}

export async function deleteTelegramAccountWebhook(accountId: string): Promise<{
  ok: boolean
  action: string
  status: string
  detail?: string | null
  account: CommunicationChannelAccount
}> {
  const { data } = await api.post(`/communications/accounts/${accountId}/telegram/webhook/delete`)
  return data as {
    ok: boolean
    action: string
    status: string
    detail?: string | null
    account: CommunicationChannelAccount
  }
}

export async function startCommunicationAccountOAuth(
  accountId: string,
  payload?: {
    redirect_uri?: string
    client_id?: string
    scopes?: string[]
    force_consent?: boolean
  }
): Promise<CommunicationAccountOAuthStartResponse> {
  const { data } = await api.post(`/communications/accounts/${accountId}/oauth/start`, payload || {})
  return data as CommunicationAccountOAuthStartResponse
}

export async function completeCommunicationAccountOAuth(
  accountId: string,
  payload: {
    state: string
    code?: string
    redirect_uri?: string
    client_id?: string
    access_token?: string
    refresh_token?: string
    token_type?: string
    expires_in?: number
    scope?: string
    id_token?: string
    provider_payload?: Record<string, any>
    simulate_exchange?: boolean
    code_verifier?: string
  }
): Promise<CommunicationAccountOAuthCompleteResponse> {
  const { data } = await api.post(`/communications/accounts/${accountId}/oauth/complete`, payload)
  return data as CommunicationAccountOAuthCompleteResponse
}

export async function refreshCommunicationAccountOAuth(
  accountId: string,
  payload?: {
    expires_in?: number
    simulate_refresh?: boolean
    provider_payload?: Record<string, any>
  }
): Promise<CommunicationAccountOAuthCompleteResponse> {
  const { data } = await api.post(`/communications/accounts/${accountId}/oauth/refresh`, payload || {})
  return data as CommunicationAccountOAuthCompleteResponse
}

export async function getCommunicationAccountSyncCursor(
  accountId: string,
  cursorKey: string
): Promise<CommunicationAccountSyncCursor> {
  const { data } = await api.get(`/communications/accounts/${accountId}/sync-cursor`, {
    params: { cursor_key: cursorKey },
  })
  return data as CommunicationAccountSyncCursor
}

export async function patchCommunicationAccountSyncCursor(
  accountId: string,
  payload: {
    cursor_key: string
    cursor_value?: string | null
    meta?: Record<string, any>
  }
): Promise<CommunicationAccountSyncCursor> {
  const { data } = await api.patch(`/communications/accounts/${accountId}/sync-cursor`, payload)
  return data as CommunicationAccountSyncCursor
}

export async function previewCommunicationAllocation(payload: {
  channel: string
  at?: string
  entity_type?: string
  entity_id?: string
}): Promise<{
  assigned: boolean
  reason?: string | null
  strategy?: string | null
  assignee_id?: string | null
  evaluated_at?: string | null
  candidates: Array<Record<string, any>>
}> {
  const { data } = await api.post('/communications/allocator/preview', payload)
  return data as {
    assigned: boolean
    reason?: string | null
    strategy?: string | null
    assignee_id?: string | null
    evaluated_at?: string | null
    candidates: Array<Record<string, any>>
  }
}

export async function ingestInboundEmail(payload: {
  channel_account_id?: string
  provider?: string
  provider_thread_ref?: string
  external_message_ref?: string
  subject?: string
  from_address?: string
  from_name?: string
  to_address?: string
  to_name?: string
  cc?: string[]
  bcc?: string[]
  text?: string
  html?: string
  received_at?: string
  headers?: Record<string, any>
  payload?: Record<string, any>
  entity_type?: string
  entity_id?: string
  linked_candidate_id?: string
  linked_company_id?: string
  assignee_id?: string
  auto_assign?: boolean
}): Promise<{
  created_thread: boolean
  duplicate_message: boolean
  auto_assigned: boolean
  auto_assign_reason?: string | null
  thread: CommunicationThread
  message: CommunicationMessage
}> {
  const { data } = await api.post('/communications/ingest/email', payload)
  return data as {
    created_thread: boolean
    duplicate_message: boolean
    auto_assigned: boolean
    auto_assign_reason?: string | null
    thread: CommunicationThread
    message: CommunicationMessage
  }
}

export async function ingestInboundChannel(
  channel: string,
  payload: {
    channel_account_id?: string
    provider?: string
    provider_thread_ref?: string
    provider_chat_ref?: string
    external_message_ref?: string
    sender_address?: string
    sender_label?: string
    recipient_address?: string
    recipient_label?: string
    subject?: string
    text?: string
    html?: string
    received_at?: string
    attachments?: Array<Record<string, any>>
    payload?: Record<string, any>
    headers?: Record<string, any>
    entity_type?: string
    entity_id?: string
    linked_candidate_id?: string
    linked_company_id?: string
    assignee_id?: string
    auto_assign?: boolean
  }
): Promise<{
  created_thread: boolean
  duplicate_message: boolean
  auto_assigned: boolean
  auto_assign_reason?: string | null
  thread: CommunicationThread
  message: CommunicationMessage
}> {
  const { data } = await api.post(`/communications/ingest/${encodeURIComponent(channel)}`, payload)
  return data as {
    created_thread: boolean
    duplicate_message: boolean
    auto_assigned: boolean
    auto_assign_reason?: string | null
    thread: CommunicationThread
    message: CommunicationMessage
  }
}

export async function simulateTelegramWebhook(payload: {
  channel_account_id: string
  update: Record<string, any>
  auto_assign?: boolean
  entity_type?: string
  entity_id?: string
  linked_candidate_id?: string
  linked_company_id?: string
}): Promise<{
  created_thread: boolean
  duplicate_message: boolean
  auto_assigned: boolean
  auto_assign_reason?: string | null
  thread: CommunicationThread
  message: CommunicationMessage
}> {
  const { data } = await api.post('/communications/telegram/webhook-simulate', payload)
  return data as {
    created_thread: boolean
    duplicate_message: boolean
    auto_assigned: boolean
    auto_assign_reason?: string | null
    thread: CommunicationThread
    message: CommunicationMessage
  }
}

export async function dispatchCommunicationMessage(
  messageId: string,
  payload?: {
    mark_delivered?: boolean
    simulate_failure?: boolean
    provider_message_ref?: string
    provider_payload?: Record<string, any>
  }
): Promise<CommunicationDispatchResponse> {
  const { data } = await api.post(`/communications/messages/${messageId}/dispatch`, payload || {})
  return data as CommunicationDispatchResponse
}

export async function dispatchQueuedCommunicationMessages(payload?: {
  limit?: number
  channel?: string
  only_email?: boolean
  mark_delivered?: boolean
  simulate_failure?: boolean
}): Promise<{
  processed: number
  dispatched: number
  failed: number
  items: CommunicationDispatchResponse[]
}> {
  const { data } = await api.post('/communications/dispatch/queued', payload || {})
  return data as {
    processed: number
    dispatched: number
    failed: number
    items: CommunicationDispatchResponse[]
  }
}

export async function patchCommunicationMessageDeliveryStatus(
  messageId: string,
  payload: {
    delivery_status: string
    error_message?: string | null
    external_message_ref?: string
    provider_payload?: Record<string, any>
    delivered_at?: string
    read_at?: string
  }
): Promise<CommunicationMessage> {
  const { data } = await api.patch(`/communications/messages/${messageId}/delivery-status`, payload)
  return data as CommunicationMessage
}

export async function runCommunicationEmailDispatchWorker(payload?: {
  limit?: number
  mark_delivered?: boolean
}): Promise<{
  processed: number
  dispatched: number
  failed: number
  items: CommunicationDispatchResponse[]
}> {
  const { data } = await api.post('/communications/email/worker/dispatch', payload || {})
  return data as {
    processed: number
    dispatched: number
    failed: number
    items: CommunicationDispatchResponse[]
  }
}

export async function runCommunicationEmailPollWorker(payload?: {
  only_account_id?: string
  limit_per_account?: number
}): Promise<{
  polled_accounts: number
  supported_accounts: number
  ingested_messages: number
  created_threads: number
  skipped_messages: number
  unsupported_accounts: number
  items: Array<Record<string, any>>
}> {
  const { data } = await api.post('/communications/email/worker/poll', payload || {})
  return data as {
    polled_accounts: number
    supported_accounts: number
    ingested_messages: number
    created_threads: number
    skipped_messages: number
    unsupported_accounts: number
    items: Array<Record<string, any>>
  }
}

export async function listCommunicationTimeOffRequests(opts?: {
  limit?: number
  offset?: number
  mine_only?: boolean
  status_filter?: string[]
  requester_user_id?: string
  approver_user_id?: string
}): Promise<{ items: CommunicationTimeOffRequest[]; total: number }> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.mine_only) params.mine_only = true
  if (opts?.status_filter?.length) params.status_filter = opts.status_filter
  if (opts?.requester_user_id) params.requester_user_id = opts.requester_user_id
  if (opts?.approver_user_id) params.approver_user_id = opts.approver_user_id
  const { data } = await api.get('/communications/time-off/requests', { params })
  return data as { items: CommunicationTimeOffRequest[]; total: number }
}

export async function createCommunicationTimeOffRequest(payload: {
  request_type: string
  start_date: string
  end_date: string
  partial_day?: string
  reason?: string
  approver_user_id?: string
  approver_label?: string
  payload?: Record<string, any>
}): Promise<CommunicationTimeOffRequest> {
  const { data } = await api.post('/communications/time-off/requests', payload)
  return data as CommunicationTimeOffRequest
}

export async function cancelCommunicationTimeOffRequest(requestId: string, payload?: { reason?: string }): Promise<CommunicationTimeOffRequest> {
  const { data } = await api.post(`/communications/time-off/requests/${requestId}/cancel`, payload || {})
  return data as CommunicationTimeOffRequest
}

export async function decideCommunicationTimeOffRequest(
  requestId: string,
  payload: { decision: 'approved' | 'rejected'; decision_note?: string }
): Promise<CommunicationTimeOffRequest> {
  const { data } = await api.post(`/communications/time-off/requests/${requestId}/decision`, payload)
  return data as CommunicationTimeOffRequest
}

export async function getMyWorkingHours(): Promise<WorkingHoursSchedule> {
  const { data } = await api.get('/communications/availability/working-hours')
  return data as WorkingHoursSchedule
}

export async function upsertMyWorkingHours(payload: WorkingHoursSchedule): Promise<WorkingHoursSchedule> {
  const { data } = await api.put('/communications/availability/working-hours', payload)
  return data as WorkingHoursSchedule
}

export async function listCommunicationAllocatorAudit(opts?: {
  limit?: number
  offset?: number
  mode?: string
  channel?: string
  thread_id?: string
  assignee_id?: string
}): Promise<{ items: CommunicationAllocationAudit[]; total: number }> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.mode) params.mode = opts.mode
  if (opts?.channel) params.channel = opts.channel
  if (opts?.thread_id) params.thread_id = opts.thread_id
  if (opts?.assignee_id) params.assignee_id = opts.assignee_id
  const { data } = await api.get('/communications/allocator/audit', { params })
  return data as { items: CommunicationAllocationAudit[]; total: number }
}

export async function createCommunicationCommandAuditBatch(payload: {
  channel: string
  thread_ids: string[]
  command_id: string
  command_label?: string
  actions_json?: Array<Record<string, any>>
  payload?: Record<string, any>
  executed_at?: string
}): Promise<{ created: number; items: CommunicationCommandAudit[] }> {
  const { data } = await api.post('/communications/commands/audit/batch', payload)
  return data as { created: number; items: CommunicationCommandAudit[] }
}

export async function listCommunicationCommandAudit(opts?: {
  limit?: number
  offset?: number
  channel?: string
  thread_id?: string
  command_id?: string
  actor_user_id?: string
}): Promise<{ items: CommunicationCommandAudit[]; total: number }> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.channel) params.channel = opts.channel
  if (opts?.thread_id) params.thread_id = opts.thread_id
  if (opts?.command_id) params.command_id = opts.command_id
  if (opts?.actor_user_id) params.actor_user_id = opts.actor_user_id
  const { data } = await api.get('/communications/commands/audit', { params })
  return data as { items: CommunicationCommandAudit[]; total: number }
}

export async function getCommunicationSchedulerStatus(): Promise<CommunicationSchedulerStatus> {
  const { data } = await api.get('/communications/scheduler/status')
  return data as CommunicationSchedulerStatus
}

export async function runCommunicationSchedulerNow(): Promise<{ ok: boolean; status: CommunicationSchedulerStatus }> {
  const { data } = await api.post('/communications/scheduler/run-now', {})
  return data as { ok: boolean; status: CommunicationSchedulerStatus }
}

export async function listCommunicationPlannerEvents(opts?: {
  limit?: number
  offset?: number
  status_filter?: string[]
  assignee_id?: string
  from_at?: string
  to_at?: string
  kind?: string
}): Promise<{ items: CommunicationPlannerEvent[]; total: number }> {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = Math.min(200, Math.max(1, opts.limit))
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.status_filter?.length) params.status_filter = opts.status_filter
  if (opts?.assignee_id) params.assignee_id = opts.assignee_id
  if (opts?.from_at) params.from_at = opts.from_at
  if (opts?.to_at) params.to_at = opts.to_at
  if (opts?.kind) params.kind = opts.kind
  const { data } = await api.get('/communications/planner/events', { params })
  return data as { items: CommunicationPlannerEvent[]; total: number }
}

export async function createCommunicationPlannerEvent(payload: {
  title: string
  description?: string
  kind?: string
  status?: string
  priority?: string
  start_at: string
  end_at?: string
  all_day?: boolean
  assignee_id?: string
  entity_type?: string
  entity_id?: string
  linked_candidate_id?: string
  linked_company_id?: string
  source?: string
  payload?: Record<string, any>
}): Promise<CommunicationPlannerEvent> {
  const { data } = await api.post('/communications/planner/events', payload)
  return data as CommunicationPlannerEvent
}

export async function patchCommunicationPlannerEvent(
  eventId: string,
  payload: Partial<{
    title: string
    description: string | null
    kind: string
    status: string
    priority: string
    start_at: string
    end_at: string | null
    all_day: boolean
    assignee_id: string | null
    entity_type: string | null
    entity_id: string | null
    linked_candidate_id: string | null
    linked_company_id: string | null
    payload: Record<string, any>
  }>
): Promise<CommunicationPlannerEvent> {
  const { data } = await api.patch(`/communications/planner/events/${eventId}`, payload)
  return data as CommunicationPlannerEvent
}
