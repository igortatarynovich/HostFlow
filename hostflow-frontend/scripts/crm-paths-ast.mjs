/**
 * Shared TypeScript AST helpers for resolving `CRM_APP_PATHS` / `CRM.*` / `seg(...)` in static checks.
 */
import fs from 'node:fs'
import ts from 'typescript'

export function loadSource(file, kind) {
  const text = fs.readFileSync(file, 'utf-8')
  return ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, kind)
}

export function getPropertyName(node) {
  if (!node) return null
  if (ts.isIdentifier(node) || ts.isStringLiteral(node)) return node.text
  return null
}

export function readString(node) {
  if (!node) return null
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text
  return null
}

export function readStringArray(node) {
  if (!node || !ts.isArrayLiteralExpression(node)) return []
  return node.elements.map((el) => readString(el)).filter(Boolean)
}

export function unwrap(node) {
  if (!node) return node
  if (ts.isAsExpression(node) || ts.isTypeAssertionExpression(node) || ts.isParenthesizedExpression(node)) {
    return unwrap(node.expression)
  }
  return node
}

export function findObjectLiteral(sf, variableName) {
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

export function findArrayLiteral(sf, variableName) {
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

export function parseCrmAppPathsMap(sf) {
  const obj = findObjectLiteral(sf, 'CRM_APP_PATHS')
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

export function crmKeyFromNode(node) {
  const n = unwrap(node)
  if (n && ts.isPropertyAccessExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === 'CRM') {
    return n.name.text
  }
  return null
}

/** Full URL starting with /app (matches `ACTIVATION_PATHS` values). */
export function resolvePathToFullAppUrl(node, crmPaths) {
  const n = unwrap(node)
  if (!n) return null
  if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) {
    const s = n.text
    if (s.startsWith('/app')) return s
    return `/app/${s.replace(/^\//, '')}`
  }
  const direct = crmKeyFromNode(n)
  if (direct && crmPaths[direct]) return crmPaths[direct]
  if (ts.isCallExpression(n) && ts.isIdentifier(n.expression)) {
    const callee = n.expression.text
    if ((callee === 'seg' || callee === 'crmAppRouteSegment') && n.arguments.length) {
      const key = crmKeyFromNode(n.arguments[0])
      if (key && crmPaths[key]) return crmPaths[key]
    }
  }
  return null
}

/** React Router segment(s) under `/app` (no leading slash), e.g. `settings/billing`. */
export function resolvePathToAppSegment(node, crmPaths) {
  const full = resolvePathToFullAppUrl(node, crmPaths)
  if (!full || !full.startsWith('/app/')) return null
  return full.slice('/app/'.length)
}

/**
 * Route pattern under `/app` (no leading slash), including params, e.g. `inbox/threads/:threadId`.
 * Supports `seg(...)`, `CRM.*`, string literals, and `` `${seg(CRM.x)}/:id` ``.
 */
export function resolvePathPatternToAppSegment(node, crmPaths) {
  const n = unwrap(node)
  if (!n) return null
  const plain = resolvePathToAppSegment(n, crmPaths)
  if (plain) return plain
  if (!ts.isTemplateExpression(n)) return null
  let acc = n.head.text
  for (const span of n.templateSpans) {
    const inner = resolvePathToFullAppUrl(span.expression, crmPaths)
    if (!inner || !inner.startsWith('/app/')) return null
    acc += inner.slice('/app/'.length) + span.literal.text
  }
  return acc
}
