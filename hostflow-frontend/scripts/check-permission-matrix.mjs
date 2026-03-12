import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const permissionsFile = path.join(process.cwd(), 'src', 'hooks', 'usePermissions.ts')
const routesFile = path.join(process.cwd(), 'src', 'app', 'routes.tsx')

function loadSource(file, kind) {
  const text = fs.readFileSync(file, 'utf-8')
  return ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, kind)
}

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

function readStringArray(node) {
  if (!node || !ts.isArrayLiteralExpression(node)) return []
  return node.elements.map((el) => readString(el)).filter(Boolean)
}

function findObjectLiteral(sf, variableName) {
  for (const stmt of sf.statements) {
    if (!ts.isVariableStatement(stmt)) continue
    for (const decl of stmt.declarationList.declarations) {
      if (!ts.isIdentifier(decl.name) || decl.name.text !== variableName) continue
      if (decl.initializer && ts.isObjectLiteralExpression(decl.initializer)) {
        return decl.initializer
      }
    }
  }
  return null
}

function findArrayLiteral(sf, variableName) {
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

function parseRolePermissions(sf) {
  const obj = findObjectLiteral(sf, 'ROLE_PERMISSIONS')
  const map = {}
  if (!obj) return map
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const role = getPropertyName(prop.name)
    if (!role) continue
    map[role] = readStringArray(prop.initializer)
  }
  return map
}

function parseRoleAliases(sf) {
  const obj = findObjectLiteral(sf, 'ROLE_ALIAS')
  const map = {}
  if (!obj) return map
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const from = getPropertyName(prop.name)
    const to = readString(prop.initializer)
    if (!from || !to) continue
    map[from] = to
  }
  return map
}

function parseAppRoutes(sf) {
  const arr = findArrayLiteral(sf, 'APP_ROUTES')
  const routes = []
  if (!arr) return routes
  for (const el of arr.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    let key = null
    let routePath = null
    let permissions = []
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      const name = getPropertyName(prop.name)
      if (!name) continue
      if (name === 'key') key = readString(prop.initializer)
      if (name === 'path') routePath = readString(prop.initializer)
      if (name === 'permission') {
        if (ts.isStringLiteral(prop.initializer)) permissions = [prop.initializer.text]
        else permissions = readStringArray(prop.initializer)
      }
    }
    if (key && routePath) {
      routes.push({ key, path: routePath, permissions })
    }
  }
  return routes
}

function resolveRole(raw, aliases, rolePermissions) {
  const norm = String(raw || '').trim().toLowerCase()
  const alias = aliases[norm] || norm || 'viewer'
  if (rolePermissions[alias]) return alias
  return 'viewer'
}

function canAccess(roleKey, routePerms, rolePermissions) {
  const perms = new Set(rolePermissions[roleKey] || [])
  if (perms.has('*')) return true
  if (!routePerms || routePerms.length === 0) return true
  return routePerms.some((perm) => perms.has(perm))
}

const permSf = loadSource(permissionsFile, ts.ScriptKind.TS)
const routeSf = loadSource(routesFile, ts.ScriptKind.TSX)

const rolePermissions = parseRolePermissions(permSf)
const roleAliases = parseRoleAliases(permSf)
const appRoutes = parseAppRoutes(routeSf)

const targetRouteKeys = [
  'overview',
  'candidates',
  'clients',
  'leads',
  'services',
  'settings',
  'settings-users',
  'settings-company-access',
  'settings-communications',
  'settings-integrations',
]

const testRoles = [
  { label: 'superadmin', rawRole: 'superadmin' },
  { label: 'owner/admin', rawRole: 'administrator' },
  { label: 'supervisor', rawRole: 'supervisor' },
  { label: 'recruiter', rawRole: 'recruiter' },
  { label: 'viewer', rawRole: 'viewer' },
]

const EXPECTED_BASELINE = {
  overview: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'ALLOW',
    viewer: 'ALLOW',
  },
  candidates: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'ALLOW',
    viewer: 'ALLOW',
  },
  clients: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'ALLOW',
    viewer: 'ALLOW',
  },
  leads: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'ALLOW',
    viewer: 'ALLOW',
  },
  services: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'ALLOW',
    viewer: 'ALLOW',
  },
  settings: {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'DENY',
    viewer: 'DENY',
  },
  'settings-users': {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'DENY',
    viewer: 'DENY',
  },
  'settings-company-access': {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'DENY',
    viewer: 'DENY',
  },
  'settings-communications': {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'DENY',
    recruiter: 'DENY',
    viewer: 'DENY',
  },
  'settings-integrations': {
    superadmin: 'ALLOW',
    'owner/admin': 'ALLOW',
    supervisor: 'ALLOW',
    recruiter: 'DENY',
    viewer: 'DENY',
  },
}

const routesByKey = new Map(appRoutes.map((r) => [r.key, r]))
const missing = targetRouteKeys.filter((key) => !routesByKey.has(key))
if (missing.length) {
  console.error(`Permission matrix check failed: missing route keys: ${missing.join(', ')}`)
  process.exit(1)
}

const headers = ['Route', ...testRoles.map((r) => r.label)]
const table = []
const mismatches = []
for (const key of targetRouteKeys) {
  const route = routesByKey.get(key)
  const row = [`${route.path}${route.permissions.length ? ` [${route.permissions.join('|')}]` : ''}`]
  const expected = EXPECTED_BASELINE[key]
  for (const role of testRoles) {
    const resolvedRole = resolveRole(role.rawRole, roleAliases, rolePermissions)
    const actual = canAccess(resolvedRole, route.permissions, rolePermissions) ? 'ALLOW' : 'DENY'
    row.push(actual)
    if (!expected || expected[role.label] !== actual) {
      mismatches.push(
        `[${key}] role "${role.label}" expected=${expected?.[role.label] ?? 'N/A'} actual=${actual}`,
      )
    }
  }
  table.push(row)
}

console.log('Permission role matrix baseline:')
console.log(`| ${headers.join(' | ')} |`)
console.log(`| ${headers.map(() => '---').join(' | ')} |`)
for (const row of table) {
  console.log(`| ${row.join(' | ')} |`)
}

if (mismatches.length) {
  console.error('\nPermission matrix baseline mismatch:')
  mismatches.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(`\nPermission matrix check passed. Roles: ${testRoles.length}, routes: ${targetRouteKeys.length}.`)
