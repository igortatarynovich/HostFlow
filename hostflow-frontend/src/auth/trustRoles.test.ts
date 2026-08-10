import { describe, expect, it } from 'vitest'
import {
  actorSatisfiesRoleAllowlist,
  canUseTeamOverviewLane,
  inferAccessContext,
  inferPresetId,
  isHrWorkspaceActor,
  isPortalActor,
  isRecruitmentAssigneeRole,
  isTeamLeadOrgActor,
  normalizeTrustRole,
  RECRUITMENT_ASSIGNEE_CATALOG_ROLES,
  resolvePermissionPersona,
  resolveActorTrustContext,
} from './trustRoles'

describe('trustRoles ADR-036', () => {
  it('normalizes legacy job/portal strings', () => {
    expect(normalizeTrustRole('recruiter')).toBe('employee')
    expect(normalizeTrustRole('supervisor')).toBe('employee')
    expect(normalizeTrustRole('client_manager')).toBe('viewer')
    expect(normalizeTrustRole('owner')).toBe('administrator')
    expect(normalizeTrustRole('')).toBe('viewer')
  })

  it('infers access_context and presets', () => {
    expect(inferAccessContext('viewer', 'portal')).toBe('portal')
    expect(inferAccessContext('client_processor')).toBe('portal')
    expect(inferAccessContext('recruiter')).toBe('tenant')
    expect(inferPresetId('supervisor')).toBe('team_lead')
    expect(inferPresetId('employee', 'hr')).toBe('hr')
  })

  it('bridges employee on job-proxy allowlists', () => {
    expect(
      actorSatisfiesRoleAllowlist({
        role: 'employee',
        allowed: ['recruiter', 'supervisor'],
      }),
    ).toBe(true)
    expect(
      actorSatisfiesRoleAllowlist({
        role: 'viewer',
        allowed: ['recruiter'],
        accessContext: 'tenant',
      }),
    ).toBe(false)
  })

  it('bridges portal viewer only with portal context', () => {
    expect(
      actorSatisfiesRoleAllowlist({
        role: 'viewer',
        allowed: ['client_manager'],
        accessContext: 'portal',
      }),
    ).toBe(true)
    expect(
      actorSatisfiesRoleAllowlist({
        role: 'viewer',
        allowed: ['client_manager'],
        accessContext: 'tenant',
      }),
    ).toBe(false)
  })

  it('resolves permission personas from trust + preset', () => {
    expect(resolvePermissionPersona({ role: 'employee', presetId: 'team_lead' })).toBe(
      'supervisor',
    )
    expect(resolvePermissionPersona({ role: 'employee', presetId: 'hr' })).toBe('hr_officer')
    expect(resolvePermissionPersona({ role: 'viewer', accessContext: 'portal' })).toBe(
      'client_processor',
    )
    expect(resolvePermissionPersona({ role: 'administrator' })).toBe('administrator')
  })

  it('resolves actor context from preferences', () => {
    const ctx = resolveActorTrustContext({
      role: 'viewer',
      tenant_id: 't1',
      preferences: { access_context: 'portal', preset_id: 'portal_guest' },
    })
    expect(ctx.trustRole).toBe('viewer')
    expect(ctx.accessContext).toBe('portal')
    expect(ctx.presetId).toBe('portal_guest')
    expect(isPortalActor(ctx.rawRole, ctx.accessContext)).toBe(true)
  })

  it('team overview lane helpers', () => {
    expect(canUseTeamOverviewLane({ role: 'administrator' })).toBe(true)
    expect(canUseTeamOverviewLane({ role: 'employee', presetId: 'team_lead' })).toBe(true)
    expect(canUseTeamOverviewLane({ role: 'employee', presetId: 'recruiter' })).toBe(false)
    expect(isTeamLeadOrgActor('supervisor')).toBe(true)
    expect(isHrWorkspaceActor('employee', 'hr')).toBe(true)
  })

  it('recruitment assignee catalog roles', () => {
    expect(isRecruitmentAssigneeRole('employee')).toBe(true)
    expect(isRecruitmentAssigneeRole('recruiter')).toBe(true)
    expect(isRecruitmentAssigneeRole('hr_officer')).toBe(false)
    expect(isRecruitmentAssigneeRole('viewer')).toBe(false)
    expect(RECRUITMENT_ASSIGNEE_CATALOG_ROLES).toContain('employee')
  })
})
