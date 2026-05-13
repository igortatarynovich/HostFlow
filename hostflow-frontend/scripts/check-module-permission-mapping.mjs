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

function parseMappingKeys(sf, variableName) {
  const obj = findObjectLiteral(sf, variableName)
  const out = new Set()
  if (!obj) return out
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const key = getPropertyName(prop.name)
    if (key) out.add(key)
  }
  return out
}

function parseRolePermissions(sf) {
  const obj = findObjectLiteral(sf, 'ROLE_PERMISSIONS')
  const out = new Set()
  if (!obj) return out
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue
    const values = readStringArray(prop.initializer)
    for (const value of values) {
      if (value && value !== '*') out.add(value)
    }
  }
  return out
}

function parseRoutePermissions(sf) {
  const arr = findArrayLiteral(sf, 'APP_ROUTES')
  const out = new Set()
  if (!arr) return out
  for (const el of arr.elements) {
    if (!ts.isObjectLiteralExpression(el)) continue
    for (const prop of el.properties) {
      if (!ts.isPropertyAssignment(prop)) continue
      const name = getPropertyName(prop.name)
      if (name !== 'permission') continue
      if (ts.isStringLiteral(prop.initializer)) {
        out.add(prop.initializer.text)
      } else {
        for (const p of readStringArray(prop.initializer)) out.add(p)
      }
    }
  }
  return out
}

const modulePermissionPrefixes = [
  'companies.',
  'leads.',
  'vacancies.',
  'candidates.',
  'documents.',
  'services.',
  'workforce.',
]

function isModulePermission(permission) {
  return modulePermissionPrefixes.some((prefix) => permission.startsWith(prefix))
}

const permissionsSf = loadSource(permissionsFile, ts.ScriptKind.TS)
const routesSf = loadSource(routesFile, ts.ScriptKind.TSX)

const viewMapping = parseMappingKeys(permissionsSf, 'VIEW_PERMISSION_TO_MODULE')
const editMapping = parseMappingKeys(permissionsSf, 'EDIT_PERMISSION_TO_MODULE')
const mapped = new Set([...viewMapping, ...editMapping])

const rolePermissions = parseRolePermissions(permissionsSf)
const routePermissions = parseRoutePermissions(routesSf)

const moduleRolePerms = [...rolePermissions].filter(isModulePermission)
const moduleRoutePerms = [...routePermissions].filter(isModulePermission)

const errors = []

for (const permission of moduleRolePerms) {
  if (!mapped.has(permission)) {
    errors.push(`ROLE_PERMISSIONS includes module permission "${permission}" without module mapping`)
  }
}

for (const permission of moduleRoutePerms) {
  if (!mapped.has(permission)) {
    errors.push(`APP_ROUTES uses module permission "${permission}" without module mapping`)
  }
}

for (const permission of mapped) {
  if (!isModulePermission(permission)) {
    errors.push(`Module mapping contains non-module permission "${permission}"`)
  }
}

if (errors.length) {
  console.error('Module permission mapping check failed:')
  errors.forEach((line) => console.error(`- ${line}`))
  process.exit(1)
}

console.log(
  `Module permission mapping check passed. Role perms: ${moduleRolePerms.length}, route perms: ${moduleRoutePerms.length}, mapped: ${mapped.size}.`,
)
