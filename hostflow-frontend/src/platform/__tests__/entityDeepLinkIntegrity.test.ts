/** @vitest-environment node */
/**
 * Stage 6C integrity: shared-platform surfaces must use the entity deep-link resolver.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '../..')

const SHARED_SURFACES = [
  'utils/resolveNotificationOpenPath.ts',
  'api/search.ts',
  'components/nav/Topbar.tsx',
  'components/activities/ActivitiesPanel.tsx',
  'modules/workHub/MyTasksPanel.tsx',
  'pages/RemindersPage.tsx',
  'pages/NotificationAlertsPage.tsx',
  'pages/hr/HrTasksPage.tsx',
  'components/communications/CommunicationsInboxThreadContextCard.tsx',
]

describe('Stage 6C shared-surface deep-link integrity', () => {
  it('shared surfaces import the entity deep-link resolver', () => {
    for (const rel of SHARED_SURFACES) {
      const src = readFileSync(join(ROOT, rel), 'utf8')
      const usesResolver =
        src.includes('entityDeepLinks') ||
        src.includes('buildEntityDeepLink') ||
        src.includes('navigateAppOrModuleLink') ||
        src.includes('resolveNotificationOpenPath') ||
        src.includes('EntityDeepLink') ||
        src.includes('resolveEntityDeepLink')
      expect(usesResolver, rel).toBe(true)
    }
  })

  it('shared surfaces do not assemble business entity URLs without the resolver on the same line', () => {
    const forbidden = [
      /CRM_APP_PATHS\.candidates\s*\}?\/\$\{/,
      /CRM_APP_PATHS\.agencyClients\s*\}?\/\$\{/,
      /CRM_APP_PATHS\.invoices\s*\}?\/\$\{/,
      /CRM_APP_PATHS\.hrEmployees\s*\}?\/\$\{/,
      /P\.candidates\s*\}?\/\$\{/,
      /P\.agencyClients\s*\}?\/\$\{/,
      /P\.invoices\s*\}?\/\$\{/,
    ]
    for (const rel of SHARED_SURFACES) {
      const lines = readFileSync(join(ROOT, rel), 'utf8').split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nearby = lines.slice(Math.max(0, i - 1), i + 2).join('\n')
        const allowed =
          nearby.includes('buildEntityDeepLink') ||
          nearby.includes('resolveEntityDeepLink') ||
          nearby.includes('EntityDeepLink')
        if (allowed) continue
        for (const re of forbidden) {
          expect(line.match(re), `${rel}:${i + 1} ${line.trim()}`).toBeNull()
        }
      }
    }
  })
})
