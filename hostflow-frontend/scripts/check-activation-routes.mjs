import path from 'node:path'
import ts from 'typescript'

import {
  findArrayLiteral,
  findObjectLiteral,
  getPropertyName,
  loadSource,
  parseCrmAppPathsMap,
  readString,
  resolvePathToFullAppUrl,
  unwrap,
} from './crm-paths-ast.mjs'

const activationFile = path.join(process.cwd(), 'src', 'app', 'activationRoutes.ts')
const crmPathsFile = path.join(process.cwd(), 'src', 'app', 'crmAppPaths.generated.ts')
const routesFile = path.join(process.cwd(), 'src', 'app', 'routes.tsx')

function readCrmPathRef(node, crmPaths) {
  const init = unwrap(node)
  const s = readString(init)
  if (s) return s
  if (
    init &&
    ts.isPropertyAccessExpression(init) &&
    ts.isIdentifier(init.expression) &&
    init.expression.text === 'CRM_APP_PATHS'
  ) {
    const k = init.name.text
    return crmPaths[k] ?? null
  }
  return null
}

function parseActivationPaths(sf, crmPaths) {
  const obj = findObjectLiteral(sf, 'ACTIVATION_PATHS')
  const out = {}
  if (!obj) return out
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const key = getPropertyName(prop.name)
    const value = readCrmPathRef(prop.initializer, crmPaths)
    if (!key || !value) continue
    out[key] = value
  }
  return out
}

function parseActivationPrefixes(sf, activationPaths) {
  const arr = findArrayLiteral(sf, 'ACTIVATION_ALLOWED_PREFIXES')
  const out = []
  if (!arr) return out
  for (const el of arr.elements) {
    if (ts.isPropertyAccessExpression(el) && ts.isIdentifier(el.expression) && el.expression.text === 'ACTIVATION_PATHS') {
      const key = el.name.text
      const value = activationPaths[key]
      if (value) out.push(value)
      continue
    }
    const value = readString(el)
    if (value) out.push(value)
  }
  return out
}

function parseAppRoutePaths(sf, crmPaths) {
  const arr = findArrayLiteral(sf, 'APP_ROUTES')
  const out = new Set()
  if (!arr) return out
  for (const el of arr.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      if (getPropertyName(prop.name) !== 'path') continue
      const full = resolvePathToFullAppUrl(prop.initializer, crmPaths)
      if (full) out.add(full)
    }
  }
  return out
}

function toSet(values) {
  return new Set(values)
}

const activationSf = loadSource(activationFile, ts.ScriptKind.TS)
const crmSf = loadSource(crmPathsFile, ts.ScriptKind.TS)
const routesSf = loadSource(routesFile, ts.ScriptKind.TSX)

const crmAppPathsMap = parseCrmAppPathsMap(crmSf)
const activationPaths = parseActivationPaths(activationSf, crmAppPathsMap)
const activationPrefixes = parseActivationPrefixes(activationSf, activationPaths)
const appRoutePaths = parseAppRoutePaths(routesSf, crmAppPathsMap)
const errors = []

const requiredPathKeys = [
  'overview',
  'onboarding',
  'onboardingCompany',
  'onboardingGettingStarted',
  'clients',
  'vacancies',
  'leads',
  'reminders',
  'billing',
  'legal',
]

for (const key of requiredPathKeys) {
  if (!activationPaths[key]) {
    errors.push(`ACTIVATION_PATHS is missing required key "${key}"`)
  }
}

for (const [key, value] of Object.entries(activationPaths)) {
  if (!value.startsWith('/app/')) {
    errors.push(`ACTIVATION_PATHS.${key} must start with "/app/", got "${value}"`)
  }
}

const appRouteBackedKeys = requiredPathKeys.filter(
  (k) => !['onboarding', 'onboardingCompany', 'onboardingGettingStarted'].includes(k),
)

for (const key of appRouteBackedKeys) {
  const value = activationPaths[key]
  if (!value) continue
  if (!appRoutePaths.has(value)) {
    errors.push(`ACTIVATION_PATHS.${key}="${value}" has no matching APP_ROUTES path`)
  }
}

if (activationPaths.onboardingCompany && !activationPaths.onboardingCompany.startsWith(activationPaths.onboarding || '')) {
  errors.push('ACTIVATION_PATHS.onboardingCompany must be under ACTIVATION_PATHS.onboarding prefix')
}
if (
  activationPaths.onboardingGettingStarted &&
  !activationPaths.onboardingGettingStarted.startsWith(activationPaths.onboarding || '')
) {
  errors.push('ACTIVATION_PATHS.onboardingGettingStarted must be under ACTIVATION_PATHS.onboarding prefix')
}

const expectedPrefixes = [
  activationPaths.onboarding,
  activationPaths.clients,
  activationPaths.vacancies,
  activationPaths.leads,
  activationPaths.reminders,
  activationPaths.billing,
  activationPaths.legal,
].filter(Boolean)

const expectedSet = toSet(expectedPrefixes)
const actualSet = toSet(activationPrefixes)
for (const p of expectedSet) {
  if (!actualSet.has(p)) errors.push(`ACTIVATION_ALLOWED_PREFIXES missing "${p}"`)
}
for (const p of actualSet) {
  if (!expectedSet.has(p)) errors.push(`ACTIVATION_ALLOWED_PREFIXES has unexpected prefix "${p}"`)
}

if (errors.length) {
  console.error('Activation routes check failed:')
  errors.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(
  `Activation routes check passed. Paths: ${Object.keys(activationPaths).length}, prefixes: ${activationPrefixes.length}.`,
)
