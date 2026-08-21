import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const vacancyList = readFileSync(resolve(here, '../../../components/vacancies/VacancyList.tsx'), 'utf8')

describe('ListWorkspace orchestration proof (Vacancies)', () => {
  it('does not own search/filter/sort/pagination/selection/saved-view wiring locally', () => {
    expect(vacancyList).toContain('useListWorkspace')
    expect(vacancyList).toContain('<ListWorkspace')
    expect(vacancyList).toContain('controller={list}')
    expect(vacancyList).not.toMatch(/\buseSearchParams\b/)
    expect(vacancyList).not.toMatch(/\bnew URLSearchParams\b/)
    expect(vacancyList).not.toMatch(/\bsetSelected\b/)
    expect(vacancyList).not.toMatch(/\bgoPage\b/)
    expect(vacancyList).not.toMatch(/\bonSearch\b/)
    expect(vacancyList).not.toMatch(/\bapplyView\b/)
    expect(vacancyList).not.toMatch(/from ['"][^'"]*DataTable['"]/)
    expect(vacancyList).not.toMatch(/\bDataTable\b/)
  })
})
