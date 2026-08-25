import path from 'node:path'
import ts from 'typescript'

import {
  findArrayLiteral,
  getPropertyName,
  loadSource,
  parseCrmAppPathsMap,
  readString,
  readStringArray,
  resolvePathPatternToAppSegment,
} from './crm-paths-ast.mjs'

const routesFile = path.join(process.cwd(), 'src', 'app', 'routes.tsx')
const crmPathsFile = path.join(process.cwd(), 'src', 'app', 'crmAppPaths.generated.ts')

const routesSf = loadSource(routesFile, ts.ScriptKind.TSX)
const crmSf = loadSource(crmPathsFile, ts.ScriptKind.TS)
const crmPaths = parseCrmAppPathsMap(crmSf)

const EXPECTED_COMM_GATES = {
  'communications-setup': { type: 'any', features: ['messages', 'email'] },
  'communications-inbox-hub': { type: 'any', features: ['messages', 'email'] },
  'communications-inbox-center': { type: 'any', features: ['messages', 'email'] },
  'email-inbox': { type: 'feature', features: ['email'] },
  'messages-inbox': { type: 'feature', features: ['messages'] },
  calendar: { type: 'feature', features: ['calendar'] },
  'sla-incidents': { type: 'any', features: ['messages', 'email'] },
  'command-audit': { type: 'feature', features: ['communicationsAdmin'] },
  'team-availability': { type: 'feature', features: ['teamAvailability'] },
  'my-availability': { type: 'feature', features: ['myAvailability'] },
  'time-off': { type: 'feature', features: ['timeOffRequests'] },
  'communications-thread': { type: 'any', features: ['messages', 'email'] },
  'settings-communications': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-messengers': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-integrations-messenger-channel': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-queue': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-sla': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-templates': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-automation': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-lead-lifecycle-email': { type: 'feature', features: ['communicationsAdmin'] },
  'settings-communications-campaigns': { type: 'feature', features: ['communicationsAdmin'] },
}

function parseComponentGate(node) {
  if (!node) return { type: 'none', features: [] }
  if (!ts.isCallExpression(node) || !ts.isIdentifier(node.expression)) {
    return { type: 'none', features: [] }
  }
  const callee = node.expression.text
  if (callee === 'withCommFeature') {
    const feature = readString(node.arguments[1])
    return { type: 'feature', features: feature ? [feature] : [] }
  }
  if (callee === 'withCommAnyFeature') {
    return { type: 'any', features: readStringArray(node.arguments[1]) }
  }
  return { type: 'none', features: [] }
}

function parseRoutes() {
  const arr = findArrayLiteral(routesSf, 'APP_ROUTES')
  const routes = []
  if (!arr) return routes
  for (const el of arr.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    let key = null
    let routePath = null
    let gate = { type: 'none', features: [] }
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      const name = getPropertyName(prop.name)
      if (!name) continue
      if (name === 'key') key = readString(prop.initializer)
      if (name === 'path') routePath = resolvePathPatternToAppSegment(prop.initializer, crmPaths)
      if (name === 'Component') gate = parseComponentGate(prop.initializer)
    }
    if (key && routePath) routes.push({ key, path: routePath, gate })
  }
  return routes
}

function sameFeatures(left, right) {
  const a = [...left].sort()
  const b = [...right].sort()
  if (a.length !== b.length) return false
  return a.every((item, idx) => item === b[idx])
}

const routes = parseRoutes()
const byKey = new Map(routes.map((r) => [r.key, r]))
const errors = []

for (const [key, expected] of Object.entries(EXPECTED_COMM_GATES)) {
  const route = byKey.get(key)
  if (!route) {
    errors.push(`[${key}] missing route in APP_ROUTES`)
    continue
  }
  if (route.gate.type !== expected.type) {
    errors.push(
      `[${key}] invalid gate type: expected=${expected.type} actual=${route.gate.type} path="${route.path}"`,
    )
    continue
  }
  if (!sameFeatures(route.gate.features, expected.features)) {
    errors.push(
      `[${key}] invalid gate features: expected=[${expected.features.join(',')}] actual=[${route.gate.features.join(',')}] path="${route.path}"`,
    )
  }
}

const gatedButUntracked = routes.filter(
  (route) =>
    (route.gate.type === 'feature' || route.gate.type === 'any') && !Object.prototype.hasOwnProperty.call(EXPECTED_COMM_GATES, route.key),
)

for (const route of gatedButUntracked) {
  errors.push(`[${route.key}] gated route is not tracked in EXPECTED_COMM_GATES (path="${route.path}")`)
}

if (errors.length) {
  console.error('Communications gate check failed:')
  errors.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(
  `Communications gate check passed. Tracked routes: ${Object.keys(EXPECTED_COMM_GATES).length}, total app routes: ${routes.length}.`,
)
