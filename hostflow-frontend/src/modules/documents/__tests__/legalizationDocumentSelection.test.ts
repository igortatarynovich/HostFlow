import { describe, expect, it } from 'vitest'
import { normalizeDocTypeCode } from '../documentUtils'
import {
  contractAsks,
  matchesContract,
  codesKnownToContract,
  stayContractGroups,
  workContractGroups,
} from '../legalizationDocumentSelection'

const temporaryStay = {
  evidence: [
    { codes: ['residence_card', 'residence_permit', 'karta_pobytu'] },
    { codes: ['decision', 'decyzja', 'voivodeship_decision', 'temporary_residence_decision'] },
  ],
  documents: ['residence_card', 'residence_permit', 'karta_pobytu'],
  dependent_documents: ['decision', 'decyzja', 'voivodeship_decision', 'temporary_residence_decision'],
}

describe('legalization document selection', () => {
  it('asks only for the documents of the selected stay basis', () => {
    const groups = stayContractGroups(temporaryStay)
    expect(groups).toHaveLength(2)
    for (const code of ['residence_card', 'karta_pobytu', 'voivodeship_decision', 'temporary_residence_decision']) {
      expect(contractAsks(groups, code)).toBe(true)
    }
    for (const code of ['visa', 'visa_free', 'other', 'additional_document', 'passport']) {
      expect(contractAsks(groups, code)).toBe(false)
    }
  })

  it('does not treat the wojewoda decision as an inbox or other document', () => {
    expect(normalizeDocTypeCode('voivodeship_decision')).toBe('unclassified')
    expect(normalizeDocTypeCode('additional_document')).toBe('unclassified')
    const decision = codesKnownToContract(temporaryStay.dependent_documents)
    expect(matchesContract('voivodeship_decision', decision)).toBe(true)
    expect(matchesContract('decyzja', decision)).toBe(true)
    expect(matchesContract('additional_document', decision)).toBe(false)
    expect(matchesContract('other', decision)).toBe(false)
    expect(matchesContract('unclassified', decision)).toBe(false)
  })

  it('asks only for the selected work procedure', () => {
    const permit = workContractGroups('work_permit', [
      { code: 'work_permit', documents: ['work_permit', 'zezwolenie_a', 'work_permit_a'] },
      { code: 'oswiadczenie', documents: ['oswiadczenie', 'employer_declaration'] },
    ])
    expect(contractAsks(permit, 'work_permit')).toBe(true)
    expect(contractAsks(permit, 'zezwolenie_a')).toBe(true)
    expect(contractAsks(permit, 'other')).toBe(false)
    expect(contractAsks(permit, 'visa')).toBe(false)
    expect(workContractGroups('included_in_stay', [{ code: 'included_in_stay', documents: [] }])).toEqual([])
  })

  it('asks for nothing until a stay basis is selected', () => {
    expect(stayContractGroups(null)).toEqual([])
    expect(stayContractGroups({ evidence: [], documents: [], dependent_documents: [] })).toEqual([])
  })
})
