/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { NAV_ITEMS } from '../../app/routes'
import { isNavKeyAccountedForInSidebarPlacement } from '../sidebarRailBuckets'

describe('sidebar nav placement integrity', () => {
  it('every NAV_ITEMS entry with a path is on agency rail, client flat list, hidden, hub-only, or standalone', () => {
    const missing: string[] = []
    for (const item of NAV_ITEMS) {
      if (!item.path) continue
      if (item.action === 'logout') continue
      if (isNavKeyAccountedForInSidebarPlacement(item.key)) continue
      missing.push(item.key)
    }
    expect(
      missing,
      `Add keys to sidebarRailBuckets (agency buckets / client flat / hub / standalone) or appShellNav hidden: ${missing.join(', ')}`,
    ).toEqual([])
  })
})
