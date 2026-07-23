/**
 * C-2 mandatory scan: no user path may create a new searchAcquisition launch.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'
import { marketingSetupWithVacancyTargetPath } from '../crmAppPaths'
import { createAcquisitionActivity } from '../../api/searchAcquisition'

const FE_ROOT = join(__dirname, '../..')
const REPO_HINT = relative(process.cwd(), FE_ROOT)

const ALLOW_CREATE_MENTIONS = new Set([
  'api/searchAcquisition.ts',
  'app/__tests__/acquisitionC2LegacyLaunchScan.test.ts',
])

const FORBIDDEN = [
  /api\.post\s*<[^>]*>\s*\(\s*[`'"][^`'"]*\/acquisition\/(?:activities|channels)/,
  /api\.post\s*\(\s*[`'"][^`'"]*\/acquisition\/(?:activities|channels)/,
  /[`'"]\/vacancies\/\$\{[^}]+\}\/acquisition\/(?:activities|channels)/,
  /createAcquisitionActivity\s*\(/,
  /createAcquisitionChannel\s*\(/,
]

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === 'dist' || name === 'coverage') continue
    const full = join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) walk(full, out)
    else if (/\.(ts|tsx)$/.test(name)) out.push(full)
  }
  return out
}

describe('C-2 legacy launch stop', () => {
  it('marketingSetupWithVacancyTargetPath points at Campaign setup', () => {
    const href = marketingSetupWithVacancyTargetPath('vac-123', { name: 'Cook PL' })
    expect(href.startsWith('/app/marketing/new?')).toBe(true)
    expect(href).toContain('target_type=vacancy')
    expect(href).toContain('target_id=vac-123')
    expect(href).toContain('flow=candidates')
    expect(href).toContain('name=Cook')
  })

  it('createAcquisitionActivity hard-fails client-side', async () => {
    await expect(createAcquisitionActivity('vac-1', { type: 'meta', name: 'x' })).rejects.toThrow(
      /legacy_launch_disabled/,
    )
  })

  it('scans frontend for hidden searchAcquisition create/launch call sites', () => {
    const offenders: string[] = []
    for (const file of walk(FE_ROOT)) {
      const rel = relative(FE_ROOT, file).replace(/\\/g, '/')
      if (ALLOW_CREATE_MENTIONS.has(rel)) continue
      const text = readFileSync(file, 'utf8')
      for (const pattern of FORBIDDEN) {
        if (pattern.test(text)) {
          offenders.push(`${REPO_HINT}/${rel}: ${pattern}`)
        }
      }
      // Legacy launch page must not POST create.
      if (rel.endsWith('LaunchAcquisitionPage.tsx')) {
        expect(text).not.toMatch(/createAcquisition/)
        expect(text).toMatch(/marketingSetupWithVacancyTargetPath|\/app\/marketing\/new/)
      }
    }
    expect(offenders, offenders.join('\n')).toEqual([])
  })

  it('LaunchAcquisitionPage redirects to Marketing', () => {
    const text = readFileSync(join(FE_ROOT, 'pages/recruitment/LaunchAcquisitionPage.tsx'), 'utf8')
    expect(text).toContain('navigate(marketingHref')
    expect(text).toContain('legacy_launch_disabled')
  })

  it('AcquisitionLayout CTA goes to Marketing setup (not legacy create)', () => {
    const text = readFileSync(join(FE_ROOT, 'pages/recruitment/AcquisitionLayout.tsx'), 'utf8')
    expect(text).toContain('marketingSetupWithVacancyTargetPath')
    expect(text).toContain('acquisition-legacy-banner')
    expect(text).not.toMatch(/recruitmentSearchAcquisitionNewPath/)
  })
})
