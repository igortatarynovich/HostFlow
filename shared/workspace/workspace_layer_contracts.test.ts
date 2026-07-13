/**
 * Platform contract tests — node:test only (no vitest dependency in shared/).
 */
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  RECRUITMENT_REQUIREMENTS_SECTION,
  registerRecruitmentWorkspaceSectionsP0,
  type WorkspaceSession,
} from './workspace_layer_contracts.ts'
import { createSectionRegistry } from './section_registry.ts'
import {
  aggregateWorkspaceStatusForSession,
  createReadinessRegistryWithCollect,
} from './workspace_status_aggregation.ts'

const baseSession: WorkspaceSession = {
  context: 'recruitment',
  anchor: {
    anchor_kind: 'candidate',
    anchor_id: 'cand-1',
    tenant_id: 'tenant-1',
  },
  enabled_modules: ['recruitment'],
}

describe('section registry', () => {
  it('lists recruitment requirements for recruitment context', () => {
    const registry = createSectionRegistry()
    registerRecruitmentWorkspaceSectionsP0(registry)

    const sections = registry.listSections(baseSession, ['candidates.view'])
    assert.equal(sections.length, 1)
    assert.equal(sections[0].section_id, 'requirements')
    assert.equal(sections[0].capability_key, 'recruitment.requirements')
  })

  it('hides section when module disabled', () => {
    const registry = createSectionRegistry()
    registerRecruitmentWorkspaceSectionsP0(registry)

    const sections = registry.listSections(
      { ...baseSession, enabled_modules: [] },
      ['candidates.view'],
    )
    assert.equal(sections.length, 0)
  })

  it('hides section when permission missing', () => {
    const registry = createSectionRegistry()
    registry.register(RECRUITMENT_REQUIREMENTS_SECTION)

    const sections = registry.listSections(baseSession, [])
    assert.equal(sections.length, 0)
  })

  it('hides section for wrong context', () => {
    const registry = createSectionRegistry()
    registerRecruitmentWorkspaceSectionsP0(registry)

    const sections = registry.listSections(
      { ...baseSession, context: 'intake' },
      ['candidates.view'],
    )
    assert.equal(sections.length, 0)
  })
})

describe('workspace status aggregation', () => {
  it('picks lowest-priority next action with permission', async () => {
    const registry = createReadinessRegistryWithCollect()
    registry.registerContributor('recruitment', async () => ({
      module_key: 'recruitment',
      context: 'recruitment',
      priority: 10,
      severity: 'blocked',
      summary_key: 'workspace.recruitment.readiness.summary',
      next_action: {
        action_id: 'upload_passport',
        module_key: 'recruitment',
        label_key: 'workspace.recruitment.actions.upload_passport',
        permission: 'candidates.manage',
        priority: 20,
        handler_kind: 'navigation',
        handler_ref: '/app/candidates/cand-1/requirements',
      },
    }))

    const snapshot = await aggregateWorkspaceStatusForSession(
      baseSession,
      registry,
      ['candidates.view', 'candidates.manage'],
    )

    assert.equal(snapshot.displayed_next_action?.action_id, 'upload_passport')
    assert.equal(snapshot.aggregated_severity, 'blocked')
  })

  it('does not display next action without permission', async () => {
    const registry = createReadinessRegistryWithCollect()
    registry.registerContributor('recruitment', async () => ({
      module_key: 'recruitment',
      context: 'recruitment',
      priority: 10,
      severity: 'warning',
      summary_key: 'workspace.recruitment.readiness.summary',
      next_action: {
        action_id: 'upload_passport',
        module_key: 'recruitment',
        label_key: 'workspace.recruitment.actions.upload_passport',
        permission: 'candidates.manage',
        priority: 10,
        handler_kind: 'api',
        handler_ref: 'POST /api/v1/candidates/cand-1/requirements',
      },
    }))

    const snapshot = await aggregateWorkspaceStatusForSession(
      baseSession,
      registry,
      ['candidates.view'],
    )

    assert.equal(snapshot.displayed_next_action, null)
  })
})
