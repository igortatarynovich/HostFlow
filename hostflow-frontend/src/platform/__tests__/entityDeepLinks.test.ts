/** @vitest-environment node */
/**
 * Stage 6C — entity deep-link matrix + no shell business fallback.
 */
import { describe, expect, it } from 'vitest'
import registry from '@shared/module_deploy_hosts.json'
import {
  buildEntityDeepLink,
  normalizeEntityType,
  resolveEntityDeepLink,
  rewriteBusinessAppPath,
} from '../entityDeepLinks'
import { DEPLOYMENT_HOSTS } from '../deployHosts'

const MATRIX: Array<{ entity: string; host: keyof typeof DEPLOYMENT_HOSTS; pathIncludes: string }> = [
  { entity: 'candidate', host: 'recruitment', pathIncludes: '/app/candidates/' },
  { entity: 'employee', host: 'hr', pathIncludes: '/app/hr/employees/' },
  { entity: 'inquiry', host: 'sales', pathIncludes: '/app/sales/inquiries/' },
  { entity: 'client_account', host: 'sales', pathIncludes: '/app/clients/' },
  { entity: 'client', host: 'sales', pathIncludes: '/app/clients/' },
  { entity: 'vehicle', host: 'fleet', pathIncludes: '/app/fleet/vehicles/' },
  { entity: 'invoice', host: 'finance', pathIncludes: '/app/invoices/' },
  { entity: 'payment', host: 'finance', pathIncludes: 'payment=' },
  { entity: 'service_order', host: 'sales', pathIncludes: '/app/services' },
]

describe('Stage 6C entity deep-link matrix', () => {
  it('maps each product entity to the owning host and path template', () => {
    for (const row of MATRIX) {
      const resolved = resolveEntityDeepLink(row.entity, 'id-1')
      expect(resolved, row.entity).not.toBeNull()
      expect(resolved!.host).toBe(row.host)
      expect(resolved!.path).toContain(row.pathIncludes)
      expect(resolved!.href).toContain(row.pathIncludes)
    }
  })

  it('registry catalog hosts are only the five product modules', () => {
    const catalog = registry.entity_deep_links as Record<string, { host: string }>
    for (const [entity, row] of Object.entries(catalog)) {
      expect(['recruitment', 'hr', 'sales', 'fleet', 'finance'], entity).toContain(row.host)
    }
  })

  it('services is not a sixth licensed entity host', () => {
    const hosts = Object.values(registry.entity_deep_links as Record<string, { host: string }>).map(
      (r) => r.host,
    )
    expect(hosts).not.toContain('services')
    expect(resolveEntityDeepLink('service_order', 'o1')!.host).toBe('sales')
  })

  it('unknown / deleted / shell entity types do not fall back to shell business routes', () => {
    expect(resolveEntityDeepLink('unknown_widget', 'x')).toBeNull()
    expect(resolveEntityDeepLink('thread', 't1')).toBeNull()
    expect(resolveEntityDeepLink('communication_thread', 't1')).toBeNull()
    expect(resolveEntityDeepLink('task', 't1')).toBeNull()
    expect(buildEntityDeepLink('deleted_type', 'x')).toBeNull()
    expect(normalizeEntityType('bogus')).toBeNull()
  })

  it('query allowlist strips unknown params', () => {
    const resolved = resolveEntityDeepLink('candidate', 'c1', {
      query: { focus: 'tasks', evil: '1', company_id: 'co1' },
    })
    expect(resolved!.path).toContain('focus=tasks')
    expect(resolved!.path).toContain('company_id=co1')
    expect(resolved!.path).not.toContain('evil=')
  })

  it('rewrites legacy relative business paths through the registry', () => {
    expect(rewriteBusinessAppPath('/app/candidates/abc')).toContain('/app/candidates/abc')
    expect(rewriteBusinessAppPath('/app/hr/employees/e1')).toContain('/app/hr/employees/e1')
    expect(rewriteBusinessAppPath('/app/services?order=o9')).toContain('order=o9')
    expect(rewriteBusinessAppPath('/app/overview')).toBeNull()
  })
})
