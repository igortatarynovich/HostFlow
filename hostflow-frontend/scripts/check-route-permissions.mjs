import path from 'node:path'
import ts from 'typescript'

import {
  findArrayLiteral,
  getPropertyName,
  loadSource,
  parseCrmAppPathsMap,
  readString,
  resolvePathToAppSegment,
} from './crm-paths-ast.mjs'

const routesFile = path.join(process.cwd(), 'src', 'app', 'routes.tsx')
const crmPathsFile = path.join(process.cwd(), 'src', 'app', 'crmAppPaths.generated.ts')

const routesSf = loadSource(routesFile, ts.ScriptKind.TSX)
const crmSf = loadSource(crmPathsFile, ts.ScriptKind.TS)
const crmPaths = parseCrmAppPathsMap(crmSf)

function readPermission(node) {
  if (!node) return []
  if (ts.isStringLiteral(node)) return [node.text]
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.map((el) => readString(el)).filter(Boolean)
  }
  return []
}

function collectObjects(arrayNode) {
  if (!arrayNode) return []
  const out = []
  for (const el of arrayNode.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    const row = {}
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      const name = getPropertyName(prop.name)
      if (!name) continue
      if (name === 'permission') row.permission = readPermission(prop.initializer)
      else if (name === 'path') {
        row.path = resolvePathToAppSegment(prop.initializer, crmPaths)
      } else if (name === 'key' || name === 'action') {
        row[name] = readString(prop.initializer)
      }
    }
    out.push(row)
  }
  return out
}

const navItems = collectObjects(findArrayLiteral(routesSf, 'NAV_ITEMS'))
const appRoutes = collectObjects(findArrayLiteral(routesSf, 'APP_ROUTES'))

const appRouteByPath = new Map(appRoutes.map((r) => [r.path, r]))
const errors = []
const warnings = []

for (const nav of navItems) {
  if (!nav.path || nav.action === 'logout') continue

  const route = appRouteByPath.get(nav.path)
  if (!route) {
    errors.push(`[nav:${nav.key}] path segment "${nav.path}" has no matching APP_ROUTES entry`)
    continue
  }

  const navPerms = new Set(nav.permission || [])
  const routePerms = new Set(route.permission || [])

  if (navPerms.size === 0 && routePerms.size > 0) {
    errors.push(
      `[nav:${nav.key}] "/app/${nav.path}" has no nav permission, but route requires [${[...routePerms].join(', ')}]`,
    )
    continue
  }

  if (navPerms.size > 0 && routePerms.size === 0) {
    warnings.push(
      `[nav:${nav.key}] "/app/${nav.path}" has nav permission [${[...navPerms].join(', ')}], but route is unguarded`,
    )
    continue
  }

  if (navPerms.size > 0 && routePerms.size > 0) {
    const overlap = [...navPerms].filter((perm) => routePerms.has(perm))
    if (overlap.length === 0) {
      errors.push(
        `[nav:${nav.key}] "/app/${nav.path}" permission mismatch: nav=[${[...navPerms].join(', ')}] route=[${[...routePerms].join(', ')}]`,
      )
    }
  }
}

if (warnings.length) {
  console.log('Route permission warnings:')
  warnings.forEach((line) => console.log(`- ${line}`))
}

if (errors.length) {
  console.error('Route permission check failed:')
  errors.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(`Route permission check passed. Checked ${navItems.length} nav items and ${appRoutes.length} app routes.`)
