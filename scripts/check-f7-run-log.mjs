#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')
const ssotPath = path.join(repoRoot, 'docs', 'crm-production-readiness-ssot.md')

function parseLinkTarget(text) {
  const match = String(text || '').match(/\[[^\]]+\]\(([^)]+)\)/)
  return match ? match[1] : null
}

function stripTicks(value) {
  return String(value || '').replace(/`/g, '').trim()
}

function normalizeSoft(value) {
  return stripTicks(value).toLowerCase()
}

function safeSlug(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function parseTableLine(line) {
  const parts = line.split('|').map((p) => p.trim())
  if (parts.length < 9) return null
  return parts.slice(1, 8)
}

function parseRunRecord(content) {
  const row = {}
  for (const line of content.split('\n')) {
    const m = line.match(/^([A-Za-z ]+):\s*`([^`]+)`/)
    if (!m) continue
    const key = m[1].trim().toLowerCase()
    const value = m[2].trim()
    if (key === 'date') row.date = value
    if (key === 'scenario') row.scenario = value
    if (key === 'business type') row.businessType = value
    if (key === 'environment') row.environment = value
    if (key === 'tenant') row.tenant = value
    if (key === 'result') row.result = value
  }
  return row
}

function main() {
  if (!fs.existsSync(ssotPath)) {
    console.error(`SSOT not found: ${ssotPath}`)
    process.exit(1)
  }
  const text = fs.readFileSync(ssotPath, 'utf-8')
  const startMarker = '### 10.1 Журнал прогонов (операционный)'
  const endMarker = '### 10.2 Next Actions Для `F7`'

  const startIdx = text.indexOf(startMarker)
  const endIdx = text.indexOf(endMarker)
  if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
    console.error('Could not locate F7 run-log section in SSOT')
    process.exit(1)
  }

  const section = text.slice(startIdx, endIdx)
  const lines = section
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('|') && !l.includes('|---'))

  if (lines.length < 2) {
    console.error('F7 run-log table is empty')
    process.exit(1)
  }

  const header = parseTableLine(lines[0]) || []
  if (header.length !== 7) {
    console.error('F7 run-log table header is malformed')
    process.exit(1)
  }

  const dataRows = lines.slice(1)
  const errors = []
  const seenScenarios = new Set()
  const seenRunKeys = new Set()
  const allowedResults = new Set(['PASS', 'FAIL', 'BLOCKED', 'IN_PROGRESS'])

  for (const rowLine of dataRows) {
    const row = parseTableLine(rowLine)
    if (!row || row.length !== 7) {
      errors.push(`Malformed row: ${rowLine}`)
      continue
    }
    const [date, scenario, env, tenant, result, evidence, owner] = row

    if (!/^\`?\d{4}-\d{2}-\d{2}\`?$/.test(date)) {
      errors.push(`Invalid date cell: "${date}"`)
    }
    const scenarioMatch = scenario.match(/([ABC])\s*\(/)
    if (!scenarioMatch) {
      errors.push(`Invalid scenario cell: "${scenario}"`)
    } else {
      seenScenarios.add(scenarioMatch[1])
    }
    if (!env) errors.push(`Empty environment cell for scenario "${scenario}"`)
    if (!tenant) errors.push(`Empty tenant cell for scenario "${scenario}"`)

    const runKey = [
      normalizeSoft(scenario),
      normalizeSoft(date),
      normalizeSoft(env),
      normalizeSoft(tenant),
    ].join('|')
    if (seenRunKeys.has(runKey)) {
      errors.push(`Duplicate run-log row key detected: scenario/date/env/tenant = ${runKey}`)
    } else {
      seenRunKeys.add(runKey)
    }

    const normalizedResult = stripTicks(result)
    if (!allowedResults.has(normalizedResult)) {
      errors.push(`Invalid result "${result}" for scenario "${scenario}"`)
    }

    if (!owner) errors.push(`Empty owner for scenario "${scenario}"`)
    if (!evidence) {
      errors.push(`Empty evidence for scenario "${scenario}"`)
      continue
    }

    const linkTarget = parseLinkTarget(evidence)
    if (linkTarget) {
      const abs = linkTarget.startsWith('/') ? linkTarget : path.resolve(repoRoot, linkTarget)
      if (!fs.existsSync(abs)) {
        errors.push(`Evidence link target does not exist for "${scenario}": ${abs}`)
      } else {
        const base = path.basename(abs)
        const filePattern = /^f7-run-([abc])-(\d{4}-\d{2}-\d{2})-(staging|production)-(.+)\.md$/i
        const fileMatch = base.match(filePattern)
        if (fileMatch) {
          const rec = parseRunRecord(fs.readFileSync(abs, 'utf-8'))
          const scenarioCode = scenarioMatch ? scenarioMatch[1] : null
          const [, fileScenario, fileDate, fileEnv, fileTenant] = fileMatch
          if (!rec.date || !rec.scenario || !rec.environment || !rec.tenant || !rec.result) {
            errors.push(`Run-record has missing header fields: ${abs}`)
          } else {
            if (normalizeSoft(fileScenario) !== normalizeSoft(scenarioCode || '')) {
              errors.push(`Run-record filename scenario mismatch for ${scenario}: row=${scenarioCode} file=${fileScenario}`)
            }
            if (normalizeSoft(fileDate) !== normalizeSoft(date)) {
              errors.push(`Run-record filename date mismatch for ${scenario}: row=${stripTicks(date)} file=${fileDate}`)
            }
            if (normalizeSoft(fileEnv) !== normalizeSoft(env)) {
              errors.push(`Run-record filename environment mismatch for ${scenario}: row=${stripTicks(env)} file=${fileEnv}`)
            }
            const rowTenantSlug = safeSlug(stripTicks(tenant))
            if (normalizeSoft(fileTenant) !== normalizeSoft(rowTenantSlug)) {
              errors.push(`Run-record filename tenant mismatch for ${scenario}: row=${rowTenantSlug} file=${fileTenant}`)
            }
            if (normalizeSoft(rec.date) !== normalizeSoft(date)) {
              errors.push(`Run-record date mismatch for ${scenario}: row=${stripTicks(date)} file=${rec.date}`)
            }
            if (normalizeSoft(rec.scenario) !== normalizeSoft(scenarioCode || '')) {
              errors.push(`Run-record scenario mismatch for ${scenario}: row=${scenarioCode} file=${rec.scenario}`)
            }
            if (normalizeSoft(rec.environment) !== normalizeSoft(env)) {
              errors.push(`Run-record environment mismatch for ${scenario}: row=${stripTicks(env)} file=${rec.environment}`)
            }
            if (normalizeSoft(rec.tenant) !== normalizeSoft(tenant)) {
              errors.push(`Run-record tenant mismatch for ${scenario}: row=${stripTicks(tenant)} file=${rec.tenant}`)
            }
            if (normalizeSoft(rec.result) !== normalizeSoft(result)) {
              errors.push(`Run-record result mismatch for ${scenario}: row=${stripTicks(result)} file=${rec.result}`)
            }
          }
        } else if (normalizedResult === 'PASS' || normalizedResult === 'FAIL') {
          errors.push(`Result ${normalizedResult} requires canonical run-record filename for "${scenario}": ${base}`)
        }
      }
    } else if (normalizedResult === 'PASS' || normalizedResult === 'FAIL') {
      errors.push(`Result ${normalizedResult} requires explicit evidence link for "${scenario}"`)
    }
  }

  for (const scenarioCode of ['A', 'B', 'C']) {
    if (!seenScenarios.has(scenarioCode)) {
      errors.push(`Missing run-log row for scenario ${scenarioCode}`)
    }
  }

  if (errors.length) {
    console.error('F7 run-log check failed:')
    errors.forEach((e) => console.error(`- ${e}`))
    process.exit(1)
  }

  console.log(`F7 run-log check passed. Rows: ${dataRows.length}, scenarios: ${[...seenScenarios].join(',')}.`)
}

main()
