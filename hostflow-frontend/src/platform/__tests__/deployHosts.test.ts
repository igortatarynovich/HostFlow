/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import registry from '@shared/module_deploy_hosts.json'
import {
  APP_PATH_PREFIX_TO_DEPLOY_HOST,
  AUTH_HANDOFF_STATUS,
  buildModuleAbsoluteUrl,
  BUSINESS_MODULE_HOSTS,
  DEPLOYMENT_HOSTS,
  SHELL_PLATFORM_PATH_PREFIXES,
  filterNavItemsForDeployHost,
  isAllowedHandoffNext,
  isNavKeyAllowedOnHost,
  isShellPlatformPath,
  locationTargetWithoutAuthHash,
  resolveDeployHost,
  resolvePathDeployHost,
  consumeAuthHandoffHash,
  withAuthHandoffHash,
  withDeployAwareNavPaths,
} from '../deployHosts'
import { buildEntityDeepLink, resolveEntityDeepLink } from '../entityDeepLinks'

describe('deployHosts registry integrity (ADR-023 §3.7 Stage 6A)', () => {
  it('maps production hostnames to five modules + shell', () => {
    expect(resolveDeployHost({ hostname: 'hostflow.cc' })).toBe('shell')
    expect(resolveDeployHost({ hostname: 'www.hostflow.cc' })).toBe('shell')
    expect(resolveDeployHost({ hostname: 'recruitment.hostflow.cc' })).toBe('recruitment')
    expect(resolveDeployHost({ hostname: 'hr.hostflow.cc' })).toBe('hr')
    expect(resolveDeployHost({ hostname: 'sales.hostflow.cc' })).toBe('sales')
    expect(resolveDeployHost({ hostname: 'fleet.hostflow.cc' })).toBe('fleet')
    expect(resolveDeployHost({ hostname: 'finance.hostflow.cc' })).toBe('finance')
    expect(BUSINESS_MODULE_HOSTS).toHaveLength(5)
    expect(Object.keys(DEPLOYMENT_HOSTS)).toEqual(
      expect.arrayContaining(['shell', ...BUSINESS_MODULE_HOSTS]),
    )
  })

  it('unknown hostname does not invent a business module context', () => {
    expect(resolveDeployHost({ hostname: 'unknown.hostflow.cc' })).toBe('shell')
    expect(resolveDeployHost({ hostname: 'evil.example' })).toBe('shell')
    expect(resolveDeployHost({ hostname: 'services.hostflow.cc' })).toBe('shell')
  })

  it('supports local emulation via env and query', () => {
    expect(resolveDeployHost({ hostname: 'localhost', envModuleHost: 'sales' })).toBe('sales')
    expect(resolveDeployHost({ hostname: 'localhost', search: '?hf_module=hr' })).toBe('hr')
    expect(resolveDeployHost({ hostname: '127.0.0.1' })).toBe('shell')
  })

  it('each module route prefix has exactly one owning host', () => {
    const byPrefix = new Map<string, string>()
    for (const row of APP_PATH_PREFIX_TO_DEPLOY_HOST) {
      expect(byPrefix.has(row.prefix)).toBe(false)
      byPrefix.set(row.prefix, row.host)
      expect(BUSINESS_MODULE_HOSTS.includes(row.host as (typeof BUSINESS_MODULE_HOSTS)[number])).toBe(
        true,
      )
    }
  })

  it('no route prefix is owned by two modules', () => {
    const owners = new Map<string, Set<string>>()
    for (const row of APP_PATH_PREFIX_TO_DEPLOY_HOST) {
      const set = owners.get(row.prefix) || new Set()
      set.add(row.host)
      owners.set(row.prefix, set)
    }
    for (const [prefix, set] of owners) {
      expect(set.size, prefix).toBe(1)
    }
  })

  it('shell platform paths are not business objects', () => {
    for (const prefix of SHELL_PLATFORM_PATH_PREFIXES) {
      expect(isShellPlatformPath(prefix)).toBe(true)
      expect(resolvePathDeployHost(prefix)).toBe('shell')
    }
    expect(isShellPlatformPath('/app/candidates')).toBe(false)
    expect(isShellPlatformPath('/app/invoices')).toBe(false)
    expect(isShellPlatformPath('/app/hr/employees')).toBe(false)
  })

  it('foreign routes resolve to the owning host', () => {
    expect(resolvePathDeployHost('/app/candidates/abc')).toBe('recruitment')
    expect(resolvePathDeployHost('/app/hr/employees')).toBe('hr')
    expect(resolvePathDeployHost('/app/sales')).toBe('sales')
    expect(resolvePathDeployHost('/app/invoices/1')).toBe('finance')
    expect(resolvePathDeployHost('/app/fleet')).toBe('fleet')
    expect(resolvePathDeployHost('/app/overview')).toBe('shell')
    expect(resolvePathDeployHost('/app/services')).toBe('sales')
  })

  it('redirect target preserves query and non-auth fragment', () => {
    expect(locationTargetWithoutAuthHash('/app/sales', '?x=1', '#section')).toBe(
      '/app/sales?x=1#section',
    )
    expect(locationTargetWithoutAuthHash('/app/sales', '?x=1', '#hf_auth=tok')).toBe(
      '/app/sales?x=1',
    )
  })

  it('next allowlist rejects external / protocol-relative / exotic ports / nested evil', () => {
    expect(isAllowedHandoffNext('https://recruitment.hostflow.cc/app/candidates')).toBe(true)
    expect(isAllowedHandoffNext('https://hostflow.cc/app/overview')).toBe(true)
    expect(isAllowedHandoffNext('https://hr.hostflow.cc/app/hr')).toBe(true)
    expect(isAllowedHandoffNext('https://sales.hostflow.cc/app/sales')).toBe(true)
    expect(isAllowedHandoffNext('https://fleet.hostflow.cc/app/fleet')).toBe(true)
    expect(isAllowedHandoffNext('https://finance.hostflow.cc/app/invoices')).toBe(true)
    expect(isAllowedHandoffNext('https://evil.example/app')).toBe(false)
    expect(isAllowedHandoffNext('//evil.example/app')).toBe(false)
    expect(isAllowedHandoffNext('https://hostflow.cc.evil.example/')).toBe(false)
    expect(isAllowedHandoffNext('https://recruitment.hostflow.cc:8443/app')).toBe(false)
    expect(isAllowedHandoffNext('/app/sales')).toBe(true)
    expect(
      isAllowedHandoffNext('/app/overview?next=https://evil.example/phish', { allowLocalhost: false }),
    ).toBe(false)
    expect(
      isAllowedHandoffNext('https://hostflow.cc/app?next=https://evil.example/', {
        allowLocalhost: false,
      }),
    ).toBe(false)
  })

  it('entity deep links resolve to owning hosts', () => {
    expect(buildEntityDeepLink('candidate', 'c1')).toContain('/app/candidates/c1')
    expect(buildEntityDeepLink('employee', 'e1')).toContain('/app/hr/employees/e1')
    expect(buildEntityDeepLink('client_account', 'a1')).toContain('/app/clients/a1')
    expect(buildEntityDeepLink('vehicle', 'v1')).toContain('/app/fleet/vehicles/v1')
    expect(buildEntityDeepLink('invoice', 'i1')).toContain('/app/invoices/i1')
    expect(buildEntityDeepLink('inquiry', 'q1')).toContain('/app/sales/inquiries/q1')
    expect(buildEntityDeepLink('service_order', 'o1')).toContain('/app/services')
    expect(buildEntityDeepLink('payment', 'p1')).toContain('payment=p1')
    expect(buildEntityDeepLink('unknown_entity', 'x')).toBeNull()
    expect(resolveEntityDeepLink('thread', 't1')).toBeNull()
    expect(resolveEntityDeepLink('candidate', '')).toBeNull()
  })

  it('shows sibling business modules as cross-host launchers on every host', () => {
    expect(isNavKeyAllowedOnHost('candidates', 'recruitment')).toBe(true)
    expect(isNavKeyAllowedOnHost('sales', 'recruitment')).toBe(true)
    expect(isNavKeyAllowedOnHost('hr-workspace', 'recruitment')).toBe(true)
    expect(isNavKeyAllowedOnHost('service-orders', 'recruitment')).toBe(true)
    expect(isNavKeyAllowedOnHost('invoices', 'finance')).toBe(true)
    expect(isNavKeyAllowedOnHost('profile', 'finance')).toBe(true)
    expect(isNavKeyAllowedOnHost('sales', 'shell')).toBe(true)

    const items = [{ key: 'candidates' }, { key: 'sales' }, { key: 'profile' }]
    expect(filterNavItemsForDeployHost(items, 'recruitment').map((i) => i.key)).toEqual([
      'candidates',
      'sales',
      'profile',
    ])

    const withPaths = withDeployAwareNavPaths(
      [
        { key: 'sales', path: '/app/sales' },
        { key: 'candidates', path: '/app/candidates' },
      ],
      'recruitment',
    )
    expect(withPaths.find((i) => i.key === 'sales')?.path).toMatch(/^https:\/\/sales\.hostflow\.cc\//)
    expect(withPaths.find((i) => i.key === 'candidates')?.path).toBe('/app/candidates')

    // Pre-absolutized paths must not become https://host/https://host/...
    const doubled = withDeployAwareNavPaths(
      [{ key: 'sales', path: 'https://sales.hostflow.cc/app/sales' }],
      'recruitment',
    )
    expect(doubled[0]?.path).toBe('https://sales.hostflow.cc/app/sales')
    expect(buildModuleAbsoluteUrl('sales', 'https://sales.hostflow.cc/app/sales')).toBe(
      'https://sales.hostflow.cc/app/sales',
    )
  })

  it('marks hash auth handoff as removed in Stage 6B', () => {
    expect(AUTH_HANDOFF_STATUS).toBe('removed_stage_6b')
    expect(registry.auth_handoff.hash_prefix).toBe('hf_auth=')
    // withAuthHandoffHash must never embed tokens
    const withHash = withAuthHandoffHash('https://sales.hostflow.cc/app/sales', 'tok123')
    expect(withHash).not.toContain('hf_auth=')
    expect(withHash).not.toContain('tok123')
    expect(consumeAuthHandoffHash('#hf_auth=tok123')).toBeNull()
  })
})
