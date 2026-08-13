/**
 * Work Hub role profiles — per-role configuration for `/app/work`.
 *
 * Closes G-6 from `docs/specs/operations-loop.md`. The hub used to render
 * the same layout for everyone; recruiters got handoff/team noise they
 * couldn't act on, supervisors got recruiter-level CTAs, client_manager
 * had no surface for incoming handoffs at all.
 *
 * The profile is *pure data* — it tells the page which sections to render,
 * in what order, with which copy. It does NOT fetch anything; data sources
 * stay shared across roles so we don't fan out the cache or the loading
 * spinners.
 */

import {
  isHrWorkspaceActor,
  isPortalActor,
  isTeamLeadOrgActor,
  normalizeTrustRole,
  resolvePermissionPersona,
  type AccessContext,
  type PermissionPresetId,
} from '../../auth/trustRoles'

export type WorkHubRoleKey =
  | 'admin_solo'
  | 'admin_team'
  | 'supervisor'
  | 'recruiter'
  | 'client_manager'
  | 'client_processor'
  | 'viewer'

/**
 * Catalogue of orderable sections. The page knows how to render each;
 * profile.sections decides order and which ones to skip.
 */
export type WorkHubSection =
  | 'hero'
  | 'critical'
  | 'myTasks'
  | 'todayPlanner'
  | 'riskDigest'
  | 'managerLoad'
  | 'bottlenecks'
  | 'handoffQueue'
  | 'quickActions'
  | 'viewerSummary'

/** What the hero card says when the user has nothing to act on. */
export type WorkHubHeroVariant =
  /** "Everything under control" — recruiter / processor friendly. */
  | 'calm_personal'
  /** "Team is on track" — supervisor / admin team. */
  | 'calm_team'
  /** "Inbox quiet — review pipeline?" — client manager. */
  | 'calm_client'
  /** "Welcome back — set up first task" — admin-solo. */
  | 'calm_solo'
  /** Read-only summary, no CTA. */
  | 'viewer'

export type WorkHubProfile = {
  key: WorkHubRoleKey
  /** i18n key for the role label shown in the strip and page sub-header. */
  labelKey: string
  labelDefault: string
  /** Short sentence that frames the hub for this role. */
  lensKey: string
  lensDefault: string
  /** Order matters — first section in this list renders first under the strip. */
  sections: WorkHubSection[]
  hero: {
    variant: WorkHubHeroVariant
    /** Headline shown in the hero when there IS something to act on. */
    needHeadlineKey: string
    needHeadlineDefault: string
  }
  /**
   * Default scope of operational counters for this role.
   * `mine` → assignee-scoped counts (recruiter, processor).
   * `team` → tenant-wide counts (supervisor, admin team, client_manager).
   * Admin-solo sees `mine` because there is no team.
   */
  defaultCounterScope: 'mine' | 'team'
  /**
   * Whether the page should surface the secondary "Bottlenecks" block.
   * Some roles (client_manager, viewer) don't act on agency-side bottlenecks.
   */
  showBottlenecks: boolean
  /** Whether the handoff queue panel should be rendered at all. */
  showHandoffQueue: boolean
}

const PROFILES: Record<WorkHubRoleKey, WorkHubProfile> = {
  admin_solo: {
    key: 'admin_solo',
    labelKey: 'app.work.profile.admin_solo.label',
    labelDefault: 'Owner (solo)',
    lensKey: 'app.work.profile.admin_solo.lens',
    lensDefault: 'You are the only operator — this view shows the whole pipeline at a glance.',
    sections: ['hero', 'critical', 'myTasks', 'todayPlanner', 'bottlenecks', 'quickActions'],
    hero: {
      variant: 'calm_solo',
      needHeadlineKey: 'app.work.hub.hero_need_action_title',
      needHeadlineDefault: 'Candidates need action',
    },
    defaultCounterScope: 'mine',
    showBottlenecks: true,
    showHandoffQueue: false,
  },
  admin_team: {
    key: 'admin_team',
    labelKey: 'app.work.profile.admin_team.label',
    labelDefault: 'Owner / Admin',
    lensKey: 'app.work.profile.admin_team.lens',
    lensDefault: 'Workspace-wide overview — block & unblock the team.',
    // G-6 Stage 2c — `managerLoad` renders after the personal panels so
    // the team-distribution view sits between personal focus and the
    // bottlenecks list; keeps the "mine first, team second" rhythm.
    sections: ['hero', 'critical', 'handoffQueue', 'myTasks', 'todayPlanner', 'riskDigest', 'managerLoad', 'bottlenecks', 'quickActions'],
    hero: {
      variant: 'calm_team',
      needHeadlineKey: 'app.work.profile.admin_team.hero_need',
      needHeadlineDefault: 'Items waiting on the team',
    },
    defaultCounterScope: 'team',
    showBottlenecks: true,
    showHandoffQueue: true,
  },
  supervisor: {
    key: 'supervisor',
    labelKey: 'app.work.profile.supervisor.label',
    labelDefault: 'Supervisor',
    lensKey: 'app.work.profile.supervisor.lens',
    lensDefault: 'Where work is stuck and who you can unblock.',
    sections: ['hero', 'critical', 'handoffQueue', 'myTasks', 'todayPlanner', 'riskDigest', 'managerLoad', 'bottlenecks', 'quickActions'],
    hero: {
      variant: 'calm_team',
      needHeadlineKey: 'app.work.profile.supervisor.hero_need',
      needHeadlineDefault: 'Items waiting on the team',
    },
    defaultCounterScope: 'team',
    showBottlenecks: true,
    showHandoffQueue: true,
  },
  recruiter: {
    key: 'recruiter',
    labelKey: 'app.work.profile.recruiter.label',
    labelDefault: 'Recruiter',
    lensKey: 'app.work.profile.recruiter.lens',
    lensDefault: 'Your candidates and your tasks for today.',
    // Recruiter is the personal-focus profile — "my tasks" goes right after
    // the hero so the page's answer to "what do I do next?" is visible
    // before scroll. Team-scope stuck items (critical) come after.
    sections: ['hero', 'myTasks', 'todayPlanner', 'critical', 'bottlenecks', 'quickActions'],
    hero: {
      variant: 'calm_personal',
      needHeadlineKey: 'app.work.hub.hero_need_action_title',
      needHeadlineDefault: 'Candidates need action',
    },
    defaultCounterScope: 'mine',
    showBottlenecks: true,
    showHandoffQueue: false,
  },
  client_manager: {
    key: 'client_manager',
    labelKey: 'app.work.profile.client_manager.label',
    labelDefault: 'Client manager',
    lensKey: 'app.work.profile.client_manager.lens',
    lensDefault: 'Candidates handed over to you that need a decision.',
    // Handoff queue is THE thing this role acts on — surface it before generic critical.
    sections: ['handoffQueue', 'hero', 'myTasks', 'todayPlanner', 'critical', 'quickActions'],
    hero: {
      variant: 'calm_client',
      needHeadlineKey: 'app.work.profile.client_manager.hero_need',
      needHeadlineDefault: 'Candidates waiting for your decision',
    },
    defaultCounterScope: 'team',
    showBottlenecks: false,
    showHandoffQueue: true,
  },
  client_processor: {
    key: 'client_processor',
    labelKey: 'app.work.profile.client_processor.label',
    labelDefault: 'Client processor',
    lensKey: 'app.work.profile.client_processor.lens',
    lensDefault: 'Your assigned candidates and onboarding tasks.',
    sections: ['handoffQueue', 'hero', 'myTasks', 'todayPlanner', 'critical', 'quickActions'],
    hero: {
      variant: 'calm_personal',
      needHeadlineKey: 'app.work.hub.hero_need_action_title',
      needHeadlineDefault: 'Candidates need action',
    },
    defaultCounterScope: 'mine',
    showBottlenecks: false,
    showHandoffQueue: true,
  },
  viewer: {
    key: 'viewer',
    labelKey: 'app.work.profile.viewer.label',
    labelDefault: 'Read-only viewer',
    lensKey: 'app.work.profile.viewer.lens',
    lensDefault: 'You can browse the workspace but not act on items here.',
    sections: ['viewerSummary', 'critical'],
    hero: {
      variant: 'viewer',
      needHeadlineKey: 'app.work.profile.viewer.hero_need',
      needHeadlineDefault: 'Recent activity',
    },
    defaultCounterScope: 'team',
    showBottlenecks: false,
    showHandoffQueue: false,
  },
}

/**
 * Resolve the profile for the given normalized role + tenant context.
 *
 * - `administrator` → `admin_solo` when `isSoloAdmin` is true (from
 *   `GET /users/me` → `is_solo_admin`, G-6 Stage 2e); otherwise `admin_team`.
 * - Unknown role strings fall back to `viewer` — never crash, never grant.
 */
export function resolveWorkHubProfile(args: {
  role: string
  isClientTenant: boolean
  isSoloAdmin?: boolean
  accessContext?: AccessContext | string | null
  presetId?: PermissionPresetId | string | null
}): WorkHubProfile {
  const { role, isClientTenant, isSoloAdmin, accessContext, presetId } = args
  const trust = normalizeTrustRole(role)
  const portal = isPortalActor(role, accessContext)

  if (trust === 'administrator' || trust === 'superadmin') {
    return PROFILES[isSoloAdmin ? 'admin_solo' : 'admin_team']
  }
  if (portal || (isClientTenant && trust === 'viewer')) {
    const persona = resolvePermissionPersona({
      role,
      accessContext,
      presetId: presetId as PermissionPresetId | null,
      isClientTenant,
    })
    if (persona === 'client_manager') return PROFILES.client_manager
    return PROFILES.client_processor
  }
  if (isTeamLeadOrgActor(role, presetId)) return PROFILES.supervisor
  if (isHrWorkspaceActor(role, presetId)) return PROFILES.recruiter
  if (trust === 'employee') return PROFILES.recruiter
  if (trust === 'viewer') return PROFILES.viewer

  // Legacy persona bridge for unread job-title JWT strings.
  const persona = resolvePermissionPersona({
    role,
    accessContext,
    presetId: presetId as PermissionPresetId | null,
    isClientTenant,
  })
  if (persona === 'team_lead' || persona === 'supervisor') return PROFILES.supervisor
  if (persona === 'recruiter' || persona === 'employee' || persona === 'compliance_officer' || persona === 'hr' || persona === 'hr_officer') {
    return PROFILES.recruiter
  }
  if (persona === 'client_manager') return PROFILES.client_manager
  if (persona === 'client_processor') return PROFILES.client_processor

  return PROFILES.viewer
}

export const WORK_HUB_PROFILES = PROFILES
