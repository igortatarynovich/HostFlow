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

function resolveRole(raw, aliases, rolePermissions, tenantType = 'agency') {
  const norm = String(raw || '').trim().toLowerCase()
  const alias = aliases[norm] || norm || 'viewer'
  let effective = alias
  // Mirror usePermissions: recruiter in client-tenant context behaves like client_processor.
  if (tenantType === 'company' && effective === 'recruiter') {
    effective = 'client_processor'
  }
  if (rolePermissions[effective]) return effective
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

const EXPECTED_BASELINE_DEFAULT = {
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

const EXPECTED_BASELINE_CLIENT_TENANT = {
  ...EXPECTED_BASELINE_DEFAULT,
  leads: { ...EXPECTED_BASELINE_DEFAULT.leads, recruiter: 'DENY' },
  services: { ...EXPECTED_BASELINE_DEFAULT.services, recruiter: 'DENY' },
}

function parseArgs(argv) {
  const out = { reportFile: null }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--report-file') {
      out.reportFile = argv[i + 1] || null
      i += 1
    }
  }
  return out
}

function toMarkdownTable(headers, rows) {
  const lines = []
  lines.push(`| ${headers.join(' | ')} |`)
  lines.push(`| ${headers.map(() => '---').join(' | ')} |`)
  for (const row of rows) {
    lines.push(`| ${row.join(' | ')} |`)
  }
  return lines.join('\n')
}

function writeMarkdownReport(reportFile, results) {
  if (!reportFile) return
  const now = new Date().toISOString().slice(0, 10)
  const body = [
    '# F3 Permission Matrix Static Snapshot',
    '',
    `Date: \`${now}\``,
    'Source: `npm --prefix hostflow-frontend run permissions:report`',
    '',
    'Этот файл сгенерирован автоматически из `scripts/check-permission-matrix.mjs`.',
    '',
    ...results.flatMap((result) => [
      `## ${result.label}`,
      '',
      toMarkdownTable(result.headers, result.table),
      '',
      `Mismatches: \`${result.mismatches.length}\``,
      '',
    ]),
  ].join('\n')
  const absPath = path.resolve(process.cwd(), reportFile)
  fs.mkdirSync(path.dirname(absPath), { recursive: true })
  fs.writeFileSync(absPath, `${body}\n`, 'utf-8')
  console.log(`Permission matrix report written to ${absPath}`)
}

function runMatrix({ label, tenantType, expectedBaseline }) {
  const headers = ['Route', ...testRoles.map((r) => r.label)]
  const table = []
  const mismatches = []
  for (const key of targetRouteKeys) {
    const route = routesByKey.get(key)
    const row = [`${route.path}${route.permissions.length ? ` [${route.permissions.join('|')}]` : ''}`]
    const expected = expectedBaseline[key]
    for (const role of testRoles) {
      const resolvedRole = resolveRole(role.rawRole, roleAliases, rolePermissions, tenantType)
      const actual = canAccess(resolvedRole, route.permissions, rolePermissions) ? 'ALLOW' : 'DENY'
      row.push(actual)
      if (!expected || expected[role.label] !== actual) {
        mismatches.push(
          `[${label}] [${key}] role "${role.label}" expected=${expected?.[role.label] ?? 'N/A'} actual=${actual}`,
        )
      }
    }
    table.push(row)
  }

  console.log(`Permission role matrix baseline (${label}):`)
  console.log(`| ${headers.join(' | ')} |`)
  console.log(`| ${headers.map(() => '---').join(' | ')} |`)
  for (const row of table) {
    console.log(`| ${row.join(' | ')} |`)
  }
  console.log('')
  return { label, headers, table, mismatches }
}

const args = parseArgs(process.argv.slice(2))
const results = [
  runMatrix({ label: 'default-tenant', tenantType: 'agency', expectedBaseline: EXPECTED_BASELINE_DEFAULT }),
  runMatrix({ label: 'client-tenant', tenantType: 'company', expectedBaseline: EXPECTED_BASELINE_CLIENT_TENANT }),
]
const mismatches = results.flatMap((result) => result.mismatches)

writeMarkdownReport(args.reportFile, results)

if (mismatches.length) {
  console.error('Permission matrix baseline mismatch:')
  mismatches.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(
  `Permission matrix check passed. Contexts: 2, roles: ${testRoles.length}, routes: ${targetRouteKeys.length}.`,
)
