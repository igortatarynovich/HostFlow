/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = path.resolve(__dirname, '../../..')

describe('MA-3 leftover mapping surfaces cease to be editors', () => {
  it('Intake form mapping is deep-link or fail-closed, not a writer', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/components/admin/IntakeFormMappingEditor.tsx'),
      'utf8',
    )
    expect(src).not.toContain('putIntakeFormMapping')
    expect(src).not.toContain('previewIntakeFormMapping')
    expect(src).not.toContain('testIntakeFormMappingIngest')
    expect(src).toContain('getIntakeFormMapping')
    expect(src).toContain('marketingSourceMappingPath')
    expect(src).toContain('intake-form-mapping-workspace')
    expect(src).toContain('intake-form-mapping-unbound')
  })

  it('Intake form detail still hosts the leftover fold, not a second editor', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/admin/IntakeFormDetailPage.tsx'),
      'utf8',
    )
    expect(src).toContain('IntakeFormMappingEditor')
    expect(src).not.toContain('putIntakeFormMapping')
  })

  it('Meta Settings field mapping is deep-link, not a writer', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/admin/MetaLeadsAdminPage.tsx'),
      'utf8',
    )
    expect(src).not.toContain('putMetaLeadFormMapping')
    expect(src).not.toContain('handleSaveFieldMapping')
    expect(src).not.toContain('field_mapping: built')
    expect(src).toContain('marketingSourceMappingPath')
    expect(src).toContain('meta-field-mapping-workspace')
  })
})
