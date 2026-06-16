import { describe, expect, it } from 'vitest'
import {
  pruneConfirmedRecruitmentBlocks,
  readConfirmedRecruitmentBlocks,
  recruitmentBlocksPendingConfirm,
  recruitmentPackageHandoffReady,
} from './recruitmentDossierConfirm'

describe('recruitmentDossierConfirm', () => {
  it('reads confirmed blocks from extra', () => {
    expect(
      readConfirmedRecruitmentBlocks({ recruitment_dossier_confirmed_blocks: ['Passport / ID', ''] }),
    ).toEqual(['Passport / ID'])
  })

  it('prunes confirmations when block is no longer ready', () => {
    const pruned = pruneConfirmedRecruitmentBlocks(
      ['Passport / ID', 'Contacts & address'],
      [
        { key: 'Passport / ID', status: 'data' },
        { key: 'Contacts & address', status: 'ready' },
      ],
    )
    expect(pruned).toEqual(['Contacts & address'])
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
