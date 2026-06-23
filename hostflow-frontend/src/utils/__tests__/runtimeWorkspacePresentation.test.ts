import { describe, expect, it } from 'vitest'
import {
  buildRuntimeWorkspaceFromSummary,
  workspaceHasPipelineBlockers,
} from '../runtimeWorkspacePresentation'

describe('runtimeWorkspacePresentation', () => {
  it('builds KPI and pipeline blockers from runtime items', () => {
    const workspace = buildRuntimeWorkspaceFromSummary({
      document_runtime: {
        items: [
          {
            document_type_code: 'passport',
            document_runtime: {
              workflow_status: 'approved',
              expiry_status: 'valid',
              satisfies_requirement: true,
              blockers: [],
              warnings: [],
            },
          },
          {
            document_type_code: 'visa',
            document_runtime: {
              workflow_status: 'missing',
              runtime_signal: 'missing',
              satisfies_requirement: false,
              blockers: [{ code: 'document_missing', message: 'Required document missing: visa' }],
              warnings: [],
            },
          },
          {
            document_type_code: 'driver_license',
            document_runtime: {
              workflow_status: 'uploaded',
              runtime_signal: 'pending_verification',
              satisfies_requirement: false,
              blockers: [],
              warnings: [{ code: 'document_pending_verification', severity: 'warning' }],
            },
          },
        ],
      },
    })

    expect(workspace).not.toBeNull()
    expect(workspace!.totalRequired).toBe(3)
    expect(workspace!.satisfiedCount).toBe(1)
    expect(workspace!.percentReady).toBe(33)
    expect(workspace!.pipelineBlockers.missing).toEqual(['visa'])
    expect(workspace!.pipelineBlockers.inProgress).toEqual(['driver_license'])
    expect(workspace!.readinessKey).toBe('problem')
    expect(workspaceHasPipelineBlockers(workspace!)).toBe(true)
  })

  it('returns ready when all satisfied', () => {
    const workspace = buildRuntimeWorkspaceFromSummary({
      checklist: {
        runtimeItems: [
          {
            document_type_code: 'passport',
            document_runtime: {
              workflow_status: 'approved',
              satisfies_requirement: true,
              blockers: [],
              warnings: [],
            },
          },
        ],
      },
    })
    expect(workspace?.readinessKey).toBe('ready')
    expect(workspace?.percentReady).toBe(100)
  })

  it('returns null when runtime items missing', () => {
    expect(buildRuntimeWorkspaceFromSummary({ percent_ready: 50, required: { missing: ['visa'] } })).toBeNull()
  })
})
