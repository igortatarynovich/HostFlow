import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const activationFile = path.join(process.cwd(), 'src', 'app', 'activationRoutes.ts')
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

function unwrap(node) {
  if (!node) return node
  if (ts.isAsExpression(node) || ts.isTypeAssertionExpression(node) || ts.isParenthesizedExpression(node)) {
    return unwrap(node.expression)
  }
  return node
}

function findObjectLiteral(sf, variableName) {
  for (const stmt of sf.statements) {
    if (!ts.isVariableStatement(stmt)) continue
    for (const decl of stmt.declarationList.declarations) {
      if (!ts.isIdentifier(decl.name) || decl.name.text !== variableName) continue
      const init = unwrap(decl.initializer)
      if (init && ts.isObjectLiteralExpression(init)) {
        return init
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
      const init = unwrap(decl.initializer)
      if (init && ts.isArrayLiteralExpression(init)) {
        return init
      }
    }
  }
  return null
}

function parseActivationPaths(sf) {
  const obj = findObjectLiteral(sf, 'ACTIVATION_PATHS')
  const out = {}
  if (!obj) return out
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const key = getPropertyName(prop.name)
    const value = readString(prop.initializer)
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

function parseAppRoutePaths(sf) {
  const arr = findArrayLiteral(sf, 'APP_ROUTES')
  const out = new Set()
  if (!arr) return out
  for (const el of arr.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    let routePath = null
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      const name = getPropertyName(prop.name)
      if (name === 'path') routePath = readString(prop.initializer)
    }
    if (routePath) out.add(`/app/${routePath}`)
  }
  return out
}

function toSet(values) {
  return new Set(values)
}

const activationSf = loadSource(activationFile, ts.ScriptKind.TS)
const routesSf = loadSource(routesFile, ts.ScriptKind.TSX)

const activationPaths = parseActivationPaths(activationSf)
const activationPrefixes = parseActivationPrefixes(activationSf, activationPaths)
const appRoutePaths = parseAppRoutePaths(routesSf)
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
