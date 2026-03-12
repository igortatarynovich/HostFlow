import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const routesFile = path.join(process.cwd(), 'src', 'app', 'routes.tsx')
const source = fs.readFileSync(routesFile, 'utf-8')
const sf = ts.createSourceFile(routesFile, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)

function getPropertyName(node) {
  if (!node) return null
  if (ts.isIdentifier(node) || ts.isStringLiteral(node)) return node.text
  return null
}

function readString(node) {
  if (!node) return null
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text
  return null
}

function readPermission(node) {
  if (!node) return []
  if (ts.isStringLiteral(node)) return [node.text]
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.map((el) => readString(el)).filter(Boolean)
  }
  return []
}

function findArrayLiteral(variableName) {
  for (const stmt of sf.statements) {
    if (!ts.isVariableStatement(stmt)) continue
    for (const decl of stmt.declarationList.declarations) {
      if (!ts.isIdentifier(decl.name) || decl.name.text !== variableName) continue
      if (decl.initializer && ts.isArrayLiteralExpression(decl.initializer)) {
        return decl.initializer
      }
    }
  }
  return null
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
      else if (name === 'path' || name === 'key' || name === 'action') row[name] = readString(prop.initializer)
    }
    out.push(row)
  }
  return out
}

const navItems = collectObjects(findArrayLiteral('NAV_ITEMS'))
const appRoutes = collectObjects(findArrayLiteral('APP_ROUTES'))

const appRouteByPath = new Map(appRoutes.map((r) => [r.path, r]))
const errors = []
const warnings = []

for (const nav of navItems) {
  if (!nav.path || nav.action === 'logout') continue
  if (!nav.path.startsWith('/app/')) {
    warnings.push(`[nav:${nav.key}] non-app path "${nav.path}" skipped`)
    continue
  }

  const appPath = nav.path.slice('/app/'.length)
  const route = appRouteByPath.get(appPath)
  if (!route) {
    errors.push(`[nav:${nav.key}] path "${nav.path}" has no matching APP_ROUTES entry ("${appPath}")`)
    continue
  }

  const navPerms = new Set(nav.permission || [])
  const routePerms = new Set(route.permission || [])

  if (navPerms.size === 0 && routePerms.size > 0) {
    errors.push(
      `[nav:${nav.key}] "${nav.path}" has no nav permission, but route requires [${[...routePerms].join(', ')}]`,
    )
    continue
  }

  if (navPerms.size > 0 && routePerms.size === 0) {
    warnings.push(
      `[nav:${nav.key}] "${nav.path}" has nav permission [${[...navPerms].join(', ')}], but route is unguarded`,
    )
    continue
  }

  if (navPerms.size > 0 && routePerms.size > 0) {
    const overlap = [...navPerms].filter((perm) => routePerms.has(perm))
    if (overlap.length === 0) {
      errors.push(
        `[nav:${nav.key}] "${nav.path}" permission mismatch: nav=[${[...navPerms].join(', ')}] route=[${[...routePerms].join(', ')}]`,
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
