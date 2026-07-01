import { describe, expect, it } from 'vitest'
import {
  buildRecruitmentBlockConfirmFingerprint,
  pruneConfirmedRecruitmentBlocks,
  readConfirmedRecruitmentBlocks,
  readRecruitmentConfirmFingerprints,
  recruitmentBlocksPendingConfirm,
  recruitmentPackageHandoffReady,
} from '../recruitmentDossierConfirm'

describe('recruitmentDossierConfirm', () => {
  it('reads confirmed blocks from extra', () => {
    expect(
      readConfirmedRecruitmentBlocks({ recruitment_dossier_confirmed_blocks: ['Passport / ID', ''] }),
    ).toEqual(['Passport / ID'])
  })

  it('reads confirm fingerprints from extra', () => {
    expect(
      readRecruitmentConfirmFingerprints({
        recruitment_dossier_confirm_fingerprints: { 'Passport / ID': 'ready|passport:abc:approved' },
      }),
    ).toEqual({ 'Passport / ID': 'ready|passport:abc:approved' })
  })

  it('prunes confirmations when block is no longer ready', () => {
    const pruned = pruneConfirmedRecruitmentBlocks(
      ['Passport / ID', 'Contacts & address'],
      [
        { key: 'Passport / ID', status: 'data' },
        { key: 'Contacts & address', status: 'ready', fingerprint: 'ready||' },
      ],
      { 'Contacts & address': 'ready||' },
    )
    expect(pruned).toEqual(['Contacts & address'])
  })

  it('prunes confirmations when document fingerprint changed', () => {
    const pruned = pruneConfirmedRecruitmentBlocks(
      ['Passport / ID'],
      [{ key: 'Passport / ID', status: 'ready', fingerprint: 'ready|passport:new-id:approved' }],
      { 'Passport / ID': 'ready|passport:old-id:approved' },
    )
    expect(pruned).toEqual([])
  })

  it('builds fingerprint from runtime document ids', () => {
    const fp = buildRecruitmentBlockConfirmFingerprint({
      blockKey: 'Passport / ID',
      status: 'ready',
      runtimeByType: new Map([
        ['passport', { document_id: 'doc-1', workflow_status: 'approved', satisfies_requirement: true }],
      ]),
    })
    expect(fp).toContain('passport:doc-1:approved')
  })

  it('requires pkg.ready and zero pending confirms for handoff', () => {
    expect(recruitmentPackageHandoffReady({ pkgReady: true, pendingConfirmCount: 0 })).toBe(true)
    expect(recruitmentPackageHandoffReady({ pkgReady: false, pendingConfirmCount: 0 })).toBe(false)
    expect(recruitmentPackageHandoffReady({ pkgReady: true, pendingConfirmCount: 1 })).toBe(false)
    expect(recruitmentPackageHandoffReady({ pkgReady: undefined, pendingConfirmCount: 0 })).toBe(false)
  })

  it('lists ready blocks still awaiting confirm', () => {
    const pending = recruitmentBlocksPendingConfirm(
      [
        { key: 'A', status: 'ready' },
        { key: 'B', status: 'missing' },
      ],
      new Set(['A']),
    )
    expect(pending).toEqual([])
    expect(
      recruitmentBlocksPendingConfirm(
        [
          { key: 'A', status: 'ready' },
          { key: 'C', status: 'ready' },
        ],
        new Set(['A']),
      ),
    ).toEqual(['C'])
  })
})
